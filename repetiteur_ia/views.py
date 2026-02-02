from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, DetailView, View
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.utils import timezone 
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import json
from django.core.management import call_command
from io import StringIO
import sys

from .embeddings import search_similar_content, create_vector_store_from_texts
from openai import OpenAI
from django.conf import settings

from utilisateurs.models import Eleve, Parent
from cours.models import Cours, EmploiDuTemps, Quiz
from repetiteur_ia.models import Notification, SessionRevisionProgrammee, SoumissionCours
from repetiteur_ia.forms import EmploiDuTempsForm, SoumissionCoursForm
from cours.models import EmploiDuTemps
from paiement.models import Paiement 
from .utils import generer_audio, generer_salutation_eleve, repondre_au_repetiteur, transcrire_audio, generer_contenu_ia



client = OpenAI(api_key=settings.OPENAI_API_KEY)

class AccueilView(TemplateView):
    template_name = 'index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            if self.request.user.type_utilisateur == 'élève':
                try:
                    eleve = Eleve.objects.get(user=self.request.user)
                    context['eleve'] = eleve
                    
                    #  Cours récents : utiliser la table intermédiaire
                    context['cours_recents'] = Cours.objects.filter(
                        eleves_inscrits__eleve=eleve
                    ).order_by('-date_creation')[:5]
                    
                    #  Notifications non lues
                    context['notifications'] = Notification.objects.filter(
                        utilisateur=self.request.user, 
                        lue=False
                    ).order_by('-date_creation')[:10]
                    
                    #  Emploi du temps : comme il est lié directement à l'élève, c’est correct
                    jour_actuel = timezone.now().strftime('%A').lower()
                    context['emploi_du_temps_aujourdhui'] = EmploiDuTemps.objects.filter(
                        eleve=eleve, 
                        jour_semaine=jour_actuel,
                        actif=True
                    ).order_by('heure_debut')
                    
                except Eleve.DoesNotExist:
                    pass
            
            elif self.request.user.type_utilisateur == 'parent':
                try:
                    parent = self.request.user.parent
                    context['enfants'] = parent.eleves.all()
                    
                    context['notifications'] = Notification.objects.filter(
                        utilisateur=self.request.user, 
                        lue=False
                    ).order_by('-date_creation')[:10]
                    
                except:
                    pass
        
        else:
            context['page_publique'] = True
        
        return context


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('connexion')

        if request.user.type_utilisateur == 'parent':
            return super().dispatch(request, *args, **kwargs)

        if request.user.type_utilisateur == 'élève':
            try:
                eleve = Eleve.objects.get(user=request.user)
                self._mettre_a_jour_abonnement(eleve)

                if eleve.abonnement_actif:
                    # Programmer automatiquement les sessions si nécessaire
                    self._programmer_sessions_automatiques(eleve)
                    return super().dispatch(request, *args, **kwargs)
                else:
                    messages.info(
                        request,
                        "Votre abonnement a expiré ou n'est pas encore activé. Veuillez souscrire pour accéder au tableau de bord."
                    )
                    return redirect('abonnements')

            except Eleve.DoesNotExist:
                messages.error(request, "Profil élève non trouvé.")
                return redirect('profil')

        return redirect('accueil')

    def _mettre_a_jour_abonnement(self, eleve):
        maintenant = timezone.now().date()

        paiement_actif = (
            Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET)
            .order_by('-date_paiement')
            .first()
        )

        if paiement_actif:
            if paiement_actif.date_debut_abonnement <= maintenant <= paiement_actif.date_fin_abonnement:
                if not eleve.abonnement_actif:
                    eleve.abonnement_actif = True
                    eleve.save()
            else:
                if eleve.abonnement_actif:
                    eleve.abonnement_actif = False
                    eleve.save()
        else:
            if eleve.abonnement_actif:
                eleve.abonnement_actif = False
                eleve.save()

    def _programmer_sessions_automatiques(self, eleve):
        """Programme automatiquement les sessions si l'élève n'en a pas pour la semaine"""
        try:
            debut_semaine = timezone.now().date() - timedelta(days=timezone.now().weekday())
            fin_semaine = debut_semaine + timedelta(days=6)
            
            # Vérifier si des sessions existent déjà pour cette semaine
            sessions_existantes = SessionRevisionProgrammee.objects.filter(
                eleve=eleve,
                date_programmation__date__range=[debut_semaine, fin_semaine]
            ).exists()
            
            if not sessions_existantes:
                self._creer_sessions_pour_eleve(eleve, debut_semaine)
                
        except Exception as e:
            print(f"❌ Erreur programmation automatique: {e}")

    def _creer_sessions_pour_eleve(self, eleve, debut_semaine):
        """Crée les sessions de révision pour un élève"""
        emplois = EmploiDuTemps.objects.filter(eleve=eleve, actif=True)
        sessions_creees = 0
        
        for emploi in emplois:
            # Programmer une session 1 jour après chaque cours
            jour_cours = self._get_jour_semaine_numero(emploi.jour_semaine)
            date_session = debut_semaine + timedelta(days=jour_cours + 1)  # +1 = jour suivant
            
            # Vérifier que la session est dans le futur
            if date_session < timezone.now().date():
                continue
                
            # Utiliser l'heure du cours ou une heure par défaut (17h00)
            heure_session = emploi.heure_debut if emploi.heure_debut else datetime.strptime("17:00", "%H:%M").time()
            
            # Créer la datetime complète
            date_complete = timezone.make_aware(
                datetime.combine(date_session, heure_session)
            )
            
            # Vérifier si la session existe déjà
            session_existante = SessionRevisionProgrammee.objects.filter(
                eleve=eleve,
                emploi_temps=emploi,
                date_programmation__date=date_session
            ).exists()
            
            if not session_existante:
                # Créer la session programmée
                SessionRevisionProgrammee.objects.create(
                    eleve=eleve,
                    emploi_temps=emploi,
                    titre=f"Révision {emploi.matiere}",
                    date_programmation=date_complete,
                    duree_prevue=45,
                    objectifs=f"Revoir le cours de {emploi.matiere} du {emploi.jour_semaine} et consolider les acquis",
                    notes_preparation=f"Session programmée automatiquement. Cours prévu le {emploi.jour_semaine} à {emploi.heure_debut}."
                )
                sessions_creees += 1
        
        if sessions_creees > 0:
            print(f"✅ {sessions_creees} session(s) programmée(s) pour {eleve.user.username}")

    def _get_jour_semaine_numero(self, jour_semaine):
        """Convertit le jour de la semaine en numéro"""
        jours = {
            'lundi': 0, 'mardi': 1, 'mercredi': 2, 
            'jeudi': 3, 'vendredi': 4, 'samedi': 5, 'dimanche': 6
        }
        return jours.get(jour_semaine.lower(), 0)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['repetiteur_access'] = False
        context['salutation_repetiteur'] = None

        if self.request.user.type_utilisateur == 'élève':
            try:
                eleve = Eleve.objects.get(user=self.request.user)
                context['eleve'] = eleve

                # Statistiques complètes
                context['statistiques'] = {
                    'cours_crees': Cours.objects.filter(eleves=eleve).count(),
                    'quiz_completes': Quiz.objects.filter(cours__eleves=eleve).count(),
                    'sessions_programmees': SessionRevisionProgrammee.objects.filter(eleve=eleve).count(),
                    'sessions_terminees': SessionRevisionProgrammee.objects.filter(eleve=eleve, statut='terminee').count(),
                    'sessions_en_cours': SessionRevisionProgrammee.objects.filter(eleve=eleve, statut='en_cours').count(),
                    'prochaines_sessions': SessionRevisionProgrammee.objects.filter(
                        eleve=eleve, 
                        date_programmation__gte=timezone.now()
                    ).count(),
                }

                # Emploi du temps personnel
                context['emploi_du_temps'] = EmploiDuTemps.objects.filter(
                    eleve=eleve, actif=True
                ).order_by('jour_semaine', 'heure_debut')

                # Sessions à venir (prochaines 5)
                sessions_a_venir = SessionRevisionProgrammee.objects.filter(
                    eleve=eleve,
                    date_programmation__gte=timezone.now()
                ).order_by('date_programmation')[:5]
                
                context['sessions_a_venir'] = sessions_a_venir

                # Session en cours (s'il y en a une)
                session_en_cours = SessionRevisionProgrammee.objects.filter(
                    eleve=eleve,
                    statut='en_cours'
                ).first()
                context['session_en_cours'] = session_en_cours

                # Prochain cours aujourd'hui
                aujourdhui = timezone.now().strftime('%A').lower()
                context['prochain_cours'] = EmploiDuTemps.objects.filter(
                    eleve=eleve,
                    jour_semaine=aujourdhui,
                    heure_debut__gte=timezone.now().time(),
                    actif=True
                ).order_by('heure_debut').first()

                # Paiement actif
                paiement_actif = (
                    Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET)
                    .order_by('-date_paiement')
                    .first()
                )
                context['paiement_actif'] = paiement_actif

                # Accès répétiteur IA
                if getattr(eleve, 'abonnement_actif', False):
                    context['repetiteur_access'] = True
                    try:
                        context['salutation_repetiteur'] = generer_salutation_eleve(eleve)
                    except Exception:
                        context['salutation_repetiteur'] = f"Bonjour {eleve.user.first_name or eleve.user.username} !"

                # Informations pour le template
                context['aujourdhui'] = timezone.now().strftime('%A %d %B %Y')
                context['semaine_progression'] = self._calculer_progression_semaine(eleve)

            except Eleve.DoesNotExist:
                messages.error(self.request, "Profil élève introuvable.")

        # Parent connecté
        elif self.request.user.type_utilisateur == 'parent':
            try:
                parent = self.request.user.parent
                enfants = parent.eleves.all()

                context['enfants_avec_statistiques'] = []
                for enfant in enfants:
                    stats_enfant = {
                        'enfant': enfant,
                        'cours_crees': Cours.objects.filter(eleves_inscrits__eleve=enfant).count(),
                        'sessions_programmees': SessionRevisionProgrammee.objects.filter(eleve=enfant).count(),
                        'sessions_terminees': SessionRevisionProgrammee.objects.filter(eleve=enfant, statut='terminee').count(),
                        'prochaines_sessions': SessionRevisionProgrammee.objects.filter(
                            eleve=enfant, 
                            date_programmation__gte=timezone.now()
                        ).order_by('date_programmation')[:3],
                        'dernier_cours': Cours.objects.filter(eleves_inscrits__eleve=enfant).last(),
                        'abonnement_actif': getattr(enfant, 'abonnement_actif', False)
                    }
                    context['enfants_avec_statistiques'].append(stats_enfant)

                # Vérifie si au moins un enfant a un abonnement actif
                actif_enfant = next((e for e in enfants if getattr(e, 'abonnement_actif', False)), None)
                if actif_enfant:
                    context['repetiteur_access'] = True
                    try:
                        context['salutation_repetiteur'] = generer_salutation_eleve(actif_enfant)
                    except Exception:
                        context['salutation_repetiteur'] = "Bonjour — un de vos enfants a accès au répétiteur."
                        
            except Exception as e:
                print(f"Erreur contexte parent: {e}")

        return context

    def _calculer_progression_semaine(self, eleve):
        """Calcule la progression de la semaine en cours"""
        try:
            debut_semaine = timezone.now().date() - timedelta(days=timezone.now().weekday())
            fin_semaine = debut_semaine + timedelta(days=6)
            
            sessions_semaine = SessionRevisionProgrammee.objects.filter(
                eleve=eleve,
                date_programmation__date__range=[debut_semaine, fin_semaine]
            )
            
            sessions_terminees = sessions_semaine.filter(statut='terminee').count()
            total_sessions = sessions_semaine.count()
            
            if total_sessions > 0:
                return {
                    'pourcentage': int((sessions_terminees / total_sessions) * 100),
                    'terminees': sessions_terminees,
                    'total': total_sessions
                }
            else:
                return {
                    'pourcentage': 0,
                    'terminees': 0,
                    'total': 0
                }
                
        except Exception as e:
            print(f"Erreur calcul progression: {e}")
            return {'pourcentage': 0, 'terminees': 0, 'total': 0}
        
        
class RepetiteurChatView(LoginRequiredMixin, View):
    template_name = 'repetiteur_ia/chat.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Vérification pour élève
        if getattr(user, 'type_utilisateur', None) == 'élève':
            try:
                eleve = Eleve.objects.get(user=user)
                if getattr(eleve, 'abonnement_actif', False):
                    return super().dispatch(request, *args, **kwargs)
                # Vérification des paiements
                dernier_paiement = Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET).order_by('-date_paiement').first()
                if dernier_paiement:
                    return super().dispatch(request, *args, **kwargs)
                messages.info(request, "Souscrivez pour accéder au répétiteur IA.")
                return redirect('abonnements')
            except Eleve.DoesNotExist:
                messages.error(request, "Profil élève introuvable.")
                return redirect('profil')

        # Vérification pour parent
        if getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = user.parent
                enfants = parent.eleves.all()
                if any(getattr(e, 'abonnement_actif', False) for e in enfants):
                    return super().dispatch(request, *args, **kwargs)
            except:
                pass
            messages.info(request, "Aucun enfant avec abonnement actif.")
            return redirect('profil')

        messages.error(request, "Accès non autorisé.")
        return redirect('accueil')

    def _sauvegarder_conversation(self, utilisateur, session, question, reponse, contexte=None):
        """Sauvegarde l'échange dans l'historique"""
        from .models import HistoriqueConversation
        
        type_conv = 'session' if session else 'libre'
        
        HistoriqueConversation.objects.create(
            utilisateur=utilisateur,
            session=session,
            type_conversation=type_conv,
            question=question,
            reponse=reponse,
            contexte_utilise=contexte or {}
        )

    def _get_historique_recent(self, utilisateur, session=None, limit=10):
        """Récupère l'historique récent pour le contexte"""
        from .models import HistoriqueConversation
        
        queryset = HistoriqueConversation.objects.filter(
            utilisateur=utilisateur
        ).order_by('-date_creation')
        
        if session:
            queryset = queryset.filter(session=session)
            
        historique = list(queryset[:limit])
        historique.reverse()  # Pour avoir l'ordre chronologique
        
        return [
            {
                'id': conv.id,
                'question': conv.question,
                'reponse': conv.reponse,
                'date': conv.date_creation,
                'session': conv.session_id,
                'type_conversation': conv.type_conversation
            }
            for conv in historique
        ]

    def _get_eleve_context(self, request):
        """Récupère et structure les informations de l'élève"""
        user = request.user
        
        if user.type_utilisateur == 'élève':
            try:
                eleve = Eleve.objects.select_related('user').get(user=user)
                return {
                    'eleve': eleve,
                    'niveau': eleve.get_niveau_display(),
                    'classe': eleve.get_classe_display(),
                    'nom_complet': eleve.user.get_full_name() or eleve.user.username
                }
            except Eleve.DoesNotExist:
                return None
                
        elif user.type_utilisateur == 'parent':
            try:
                parent = user.parent
                enfants_actifs = [
                    e for e in parent.eleves.all() 
                    if getattr(e, 'abonnement_actif', False)
                ]
                if enfants_actifs:
                    eleve = enfants_actifs[0]
                    return {
                        'eleve': eleve,
                        'niveau': eleve.get_niveau_display(),
                        'classe': eleve.get_classe_display(),
                        'nom_complet': eleve.user.get_full_name() or eleve.user.username,
                        'est_parent': True
                    }
            except Parent.DoesNotExist:
                pass
                
        return None

    def get(self, request):
        """Affiche la page du chat avec sessions programmées et historique"""
        context = self.get_context_data()
        
        # Récupérer la session active si spécifiée
        session_id = request.GET.get('session')
        session_active = None
        
        if session_id:
            try:
                session_active = SessionRevisionProgrammee.objects.get(
                    id=session_id, 
                    eleve=request.user.eleve
                )
                context['session_active'] = session_active
                
                # Marquer la session comme en cours
                if session_active.statut != 'en_cours':
                    session_active.statut = 'en_cours'
                    session_active.save()
                    
            except SessionRevisionProgrammee.DoesNotExist:
                pass
        
        # Récupérer l'historique des conversations
        try:
            historique = self._get_historique_recent(
                request.user, 
                session_active, 
                limit=20
            )
            context['historique_conversations'] = historique
            context['total_messages'] = len(historique)
        except Exception as e:
            print(f"Erreur chargement historique: {e}")
            context['historique_conversations'] = []
            context['total_messages'] = 0
        
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        ctx = {}
        try:
            if getattr(self.request.user, 'type_utilisateur', None) == 'élève':
                eleve = Eleve.objects.get(user=self.request.user)
                
                # Sessions programmées
                sessions = SessionRevisionProgrammee.objects.filter(
                    eleve=eleve,
                    date_programmation__gte=timezone.now() - timedelta(days=1)
                ).order_by('date_programmation')[:10]
                
                ctx['sessions_programmees'] = [
                    {
                        'id': session.id,
                        'matiere': session.emploi_temps.matiere,
                        'date_programmation': session.date_programmation,
                        'duree': session.duree_prevue,
                        'objectifs': session.objectifs,
                        'statut': session.get_statut_display(),
                        'est_en_cours': session.statut == 'en_cours',
                        'soumissions_count': session.soumissions.count()
                    }
                    for session in sessions
                ]
                
                # Prochain cours aujourd'hui
                aujourdhui = timezone.now().strftime('%A').lower()
                ctx['prochain_cours'] = EmploiDuTemps.objects.filter(
                    eleve=eleve,
                    jour_semaine=aujourdhui,
                    heure_debut__gte=timezone.now().time(),
                    actif=True
                ).order_by('heure_debut').first()
                
                # Informations élève
                ctx['eleve_info'] = {
                    'eleve': eleve,
                    'niveau': eleve.get_niveau_display(),
                    'classe': eleve.get_classe_display(),
                    'nom_complet': eleve.user.get_full_name() or eleve.user.username
                }
                
                # Salutation personnalisée
                ctx['salutation'] = generer_salutation_eleve(eleve)
                
                # Matières disponibles
                ctx['matieres_disponibles'] = EmploiDuTemps.objects.filter(
                    eleve=eleve, actif=True
                ).values_list('matiere', flat=True).distinct()
                
            else:
                # Cas parent
                parent = self.request.user.parent
                actif = next((e for e in parent.eleves.all() if getattr(e, 'abonnement_actif', False)), None)
                if actif:
                    ctx['salutation'] = generer_salutation_eleve(actif)
                    ctx['eleve_info'] = {
                        'eleve': actif,
                        'niveau': actif.get_niveau_display(),
                        'classe': actif.get_classe_display(),
                        'nom_complet': actif.user.get_full_name() or actif.user.username,
                        'est_parent': True
                    }
                else:
                    ctx['salutation'] = "Bonjour, bienvenue sur Mrkarfour."
                    
        except Exception as e:
            print(f"Erreur contexte: {e}")
            ctx['salutation'] = "Bonjour, bienvenue sur Mrkarfour."
        
        ctx['niveau_eleve'] = ctx.get('eleve_info', {}).get('niveau', 'secondaire')
        return ctx

    def post(self, request):
        """Gère l'interaction avec le répétiteur IA avec contexte de session et historique"""
        try:
            # Vérification d'accès
            user = request.user
            if getattr(user, 'type_utilisateur', None) == 'élève':
                try:
                    eleve = Eleve.objects.get(user=user)
                    if not getattr(eleve, 'abonnement_actif', False):
                        dernier_paiement = Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET).order_by('-date_paiement').first()
                        if not dernier_paiement:
                            return JsonResponse({
                                "status": "error",
                                "error": "Accès au répétiteur non autorisé. Vérifiez votre abonnement."
                            }, status=403)
                except Eleve.DoesNotExist:
                    return JsonResponse({
                        "status": "error",
                        "error": "Profil élève introuvable."
                    }, status=403)
            
            elif getattr(user, 'type_utilisateur', None) == 'parent':
                try:
                    parent = user.parent
                    if not any(getattr(e, 'abonnement_actif', False) for e in parent.eleves.all()):
                        return JsonResponse({
                            "status": "error",
                            "error": "Aucun enfant avec abonnement actif."
                        }, status=403)
                except:
                    return JsonResponse({
                        "status": "error",
                        "error": "Profil parent introuvable."
                    }, status=403)
            else:
                return JsonResponse({
                    "status": "error",
                    "error": "Type d'utilisateur non reconnu."
                }, status=403)

            # Récupération des informations élève et session
            eleve_info = self._get_eleve_context(request)
            session_id = request.POST.get('session_id')
            session_context = None
            session_obj = None
            
            if session_id:
                try:
                    session_obj = SessionRevisionProgrammee.objects.get(
                        id=session_id, 
                        eleve=request.user.eleve
                    )
                    session_context = {
                        'matiere': session_obj.emploi_temps.matiere,
                        'objectifs': session_obj.objectifs,
                        'soumissions': list(session_obj.soumissions.values_list('contenu_texte', flat=True))
                    }
                except SessionRevisionProgrammee.DoesNotExist:
                    pass
            
            # Récupérer l'historique récent pour le contexte
            historique = self._get_historique_recent(
                request.user, 
                session_obj, 
                limit=5  # Derniers 5 échanges
            )
            
            # Construire le contexte avec l'historique
            contexte_historique = ""
            if historique:
                contexte_historique = "CONTEXTE DES ÉCHANGES PRÉCÉDENTS:\n"
                for i, conv in enumerate(historique, 1):
                    contexte_historique += f"\nÉchange {i}:\n"
                    contexte_historique += f"Question: {conv['question']}\n"
                    contexte_historique += f"Réponse: {conv['reponse']}\n"
            
            # Traitement de la question
            question = ""
            if "audio" in request.FILES:
                try:
                    question = transcrire_audio(request.FILES["audio"])
                    if not question or question == "Je n'ai pas compris la question.":
                        return JsonResponse({
                            "status": "error",
                            "error": "Je n'ai pas compris votre question audio. Pouvez-vous répéter ?"
                        }, status=400)
                except Exception as e:
                    return JsonResponse({
                        "status": "error",
                        "error": f"Erreur de traitement audio: {str(e)}"
                    }, status=400)
            else:
                question = request.POST.get("question", "").strip()
                if not question:
                    return JsonResponse({
                        "status": "error", 
                        "error": "Veuillez poser une question."
                    }, status=400)

            # Recherche de contenu similaire dans le vectorstore
            try:
                contenus_similaires = search_similar_content(question)
                contexte_pedagogique = {
                    "contenus_similaires": contenus_similaires,
                    "nombre_resultats": len(contenus_similaires),
                    "historique_conversation": contexte_historique
                }
                print(f"🔍 Vectorstore: {len(contenus_similaires)} contenus similaires trouvés")
            except Exception as e:
                print(f"⚠️ Erreur vectorstore: {e}")
                contexte_pedagogique = {
                    "contenus_similaires": [],
                    "nombre_resultats": 0,
                    "historique_conversation": contexte_historique
                }

            # Niveau par défaut si non spécifié
            niveau_eleve = "secondaire"
            if eleve_info and 'niveau' in eleve_info:
                niveau_eleve = eleve_info['niveau']

            # Génération de la réponse IA avec contexte enrichi
            try:
                reponse_texte = repondre_au_repetiteur(
                    question=question,
                    contexte_pedagogique=contexte_pedagogique,
                    contexte_session=session_context,
                    niveau_eleve=niveau_eleve,
                    historique_conversation=contexte_historique
                )
            except Exception as e:
                print(f"Erreur génération réponse IA: {e}")
                reponse_texte = f"Je suis MrKarfour. Pour votre question '{question}', je rencontre actuellement un problème technique. Veuillez réessayer dans quelques instants."

            # Sauvegarder la conversation dans l'historique
            self._sauvegarder_conversation(
                utilisateur=request.user,
                session=session_obj,
                question=question,
                reponse=reponse_texte,
                contexte={
                    'niveau_eleve': niveau_eleve,
                    'session_id': session_id,
                    'contenus_trouves': contexte_pedagogique["nombre_resultats"],
                    'historique_utilise': len(historique)
                }
            )

            # Génération de la version audio
            chemin_audio = ""
            try:
                chemin_audio = generer_audio(reponse_texte)
            except Exception as e:
                print(f"Génération audio échouée: {e}")

            # Récupérer le nouvel historique mis à jour
            nouvel_historique = self._get_historique_recent(
                request.user, 
                session_obj, 
                limit=10
            )

            return JsonResponse({
                "status": "success",
                "question": question,
                "reponse": reponse_texte,
                "audio_url": chemin_audio,
                "niveau_adapte": niveau_eleve,
                "contenus_trouves": contexte_pedagogique["nombre_resultats"],
                "session_active": bool(session_id),
                "historique_count": len(nouvel_historique),
                "historique_recent": nouvel_historique[-5:] if len(nouvel_historique) > 5 else nouvel_historique
            })

        except Exception as e:
            print(f"Erreur répétiteur IA: {e}")
            return JsonResponse({
                "status": "error",
                "error": "Désolé, une erreur technique est survenue. Veuillez réessayer."
            }, status=500)        



@method_decorator(csrf_exempt, name='dispatch')
class RepetiteurChatSendView(LoginRequiredMixin, View):
    """Vue qui gère les messages POST du chat pédagogique"""
    def post(self, request):
        question = request.POST.get("question")
        if not question:
            return JsonResponse({"status": "error", "error": "Question vide."})

        # Récupérer les contenus similaires dans la base vectorielle
        context_docs = search_similar_content(question)
        context = "\n\n".join(context_docs)

        # Générer la réponse basée sur le contexte
        prompt = f"""
        Tu es MrKarfour, un répétiteur pédagogique intelligent.
        Contexte : {context}
        Question : {question}
        Réponds de façon claire, adaptée au niveau de l'élève.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.choices[0].message.content.strip()

        return JsonResponse({
            "status": "success",
            "reponse": answer,
            "niveau_adapte": "Réponse personnalisée"
        })






class TestRepetiteurView(View):
    """Vue temporaire pour tester le répétiteur IA"""
    template_name = 'repetiteur_ia/test_repetiteur.html'

    def get(self, request):
        """Affiche la page de test"""
        return render(request, self.template_name)

    def post(self, request):
        """Teste le répétiteur IA avec une question"""
        try:
            question = request.POST.get('question', 'Test')
            
            # Informations de test pour un élève
            eleve_info = {
                'niveau': 'Collège',
                'classe': '4ème', 
                'nom_complet': 'Élève Test'
            }
            
            # Appel au répétiteur IA
            reponse = repondre_au_repetiteur(
                question=question,
                contexte_pedagogique={},
                niveau_eleve='Collège'
            )
            
            # Réponse JSON
            return JsonResponse({
                'question': question,
                'reponse': reponse,
                'status': 'success'
            })
            
        except Exception as e:
            print(f"Erreur test répétiteur: {e}")
            return JsonResponse({
                'error': str(e), 
                'status': 'error'
            }, status=500)


class ListeNotificationsView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'gestionnaire/notifications.html'
    context_object_name = 'notifications'
    
    def get_queryset(self):
        return Notification.objects.filter(
            utilisateur=self.request.user
        ).order_by('-date_creation')

class MarquerNotificationLueView(LoginRequiredMixin, View):
    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, utilisateur=request.user)
        notification.lue = True
        notification.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        return redirect('notifications')

class SupprimerNotificationView(LoginRequiredMixin, View):
    def post(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, utilisateur=request.user)
        notification.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        return redirect('notifications')


@method_decorator(require_POST, name='dispatch')
class MarquerToutesNotificationsLuesView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(utilisateur=request.user, lue=False).update(lue=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        messages.success(request, "Toutes les notifications ont été marquées comme lues.")
        return redirect('notifications')


class SoumettreCoursView(LoginRequiredMixin, View):
    """Vue pour soumettre un cours (texte ou fichier) avec génération automatique de quiz"""
    
    def get(self, request):
        """Affiche le formulaire de soumission de cours"""
        try:
            # Récupérer les sessions disponibles pour l'élève
            sessions = SessionRevisionProgrammee.objects.filter(
                eleve=request.user.eleve,
                date_programmation__gte=timezone.now() - timedelta(days=1)
            ).order_by('date_programmation')[:10]
            
            # Récupérer les matières disponibles
            matieres = EmploiDuTemps.objects.filter(
                eleve=request.user.eleve, 
                actif=True
            ).values_list('matiere', flat=True).distinct()
            
            context = {
                'sessions': sessions,
                'matieres': matieres,
                'form': SoumissionCoursForm()
            }
            return render(request, 'repetiteur_ia/soumettre_cours.html', context)
            
        except Exception as e:
            print(f"Erreur chargement formulaire soumission: {e}")
            messages.error(request, "Erreur lors du chargement du formulaire.")
            return redirect('tableau_sessions')
    
    def post(self, request):
        """Traite la soumission du cours"""
        try:
            session_id = request.POST.get('session_id')
            type_soumission = request.POST.get('type_soumission')
            matiere = request.POST.get('matiere')
            matiere_autre = request.POST.get('matiere_autre', '')
            contenu_texte = request.POST.get('contenu_texte', '')
            fichier = request.FILES.get('fichier')
            generer_quiz_auto = request.POST.get('generer_quiz_auto') == 'true'
            
            eleve = request.user.eleve
            
            # Utiliser la matière "autre" si spécifiée
            if matiere == 'autre' and matiere_autre:
                matiere = matiere_autre
            
            # Créer ou récupérer la session
            session = None
            if session_id:
                try:
                    session = SessionRevisionProgrammee.objects.get(id=session_id, eleve=eleve)
                except SessionRevisionProgrammee.DoesNotExist:
                    pass
            
            # Si pas de session, créer une soumission générale
            if not session:
                # Trouver ou créer un emploi du temps pour cette matière
                emploi_temps = self._get_or_create_emploi_temps(eleve, matiere)
                
                # Créer une session ad-hoc
                session = SessionRevisionProgrammee.objects.create(
                    eleve=eleve,
                    emploi_temps=emploi_temps,
                    titre=f"Soumission {matiere}",
                    date_programmation=timezone.now(),
                    duree_prevue=30,
                    objectifs=f"Révision du cours de {matiere}",
                    statut='en_cours'
                )
            
            # Créer la soumission
            soumission = SoumissionCours.objects.create(
                session=session,
                type_soumission=type_soumission,
                contenu_texte=contenu_texte,
                fichier=fichier
            )
            
            # Traiter la soumission avec IA pour générer un résumé
            resume_automatique = self._traiter_soumission_ia(soumission)
            
            # Générer automatiquement un quiz si demandé
            quiz_genere = None
            if generer_quiz_auto:
                quiz_genere = self._generer_quiz_automatique(soumission, eleve)
            
            # Générer la réponse automatique de MrKarfour
            reponse_mrkarfour = self._generer_reponse_mrkarfour(soumission, resume_automatique, quiz_genere, eleve)
            
            # Sauvegarder la réponse dans l'historique des conversations
            self._sauvegarder_reponse_mrkarfour(request.user, session, reponse_mrkarfour, soumission)
            
            # Si c'est une requête AJAX, retourner JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response_data = {
                    'status': 'success',
                    'message': 'Cours soumis avec succès ! MrKarfour va vous aider à le réviser.',
                    'session_id': session.id,
                    'soumission_id': soumission.id,
                    'quiz_genere': bool(quiz_genere),
                    'reponse_mrkarfour': reponse_mrkarfour,
                    'resume_automatique': resume_automatique
                }
                
                # Ajouter les infos du quiz si généré
                if quiz_genere:
                    response_data.update({
                        'quiz_id': quiz_genere.id,
                        'quiz_titre': quiz_genere.titre,
                        'quiz_url': reverse('cours:quiz_detail', kwargs={'pk': quiz_genere.id})
                    })
                
                return JsonResponse(response_data)
            else:
                # Si c'est une soumission normale, rediriger vers le chat avec la session
                messages.success(request, 'Cours soumis avec succès ! MrKarfour a analysé votre contenu.')
                return redirect(f"{reverse('repetiteur_ia')}?session={session.id}")
            
        except Exception as e:
            print(f"Erreur soumission cours: {e}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': 'Erreur lors de la soumission du cours.'
                }, status=500)
            else:
                messages.error(request, 'Erreur lors de la soumission du cours.')
                return redirect('soumettre_cours')

    def _get_or_create_emploi_temps(self, eleve, matiere):
        """Trouve ou crée un emploi du temps pour l'élève et la matière"""
        try:
            # Essayer de trouver un emploi du temps existant pour cette matière
            emploi_temps = EmploiDuTemps.objects.filter(
                eleve=eleve, 
                matiere=matiere,
                actif=True
            ).first()
            
            if emploi_temps:
                return emploi_temps
            
            # Sinon, chercher n'importe quel emploi du temps actif
            emploi_temps = EmploiDuTemps.objects.filter(
                eleve=eleve,
                actif=True
            ).first()
            
            if emploi_temps:
                return emploi_temps
            
            # Si aucun emploi du temps n'existe, en créer un par défaut
            from datetime import time
            
            emploi_temps = EmploiDuTemps.objects.create(
                eleve=eleve,
                matiere=matiere,
                jour_semaine='lundi',
                heure_debut=time(17, 0),  # 17h00
                heure_fin=time(18, 0),    # 18h00
                actif=True,
                description=f"Emploi du temps créé automatiquement pour {matiere}"
            )
            
            return emploi_temps
            
        except Exception as e:
            print(f"Erreur création emploi du temps: {e}")
            # En cas d'erreur, créer un emploi du temps minimal
            from datetime import time
            
            return EmploiDuTemps.objects.create(
                eleve=eleve,
                matiere=matiere,
                jour_semaine='lundi',
                heure_debut=time(17, 0),
                heure_fin=time(18, 0),
                actif=True
            )

    def _traiter_soumission_ia(self, soumission):
        """Utilise l'IA pour analyser la soumission et générer un résumé"""
        try:
            contenu = ""
            if soumission.type_soumission == 'texte':
                contenu = soumission.contenu_texte
            elif soumission.type_soumission == 'fichier' and soumission.fichier:
                # Pour l'instant, on utilise juste le nom du fichier
                contenu = f"Fichier soumis: {soumission.fichier.name}"
            
            if not contenu:
                return "Aucun contenu à analyser."
            
            # Générer le résumé avec l'IA
            prompt = f"""
            En tant qu'assistant pédagogique MrKarfour, analyse ce contenu de cours et génère un résumé structuré :
            
            CONTENU À ANALYSER:
            {contenu[:4000]}
            
            STRUCTURE TA RÉPONSE AVEC:
            1. 📝 **Points clés** (les concepts les plus importants)
            2. 🎯 **Objectifs d'apprentissage** (ce que l'élève devrait maîtriser)
            3. 💡 **Conseils de révision** (méthodes pour bien retenir)
            4. ❓ **Questions de réflexion** (pour tester la compréhension)
            
            Sois encourageant et pédagogique !
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            resume = response.choices[0].message.content.strip()
            soumission.resume_automatique = resume
            soumission.save()
            
            return resume
            
        except Exception as e:
            print(f"Erreur traitement IA soumission: {e}")
            resume_erreur = "Je vais analyser votre contenu et vous proposer des exercices adaptés. En attendant, n'hésitez pas à me poser des questions sur ce cours !"
            soumission.resume_automatique = resume_erreur
            soumission.save()
            return resume_erreur

    def _generer_reponse_mrkarfour(self, soumission, resume_automatique, quiz_genere, eleve):
        """Génère une réponse personnalisée de MrKarfour après soumission"""
        try:
            nom_eleve = eleve.user.first_name or eleve.user.username
            matiere = soumission.session.emploi_temps.matiere if soumission.session.emploi_temps else "cette matière"
            
            prompt = f"""
            Tu es MrKarfour, un répétiteur pédagogique bienveillant et encourageant.
            
            CONTEXTE:
            - Élève: {nom_eleve}
            - Matière: {matiere}
            - Type de soumission: {soumission.type_soumission}
            - Quiz généré: {"Oui" if quiz_genere else "Non"}
            
            RÉSUMÉ GÉNÉRÉ:
            {resume_automatique[:1000]}
            
            TÂCHE:
            Écris une réponse chaleureuse et motivante pour accueillir la soumission de l'élève.
            
            TON MESSAGE DOIT:
            1. 🎉 Féliciter l'élève pour sa démarche proactive
            2. 📚 Résumer brièvement ce que tu as compris du contenu
            3. 🎯 Proposer des pistes de révision ou des questions à explorer
            4. 💬 Inviter l'élève à interagir avec toi
            5. 🔍 Mentionner le quiz si il a été généré
            
            Sois naturel, amical et pédagogique. Utilise des émojis avec modération.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Erreur génération réponse MrKarfour: {e}")
            return f"🎉 Bravo {eleve.user.first_name or 'cher élève'} ! J'ai bien reçu ton cours de {soumission.session.emploi_temps.matiere if soumission.session.emploi_temps else 'cette matière'}. Je suis là pour t'aider à le réviser et répondre à toutes tes questions. N'hésite pas à me demander des explications ou des exercices ! 📚✨"

    def _sauvegarder_reponse_mrkarfour(self, utilisateur, session, reponse, soumission):
        """Sauvegarde la réponse de MrKarfour dans l'historique des conversations"""
        try:
            from .models import HistoriqueConversation
            
            HistoriqueConversation.objects.create(
                utilisateur=utilisateur,
                session=session,
                type_conversation='soumission_cours',
                question=f"Soumission de cours: {soumission.type_soumission}",
                reponse=reponse,
                contexte_utilise={
                    'soumission_id': soumission.id,
                    'matiere': session.emploi_temps.matiere if session.emploi_temps else 'Non spécifiée',
                    'type_soumission': soumission.type_soumission,
                    'timestamp': timezone.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Erreur sauvegarde historique MrKarfour: {e}")

    def _generer_quiz_automatique(self, soumission, eleve):
        """Génère automatiquement un quiz à partir de la soumission"""
        try:
            from cours.models import Quiz
            from repetiteur_ia.utils import generer_quiz_ia
            
            # Créer un objet cours temporaire pour la génération
            class CoursTemp:
                def __init__(self, titre, matiere, contenu):
                    self.titre = titre
                    self.matiere = matiere
                    self.contenu = contenu
            
            # Déterminer le titre et la matière du cours
            titre = f"Quiz - {soumission.titre or 'Révision'}"
            matiere = soumission.matiere or 'Général'
            contenu = soumission.contenu_texte or str(soumission.fichier.name) if soumission.fichier else ''
            
            cours_temp = CoursTemp(titre, matiere, contenu)
            
            # Générer les questions avec l'IA
            questions_ia = generer_quiz_ia(cours_temp)
            
            if not questions_ia:
                print("❌ Aucune question générée par l'IA")
                return None
            
            # Créer le quiz
            quiz = Quiz.objects.create(
                titre=titre,
                description=f"Quiz généré automatiquement à partir de la soumission: {soumission.titre}",
                matiere=matiere,
                created_by=eleve.user,
                duree_minutes=15,  # Durée par défaut
                est_actif=True
            )
            
            # Ajouter les questions au quiz
            from cours.models import Question
            for i, q_data in enumerate(questions_ia):
                if isinstance(q_data, dict) and 'question' in q_data and 'options' in q_data:
                    question = Question.objects.create(
                        quiz=quiz,
                        texte=q_data['question'],
                        ordre=i + 1,
                        type_question='qcm'
                    )
                    
                    # Ajouter les options
                    for j, option_text in enumerate(q_data['options']):
                        from cours.models import Option
                        Option.objects.create(
                            question=question,
                            texte=option_text,
                            est_correcte=(option_text == q_data.get('reponse_correcte')),
                            ordre=j + 1
                        )
            
            # Associer le quiz à la soumission
            soumission.quiz_associe = quiz
            soumission.save()
            
            print(f"✅ Quiz généré avec succès: {quiz.titre} ({quiz.questions.count()} questions)")
            return quiz
            
        except Exception as e:
            print(f"❌ Erreur génération quiz automatique: {e}")
            return None




class DemarrerSessionView(LoginRequiredMixin, View):
    """Démarre une session de révision programmée"""
    
    def post(self, request, session_id):
        try:
            session = SessionRevisionProgrammee.objects.get(id=session_id, eleve=request.user.eleve)
            session.statut = 'en_cours'
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'redirect_url': f"{reverse('repetiteur_chat')}?session={session.id}"
            })
            
        except SessionRevisionProgrammee.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Session non trouvée.'
            }, status=404)


class TerminerSessionView(LoginRequiredMixin, View):
    """Termine une session de révision et génère un quiz automatique"""
    
    def post(self, request, session_id):
        try:
            session = SessionRevisionProgrammee.objects.get(id=session_id, eleve=request.user.eleve)
            session.statut = 'terminee'
            session.save()
            
            # Générer automatiquement un quiz si aucun n'est associé
            quiz_genere = None
            if not session.quiz_genere:
                quiz_genere = self._generer_quiz_session(session, request.user.eleve)
                if quiz_genere:
                    session.quiz_genere = quiz_genere
                    session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Session terminée avec succès.',
                'quiz_genere': bool(quiz_genere),
                'quiz_id': quiz_genere.id if quiz_genere else None,
                'quiz_url': reverse('cours:quiz_detail', kwargs={'pk': quiz_genere.id}) if quiz_genere else None
            })
            
        except SessionRevisionProgrammee.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Session non trouvée.'
            }, status=404)
    
    def _generer_quiz_session(self, session, eleve):
        """Génère un quiz basé sur le contenu de la session"""
        try:
            from cours.models import Quiz
            from repetiteur_ia.utils import generer_quiz_ia
            
            # Récupérer les soumissions de la session
            soumissions = session.soumissions.all()
            if not soumissions.exists():
                return None
            
            # Combiner le contenu de toutes les soumissions
            contenu_combine = ""
            matiere = session.emploi_temps.matiere if session.emploi_temps else 'Général'
            
            for soumission in soumissions:
                if soumission.contenu_texte:
                    contenu_combine += f"\n{soumission.contenu_texte}"
            
            if not contenu_combine.strip():
                return None
            
            # Créer un objet cours temporaire
            class CoursTemp:
                def __init__(self, titre, matiere, contenu):
                    self.titre = titre
                    self.matiere = matiere
                    self.contenu = contenu
            
            titre = f"Quiz - {session.titre or 'Révision de ' + matiere}"
            cours_temp = CoursTemp(titre, matiere, contenu_combine)
            
            # Générer les questions avec l'IA
            questions_ia = generer_quiz_ia(cours_temp)
            
            if not questions_ia:
                return None
            
            # Créer le quiz
            quiz = Quiz.objects.create(
                titre=titre,
                description=f"Quiz généré automatiquement après la session de révision: {session.titre}",
                matiere=matiere,
                created_by=eleve.user,
                duree_minutes=20,
                est_actif=True
            )
            
            # Ajouter les questions au quiz
            from cours.models import Question
            for i, q_data in enumerate(questions_ia):
                if isinstance(q_data, dict) and 'question' in q_data and 'options' in q_data:
                    question = Question.objects.create(
                        quiz=quiz,
                        texte=q_data['question'],
                        ordre=i + 1,
                        type_question='qcm'
                    )
                    
                    # Ajouter les options
                    for j, option_text in enumerate(q_data['options']):
                        from cours.models import Option
                        Option.objects.create(
                            question=question,
                            texte=option_text,
                            est_correcte=(option_text == q_data.get('reponse_correcte')),
                            ordre=j + 1
                        )
            
            print(f"✅ Quiz de session généré: {quiz.titre} ({quiz.questions.count()} questions)")
            return quiz
            
        except Exception as e:
            print(f"❌ Erreur génération quiz session: {e}")
            return None

# Dans repetiteur_ia/views.py
class ProgrammerSessionsView(LoginRequiredMixin, View):
    """Vue pour programmer les sessions automatiquement"""
    
    def get(self, request):
        # Ajouter des statistiques pour l'affichage
        from .models import SessionRevisionProgrammee
        
        sessions = SessionRevisionProgrammee.objects.filter(eleve=request.user.eleve)
        context = {
            'sessions_planifiees': sessions.filter(statut='planifie').count(),
            'sessions_terminees': sessions.filter(statut='termine').count(),
            'total_sessions': sessions.count(),
        }
        return render(request, 'repetiteur_ia/programmer_sessions.html', context)
    
    def post(self, request):
        try:
            
            # Capturer la sortie de la commande
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()
            
            # Exécuter la commande
            call_command('programmer_sessions')
            
            # Récupérer la sortie
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            
            messages.success(request, "Sessions programmées avec succès !")
            return JsonResponse({
                'status': 'success',
                'message': 'Sessions programmées automatiquement',
                'output': output
            })
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la programmation: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'error': str(e)
            }, status=500)
        

class TableauSessionsView(LoginRequiredMixin, ListView):
    """Tableau de bord des sessions de révision"""
    model = SessionRevisionProgrammee
    template_name = 'repetiteur_ia/tableau_sessions.html'
    context_object_name = 'sessions'
    
    def get_queryset(self):
        return SessionRevisionProgrammee.objects.filter(
            eleve=self.request.user.eleve
        ).order_by('-date_programmation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = context['sessions']
        
        # Statistiques basées sur le champ 'statut'
        context['sessions_planifiees'] = sessions.filter(statut='planifie')
        context['sessions_terminees'] = sessions.filter(statut='termine')
        context['sessions_annulees'] = sessions.filter(statut='annule')
        
        return context
    


class GestionEmploiDuTempsView(LoginRequiredMixin, ListView):
    model = EmploiDuTemps
    template_name = 'gestionnaire/emploi_du_temps.html'
    context_object_name = 'emplois'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Vérification d'accès pour les élèves
        if getattr(user, 'type_utilisateur', None) == 'élève':
            try:
                eleve = Eleve.objects.get(user=user)
                paiement_actif = (
                    Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET)
                    .order_by('-date_paiement')
                    .first()
                )

                abonnement_valide = (
                    paiement_actif and
                    paiement_actif.date_debut_abonnement <= timezone.now().date() <= paiement_actif.date_fin_abonnement
                )

                if not abonnement_valide:
                    messages.warning(request, "Votre abonnement est expiré ou inactif. Veuillez souscrire pour accéder à votre emploi du temps.")
                    return redirect('abonnements')

            except Eleve.DoesNotExist:
                messages.error(request, "Profil élève introuvable.")
                return redirect('profil')

        # Vérification pour les parents
        elif getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=user)
                enfants = parent.eleves.all()

                abonnement_valide = any(
                    Paiement.objects.filter(
                        eleve=e, statut=Paiement.STATUT_COMPLET,
                        date_debut_abonnement__lte=timezone.now().date(),
                        date_fin_abonnement__gte=timezone.now().date()
                    ).exists()
                    for e in enfants
                )

                if not abonnement_valide:
                    messages.warning(request, "Aucun enfant avec abonnement actif. Veuillez souscrire pour accéder à l'emploi du temps.")
                    return redirect('abonnements')

            except Parent.DoesNotExist:
                messages.error(request, "Profil parent introuvable.")
                return redirect('profil')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=user)
                enfants = parent.eleves.all()
                return EmploiDuTemps.objects.filter(eleve__in=enfants).order_by('jour_semaine', 'heure_debut')
            except Parent.DoesNotExist:
                return EmploiDuTemps.objects.none()
        else:
            try:
                eleve = Eleve.objects.get(user=user)
                return EmploiDuTemps.objects.filter(eleve=eleve).order_by('jour_semaine', 'heure_debut')
            except Eleve.DoesNotExist:
                return EmploiDuTemps.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jours_ordre = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
        emplois = list(self.get_queryset())
        emplois_par_jour = {j: [] for j in jours_ordre}
        for e in emplois:
            key = getattr(e, 'jour_semaine', '').lower()
            if key in emplois_par_jour:
                emplois_par_jour[key].append(e)
        context['emplois_par_jour'] = emplois_par_jour
        context['jours_ordre'] = jours_ordre
        return context



class AjouterEmploiDuTempsView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'gestionnaire/form_emploi_du_temps.html'
    success_message = "Créneau ajouté avec succès."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Ajouter'

        if getattr(self.request.user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=self.request.user)
                context['enfants'] = parent.eleves.all()
            except Parent.DoesNotExist:
                context['enfants'] = None
        return context

    def form_valid(self, form):
        eleve_obj = None
        eleve_id = self.request.POST.get('eleve_id')

        if eleve_id:
            try:
                eleve_obj = Eleve.objects.get(pk=int(eleve_id))
            except (Eleve.DoesNotExist, ValueError):
                pass

        if not eleve_obj:
            try:
                eleve_obj = Eleve.objects.get(user=self.request.user)
            except Eleve.DoesNotExist:
                eleve_obj = None

        if not eleve_obj:
            form.add_error(None, "Impossible de déterminer l'élève lié à ce créneau.")
            return self.form_invalid(form)

        form.instance.eleve = eleve_obj

        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Erreur lors de l'enregistrement. Réessayez.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('tableau_de_bord') + '#emploi-du-temps'


class ModifierEmploiDuTempsView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = EmploiDuTemps
    form_class = EmploiDuTempsForm
    template_name = 'gestionnaire/form_emploi_du_temps.html'
    success_message = "Créneau modifié."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Modifier'
        if getattr(self.request.user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=self.request.user)
                context['enfants'] = parent.eleves.all()
            except Parent.DoesNotExist:
                context['enfants'] = None
        return context

    def get_success_url(self):
        return reverse('tableau_de_bord') + '#emploi-du-temps'

    def get_queryset(self):
        # restreindre édition aux créneaux de l'utilisateur / ses enfants
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=user)
                return qs.filter(cours__eleves__in=parent.eleves.all())
            except Parent.DoesNotExist:
                return qs.none()
        try:
            eleve = Eleve.objects.get(user=user)
            return qs.filter(eleve=eleve)
        except Eleve.DoesNotExist:
            return qs.none()


class SupprimerEmploiDuTempsView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = EmploiDuTemps
    template_name = 'gestionnaire/supprimer_emploi_du_temps.html'
    success_message = "Créneau supprimé."

    def get_success_url(self):
        return reverse('tableau_de_bord') + '#emploi-du-temps'

    def get_queryset(self):
        # restreindre suppression aux créneaux de l'utilisateur / ses enfants
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = Parent.objects.get(user=user)
                return qs.filter(cours__eleves__in=parent.eleves.all())
            except Parent.DoesNotExist:
                return qs.none()
        try:
            eleve = Eleve.objects.get(user=user)
            return qs.filter(eleve=eleve)
        except Eleve.DoesNotExist:
            return qs.none()

class ParametresView(LoginRequiredMixin, TemplateView):
    template_name = 'gestionnaire/parametres.html'
    
    def post(self, request):
        # Gérer la modification des paramètres
        email_notifications = request.POST.get('email_notifications') == 'on'
        request.user.email_notifications = email_notifications
        request.user.save()
        
        from django.contrib import messages
        messages.success(request, "Paramètres mis à jour avec succès.")
        return redirect('parametres')

class AideView(LoginRequiredMixin, TemplateView):
    template_name = 'gestionnaire/aide.html'

@method_decorator(require_POST, name='dispatch')
class MarquerToutesNotificationsLuesView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(utilisateur=request.user, lue=False).update(lue=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        messages.success(request, "Toutes les notifications ont été marquées comme lues.")
        return redirect('notifications')

class NotificationDetailView(LoginRequiredMixin, DetailView):
    model = Notification
    template_name = 'gestionnaire/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user)
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Marquer la notification comme lue lorsqu'elle est visualisée
        notification = self.object
        if not notification.lue:
            notification.lue = True
            notification.save()
        
        return response

class fonctionnalitesView(TemplateView):
    template_name = 'features.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class comment_ca_marcheView(TemplateView):
    template_name = 'how_it_works.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class a_proposView(TemplateView):
    template_name = 'about.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class contactView(TemplateView):
    template_name = 'contact.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


    template_name = 'repetiteur_ia/chat.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # élève avec abonnement actif
        if getattr(user, 'type_utilisateur', None) == 'élève':
            try:
                eleve = Eleve.objects.get(user=user)
                if getattr(eleve, 'abonnement_actif', False):
                    return super().dispatch(request, *args, **kwargs)
                # fallback : vérifier paiements réussis récents
                dernier_paiement = Paiement.objects.filter(eleve=eleve, statut=Paiement.STATUT_COMPLET).order_by('-date_paiement').first()
                if dernier_paiement:
                    return super().dispatch(request, *args, **kwargs)
                messages.info(request, "Souscrivez pour accéder au répétiteur IA.")
                return redirect('abonnements')
            except Eleve.DoesNotExist:
                messages.error(request, "Profil élève introuvable.")
                return redirect('profil')

        # parent : si au moins un enfant actif -> ok
        if getattr(user, 'type_utilisateur', None) == 'parent':
            try:
                parent = user.parent
                enfants = parent.eleves.all()
                if any(getattr(e, 'abonnement_actif', False) for e in enfants):
                    return super().dispatch(request, *args, **kwargs)
            except:
                pass
            messages.info(request, "Aucun enfant avec abonnement actif.")
            return redirect('profil')

        messages.error(request, "Accès non autorisé.")
        return redirect('accueil')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # tenter salutation (pour élève ou premier enfant actif du parent)
        try:
            if getattr(self.request.user, 'type_utilisateur', None) == 'élève':
                eleve = Eleve.objects.get(user=self.request.user)
                ctx['salutation'] = generer_salutation_eleve(eleve)
            else:
                parent = self.request.user.parent
                actif = next((e for e in parent.eleves.all() if getattr(e, 'abonnement_actif', False)), None)
                if actif:
                    ctx['salutation'] = generer_salutation_eleve(actif)
                else:
                    ctx['salutation'] = "Bonjour, bienvenue sur Mrkarfour."
        except Exception:
            ctx['salutation'] = "Bonjour, bienvenue sur Mrkarfour."
        return ctx