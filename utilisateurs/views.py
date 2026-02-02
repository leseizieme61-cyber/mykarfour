from django.views.generic import CreateView, View
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
import uuid
from django.utils import timezone
from django.db.models import Avg, Sum, Max, Min, Count

from cours.models import CoursCoursEleves, Evaluation, QuizAttempt, Cours, Quiz
from utilisateurs.models import Utilisateur, Eleve, Parent, Professeur
from repetiteur_ia.models import RappelRevision
from utilisateurs.forms import InscriptionForm, ConnexionForm, EleveProfilForm, ParentProfilForm, ProfesseurProfilForm, LienParentEleveForm, ParentNotificationsForm


class ProfilView(LoginRequiredMixin, View):
    
    def get_template_name(self, user):
        """Retourne le template approprié selon le type d'utilisateur"""
        if user.type_utilisateur == 'professeur':
            return 'utilisateurs/profil_professeur.html'
        elif user.type_utilisateur == 'parent':
            return 'utilisateurs/profil_parent.html'
        else:
            return 'utilisateurs/profil.html'

    def get(self, request):
        template_name = self.get_template_name(request.user)
        context = self._get_context_utilisateur(request.user)
        return render(request, template_name, context)

    def post(self, request):
        template_name = self.get_template_name(request.user)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        try:
            if request.user.type_utilisateur == 'élève':
                profil = Eleve.objects.get(user=request.user)
                form = EleveProfilForm(request.POST, instance=profil)
                if form.is_valid():
                    form.save()
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': "Profil mis à jour."})
                    messages.success(request, "Votre profil a été mis à jour.")
                    return redirect('profil')
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
                    else:
                        context = self._get_context_utilisateur(request.user, form=form)
                        return render(request, template_name, context)

            elif request.user.type_utilisateur == 'parent':
                profil = Parent.objects.get(user=request.user)
                
                # Identifier quel formulaire a été soumis
                if 'notifications_quotidiennes' in request.POST:
                    # Formulaire de notifications
                    notifications_form = ParentNotificationsForm(request.POST, instance=profil)
                    if notifications_form.is_valid():
                        notifications_form.save()
                        if is_ajax:
                            return JsonResponse({'success': True, 'message': "Préférences de notifications mises à jour."})
                        messages.success(request, "Préférences de notifications mises à jour.")
                        return redirect('profil')
                    else:
                        context = self._get_context_utilisateur(
                            request.user, 
                            notifications_form=notifications_form
                        )
                        if is_ajax:
                            return JsonResponse({'success': False, 'errors': notifications_form.errors}, status=400)
                        return render(request, template_name, context)
                
                elif 'code_eleve' in request.POST:
                    # Formulaire de lien parent-élève
                    lien_form = LienParentEleveForm(request.POST, parent=profil)
                    if lien_form.is_valid():
                        try:
                            eleve = lien_form.save(profil)
                            if is_ajax:
                                return JsonResponse({'success': True, 'message': f"L'élève {eleve} a été lié."})
                            messages.success(request, f"L'élève {eleve} a été lié à votre compte.")
                            return redirect('profil')
                        except Exception as e:
                            lien_form.add_error(None, str(e))
                            context = self._get_context_utilisateur(request.user, lien_form=lien_form)
                            if is_ajax:
                                return JsonResponse({'success': False, 'errors': lien_form.errors}, status=400)
                            return render(request, template_name, context)
                    else:
                        context = self._get_context_utilisateur(request.user, lien_form=lien_form)
                        if is_ajax:
                            return JsonResponse({'success': False, 'errors': lien_form.errors}, status=400)
                        return render(request, template_name, context)
                
                else:
                    # Formulaire de profil parent
                    form = ParentProfilForm(request.POST, instance=profil)
                    if form.is_valid():
                        form.save()
                        if is_ajax:
                            return JsonResponse({'success': True, 'message': "Profil parent mis à jour."})
                        messages.success(request, "Votre profil a été mis à jour.")
                        return redirect('profil')
                    else:
                        context = self._get_context_utilisateur(request.user, form=form)
                        if is_ajax:
                            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
                        return render(request, template_name, context)
                    
            elif request.user.type_utilisateur == 'professeur':
                profil = Professeur.objects.get(user=request.user)
                form = ProfesseurProfilForm(request.POST, request.FILES, instance=profil)
                if form.is_valid():
                    form.save()
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': "Profil professeur mis à jour."})
                    messages.success(request, "Votre profil a été mis à jour avec succès.")
                    return redirect('profil')
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
                    else:
                        context = self._get_context_utilisateur(request.user, form=form)
                        return render(request, template_name, context)

            return redirect('profil')

        except (Eleve.DoesNotExist, Parent.DoesNotExist, Professeur.DoesNotExist):
            if is_ajax:
                return JsonResponse({'success': False, 'message': "Profil non trouvé."}, status=404)
            messages.error(request, "Profil non trouvé.")
            return redirect('accueil')

    def _get_context_utilisateur(self, user, form=None, lien_form=None, notifications_form=None):
        """
        Prépare le contexte pour l'affichage du profil
        """
        context = {}
        request = getattr(self, 'request', None)
        
        try:
            if user.type_utilisateur == 'élève':
                profil = Eleve.objects.get(user=user)
                form = form or EleveProfilForm(instance=profil)
                context.update({
                    'profil': profil,
                    'form': form
                })
            
            elif user.type_utilisateur == 'parent':
                profil = Parent.objects.get(user=user)
                form = form or ParentProfilForm(instance=profil)
                lien_form = lien_form or LienParentEleveForm(parent=profil)
                notifications_form = notifications_form or ParentNotificationsForm(instance=profil)
                enfants = profil.eleves.all()
                
                # Récupérer les données de suivi des enfants
                enfants_data = []
                for eleve in enfants:
                    # Évaluations de l'élève
                    evaluations = Evaluation.objects.filter(eleve=eleve).select_related('cours')
                    
                    # Tous les quiz réalisés (pour les statistiques)
                    quiz_total = QuizAttempt.objects.filter(
                        eleve=eleve, 
                        statut='termine'
                    )
                    
                    # Quiz réussis (score >= 70)
                    quiz_reussis_count = quiz_total.filter(score__gte=70).count()
                    
                    # Quiz récents pour l'affichage (5 derniers)
                    quiz_recents = quiz_total.select_related('quiz').order_by('-date_debut')[:5]
                    
                    # Cours suivis
                    cours_suivis = CoursCoursEleves.objects.filter(eleve=eleve).select_related('cours')
                    
                    # Moyenne générale
                    moyenne = evaluations.aggregate(avg_note=Avg('note'))['avg_note'] if evaluations.exists() else 0
                    
                    # Dernière activité
                    derniere_evaluation = evaluations.order_by('-date_creation').first()
                    dernier_quiz = quiz_total.order_by('-date_debut').first()
                    
                    enfants_data.append({
                        'eleve': eleve,
                        'evaluations_count': evaluations.count(),
                        'quiz_count': quiz_total.count(),  # Total des quiz
                        'cours_count': cours_suivis.count(),
                        'moyenne': round(moyenne, 1) if moyenne else 0,
                        'derniere_evaluation': derniere_evaluation,
                        'dernier_quiz': dernier_quiz,
                        'quiz_reussis': quiz_reussis_count,
                        'quiz_recents': list(quiz_recents),  # Convertir en liste pour éviter les problèmes de queryset
                    })
                
                # Statistiques globales
                stats_parent = self._calculer_statistiques_parent(profil)
                
                # Dernières activités (évaluations et quiz récents)
                dernieres_activites = self._get_dernieres_activites_parent(profil)
                
                # Rapport hebdomadaire
                rapport_hebdo = self._get_rapport_hebdomadaire_parent(profil)
                
                context.update({
                    'profil': profil,
                    'form': form,
                    'lien_form': lien_form,
                    'notifications_form': notifications_form,
                    'enfants': enfants,
                    'enfants_data': enfants_data,
                    'stats_parent': stats_parent,
                    'dernieres_activites': dernieres_activites,
                    'rapport_hebdo': rapport_hebdo,
                })
            
            elif user.type_utilisateur == 'professeur':
                profil = Professeur.objects.get(user=user)
                form = form or ProfesseurProfilForm(instance=profil)
                
                # RÉCUPÉRATION DES COURS RÉELS DU PROFESSEUR
                cours_professeur = Cours.objects.filter(professeur=profil).order_by('-date_creation')
                
                # CALCUL DES STATISTIQUES RÉELLES
                stats = self._calculer_statistiques_professeur(profil, cours_professeur)
                
                context.update({
                    'form': form,
                    'profil': profil,
                    'stats': stats,
                    'cours_professeur': cours_professeur,
                    'cours_count': cours_professeur.count()
                })

        except (Eleve.DoesNotExist, Parent.DoesNotExist, Professeur.DoesNotExist):
            # Création du profil s'il n'existe pas
            if user.type_utilisateur == 'élève':
                profil = Eleve.objects.create(user=user)
                profil.code_parrainage = str(uuid.uuid4())[:8].upper()
                profil.save()
                if request:
                    messages.info(request, "Votre profil élève a été créé. Veuillez le compléter.")
            elif user.type_utilisateur == 'parent':
                profil = Parent.objects.create(user=user)
                if request:
                    messages.info(request, "Votre profil parent a été créé. Veuillez le compléter.")
            elif user.type_utilisateur == 'professeur':
                profil = Professeur.objects.create(user=user)
                if request:
                    messages.info(request, "Votre profil professeur a été créé. Veuillez le compléter.")

        return context

    def _calculer_statistiques_professeur(self, professeur, cours_professeur):
        """
        Calcule les statistiques réelles du professeur
        """
        from django.db.models import Avg
        
        # Nombre de cours actifs
        cours_actifs = cours_professeur.count()
        
        # Nombre total d'élèves inscrits à tous les cours
        total_eleves = 0
        for cours in cours_professeur:
            total_eleves += CoursCoursEleves.objects.filter(cours=cours).count()
        
        # Sessions ce mois (approximation basée sur les cours)
        debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        sessions_mois = cours_professeur.filter(date_creation__gte=debut_mois).count()
        
        # Note moyenne (basée sur les évaluations données par le professeur)
        try:
            evaluations = Evaluation.objects.filter(cours__professeur=professeur)
            if evaluations.exists():
                note_moyenne = round(evaluations.aggregate(avg_note=Avg('note'))['avg_note'] or 0, 1)
            else:
                note_moyenne = "0.0"
        except Exception as e:
            print(f"Erreur calcul note moyenne: {e}")
            note_moyenne = "0.0"
        
        return {
            'cours_actifs': cours_actifs,
            'eleves_total': total_eleves,
            'sessions_mois': sessions_mois,
            'note_moyenne': note_moyenne
        }
    
    def _calculer_statistiques_parent(self, parent):
        """
        Calcule les statistiques pour le parent
        """
        enfants = parent.eleves.all()
        
        if not enfants.exists():
            return {
                'total_enfants': 0,
                'moyenne_generale': 0,
                'total_evaluations': 0,
                'total_quiz': 0,
                'total_cours': 0,
                'quiz_reussis': 0,
                'taux_reussite': 0,
            }
        
        # Récupérer toutes les évaluations des enfants
        evaluations = Evaluation.objects.filter(eleve__in=enfants)
        
        # Récupérer tous les quiz des enfants
        quiz_attempts = QuizAttempt.objects.filter(eleve__in=enfants, statut='termine')
        
        # Cours suivis par les enfants
        cours_suivis = CoursCoursEleves.objects.filter(eleve__in=enfants)
        
        # Moyenne générale de tous les enfants
        moyenne_generale = evaluations.aggregate(avg=Avg('note'))['avg'] or 0
        
        # Taux de réussite aux quiz
        quiz_reussis = quiz_attempts.filter(score__gte=70).count()
        taux_reussite = (quiz_reussis / quiz_attempts.count() * 100) if quiz_attempts.count() > 0 else 0
        
        return {
            'total_enfants': enfants.count(),
            'moyenne_generale': round(moyenne_generale, 1),
            'total_evaluations': evaluations.count(),
            'total_quiz': quiz_attempts.count(),
            'total_cours': cours_suivis.count(),
            'quiz_reussis': quiz_reussis,
            'taux_reussite': round(taux_reussite, 1),
        }
    
    def _get_dernieres_activites_parent(self, parent):
        """
        Récupère les dernières activités de tous les enfants du parent
        """
        from datetime import timedelta
        
        derniere_semaine = timezone.now() - timedelta(days=7)
        activites = []
        
        for eleve in parent.eleves.all():
            # Évaluations récentes
            evaluations = Evaluation.objects.filter(
                eleve=eleve,
                date_creation__gte=derniere_semaine
            ).select_related('cours')[:3]
            
            for eval in evaluations:
                activites.append({
                    'type': 'evaluation',
                    'date': eval.date_creation,
                    'eleve': eleve,
                    'titre': f"Nouvelle évaluation: {eval.cours.titre}",
                    'description': f"{eval.eleve.user.get_full_name()} a reçu {eval.note}/5",
                    'note': eval.note,
                })
            
            # Quiz récents
            quiz = QuizAttempt.objects.filter(
                eleve=eleve,
                date_debut__gte=derniere_semaine,
                statut='termine'
            ).select_related('quiz')[:3]
            
            for attempt in quiz:
                activites.append({
                    'type': 'quiz',
                    'date': attempt.date_debut,
                    'eleve': eleve,
                    'titre': f"Quiz réalisé: {attempt.quiz.titre}",
                    'description': f"{attempt.eleve.user.get_full_name()} a obtenu {attempt.score}%",
                    'score': attempt.score,
                })
        
        # Trier par date (plus récent d'abord)
        activites.sort(key=lambda x: x['date'], reverse=True)
        return activites[:10]
    
    def _get_rapport_hebdomadaire_parent(self, parent):
        """Génère un rapport hebdomadaire pour tous les enfants"""
        from datetime import timedelta
        
        debut_semaine = timezone.now() - timedelta(days=7)
        rapport = {
            'periode': f"Du {debut_semaine.strftime('%d/%m/%Y')} au {timezone.now().strftime('%d/%m/%Y')}",
            'enfants': []
        }
        
        for eleve in parent.eleves.all():
            # Évaluations de la semaine
            evaluations_semaine = Evaluation.objects.filter(
                eleve=eleve,
                date_creation__gte=debut_semaine
            ).select_related('cours')
            
            # Quiz de la semaine
            quiz_semaine = QuizAttempt.objects.filter(
                eleve=eleve,
                date_debut__gte=debut_semaine,
                statut='termine'
            )
            
            # Temps d'étude (approximatif)
            temps_etude = quiz_semaine.aggregate(
                total_temps=Sum('duree_secondes')
            )['total_temps'] or 0
            heures_etude = round(temps_etude / 3600, 1) if temps_etude else 0
            
            # Meilleure note de la semaine
            meilleure_note = evaluations_semaine.aggregate(max_note=Max('note'))['max_note'] if evaluations_semaine.exists() else None
            
            # Score moyen des quiz de la semaine
            quiz_moyen = quiz_semaine.aggregate(avg_score=Avg('score'))['avg_score'] if quiz_semaine.exists() else None
            
            rapport['enfants'].append({
                'eleve': eleve,
                'evaluations_count': evaluations_semaine.count(),
                'quiz_count': quiz_semaine.count(),
                'heures_etude': heures_etude,
                'meilleure_note': meilleure_note,
                'quiz_moyen': quiz_moyen,
            })
        
        return rapport


# =====================================
# VUES POUR LE PARENT
# =====================================

class ParentDashboardView(LoginRequiredMixin, View):
    """Tableau de bord complet pour les parents"""
    
    def get(self, request):
        if getattr(request.user, "type_utilisateur", "") != "parent":
            return HttpResponseForbidden("Accès réservé aux parents.")
        
        try:
            parent = Parent.objects.get(user=request.user)
            
            # Récupérer les données de progression des enfants
            enfants_data = []
            for eleve in parent.eleves.all():
                # Évaluations de l'élève
                evaluations = Evaluation.objects.filter(eleve=eleve).select_related('cours')
                
                # Quiz réalisés
                quiz_total = QuizAttempt.objects.filter(eleve=eleve, statut='termine')
                quiz_recent = quiz_total.select_related('quiz').order_by('-date_debut')[:10]
                
                # Cours suivis
                cours_suivis = CoursCoursEleves.objects.filter(eleve=eleve).select_related('cours')
                
                # Moyenne générale
                moyenne = evaluations.aggregate(avg_note=Avg('note'))['avg_note'] if evaluations.exists() else 0
                
                enfants_data.append({
                    'eleve': eleve,
                    'evaluations': evaluations,
                    'quiz_attempts': list(quiz_recent),
                    'cours_suivis': cours_suivis,
                    'moyenne': round(moyenne, 1) if moyenne else 0,
                    'total_quiz': quiz_total.count(),
                    'total_cours': cours_suivis.count(),
                })
            
            # Statistiques globales
            stats = {
                'total_enfants': parent.eleves.count(),
                'total_evaluations': sum(len(data['evaluations']) for data in enfants_data),
                'total_quiz_realises': sum(data['total_quiz'] for data in enfants_data),
                'moyenne_generale': round(sum(data['moyenne'] for data in enfants_data) / len(enfants_data), 1) if enfants_data else 0,
                'evaluations_total': Evaluation.objects.filter(eleve__in=parent.eleves.all()).count(),
                'quiz_total': QuizAttempt.objects.filter(eleve__in=parent.eleves.all(), statut='termine').count(),
                'rappels_total': RappelRevision.objects.filter(eleve__in=parent.eleves.all(), envoye=True).count(),
            }
            
            # Dernières activités
            toutes_evaluations = []
            tous_quiz = []
            
            for eleve in parent.eleves.all():
                evaluations = Evaluation.objects.filter(
                    eleve=eleve
                ).select_related('cours').order_by('-date_creation')[:5]
                toutes_evaluations.extend(evaluations)
                
                quiz = QuizAttempt.objects.filter(
                    eleve=eleve,
                    statut='termine'
                ).select_related('quiz').order_by('-date_debut')[:5]
                tous_quiz.extend(quiz)
            
            toutes_evaluations.sort(key=lambda x: x.date_creation, reverse=True)
            tous_quiz.sort(key=lambda x: x.date_debut, reverse=True)
            
            context = {
                'parent': parent,
                'enfants': parent.eleves.all(),
                'enfants_data': enfants_data,
                'evaluations_recentes': toutes_evaluations[:10],
                'quiz_recents': tous_quiz[:10],
                'stats': stats,
            }
            
            return render(request, 'utilisateurs/parent_dashboard.html', context)
            
        except Parent.DoesNotExist:
            messages.error(request, "Profil parent introuvable.")
            return redirect('profil')


class ParentEvaluationsDetailView(LoginRequiredMixin, View):
    """Détail des évaluations d'un enfant spécifique"""
    
    def get(self, request, eleve_id):
        if getattr(request.user, "type_utilisateur", "") != "parent":
            return HttpResponseForbidden("Accès réservé aux parents.")
        
        try:
            parent = Parent.objects.get(user=request.user)
            eleve = get_object_or_404(Eleve, id=eleve_id)
            
            if eleve not in parent.eleves.all():
                return HttpResponseForbidden("Cet enfant n'est pas lié à votre compte.")
            
            matiere = request.GET.get('matiere')
            date_debut = request.GET.get('date_debut')
            date_fin = request.GET.get('date_fin')
            
            evaluations = Evaluation.objects.filter(eleve=eleve).select_related('cours')
            
            if matiere:
                evaluations = evaluations.filter(cours__matiere=matiere)
            
            if date_debut:
                evaluations = evaluations.filter(date_creation__gte=date_debut)
            
            if date_fin:
                evaluations = evaluations.filter(date_creation__lte=date_fin)
            
            evaluations = evaluations.order_by('-date_creation')
            
            stats = {
                'moyenne': evaluations.aggregate(avg=Avg('note'))['avg'] or 0,
                'total': evaluations.count(),
                'meilleure_note': evaluations.aggregate(max=Max('note'))['max'] or 0,
                'pire_note': evaluations.aggregate(min=Min('note'))['min'] or 0,
            }
            
            matieres_disponibles = Evaluation.objects.filter(
                eleve=eleve
            ).exclude(
                cours__matiere__isnull=True
            ).exclude(
                cours__matiere__exact=''
            ).values_list('cours__matiere', flat=True).distinct()
            
            context = {
                'parent': parent,
                'eleve': eleve,
                'evaluations': evaluations,
                'stats': stats,
                'matieres_disponibles': matieres_disponibles,
                'matiere_selectionnee': matiere,
                'date_debut': date_debut,
                'date_fin': date_fin,
            }
            
            return render(request, 'utilisateurs/parent_evaluations_detail.html', context)
            
        except Parent.DoesNotExist:
            messages.error(request, "Profil parent introuvable.")
            return redirect('profil')


class ParentQuizDetailView(LoginRequiredMixin, View):
    """Détail des quiz d'un enfant spécifique"""
    
    def get(self, request, eleve_id):
        if getattr(request.user, "type_utilisateur", "") != "parent":
            return HttpResponseForbidden("Accès réservé aux parents.")
        
        try:
            parent = Parent.objects.get(user=request.user)
            eleve = get_object_or_404(Eleve, id=eleve_id)
            
            if eleve not in parent.eleves.all():
                return HttpResponseForbidden("Cet enfant n'est pas lié à votre compte.")
            
            # Récupérer les filtres
            matiere = request.GET.get('matiere', '')
            statut = request.GET.get('statut', '')
            periode = request.GET.get('periode', '')
            
            # Base queryset
            quiz_attempts = QuizAttempt.objects.filter(eleve=eleve).select_related('quiz', 'quiz__cours')
            
            # Appliquer les filtres
            if matiere:
                quiz_attempts = quiz_attempts.filter(quiz__cours__matiere=matiere)
            
            if statut:
                quiz_attempts = quiz_attempts.filter(statut=statut)
            
            if periode:
                from datetime import timedelta
                from django.utils import timezone
                jours = int(periode)
                date_limite = timezone.now() - timedelta(days=jours)
                quiz_attempts = quiz_attempts.filter(date_debut__gte=date_limite)
            
            # Trier par date
            quiz_attempts = quiz_attempts.order_by('-date_debut')
            
            # Calculer les statistiques
            quiz_termines = quiz_attempts.filter(statut='termine')
            moyenne_score = quiz_termines.aggregate(avg=Avg('score'))['avg'] or 0
            
            # Ajouter des propriétés calculées pour chaque tentative
            for attempt in quiz_attempts:
                # Calculer le nombre de questions répondues
                attempt.questions_repondues = attempt.reponses.count()
                
                # Récupérer la matière depuis le cours
                attempt.matiere = attempt.quiz.cours.matiere if attempt.quiz.cours else 'Général'
                
                # Progression des questions
                total_questions = attempt.quiz.questions.count()
                if total_questions > 0:
                    attempt.progress_percent = int((attempt.questions_repondues / total_questions) * 100)
                else:
                    attempt.progress_percent = 0
                
                # Couleurs pour la progression
                if attempt.progress_percent >= 80:
                    attempt.progress_color = 'success'
                elif attempt.progress_percent >= 50:
                    attempt.progress_color = 'warning'
                else:
                    attempt.progress_color = 'danger'
                
                # Couleurs pour le score
                if attempt.score is not None:
                    if attempt.score >= 80:
                        attempt.score_color = 'success'
                    elif attempt.score >= 60:
                        attempt.score_color = 'warning'
                    else:
                        attempt.score_color = 'danger'
                else:
                    attempt.score_color = 'secondary'
                
                # Ajouter le temps passé formaté
                attempt.temps_passe = attempt.get_duree_formatee()
            
            # Matières disponibles pour les filtres
            matieres_disponibles = QuizAttempt.objects.filter(
                eleve=eleve,
                quiz__cours__isnull=False
            ).values_list('quiz__cours__matiere', flat=True).distinct().order_by('quiz__cours__matiere')
            
            # Matières distinctes pour les statistiques
            matieres_distinctes = set()
            for attempt in quiz_attempts:
                if attempt.quiz.cours and attempt.quiz.cours.matiere:
                    matieres_distinctes.add(attempt.quiz.cours.matiere)
            
            context = {
                'parent': parent,
                'eleve': eleve,
                'quiz_attempts': quiz_attempts,
                'moyenne_score': moyenne_score,
                'quiz_termines_count': quiz_termines.count(),
                'matieres_disponibles': matieres_disponibles,
                'matieres_distinctes': matieres_distinctes,
                'matiere': matiere,
                'statut': statut,
                'periode': periode,
            }
            
            return render(request, 'utilisateurs/parent_quiz_detail.html', context)
            
        except Parent.DoesNotExist:
            messages.error(request, "Profil parent introuvable.")
            return redirect('profil')


class UpdateParentNotificationsView(LoginRequiredMixin, View):
    """Met à jour les préférences de notifications du parent"""
    
    def post(self, request):
        if getattr(request.user, "type_utilisateur", "") != "parent":
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)
        
        try:
            parent = Parent.objects.get(user=request.user)
            
            parent.notifications_quotidiennes = request.POST.get('notifications_quotidiennes') == 'on'
            parent.notifications_hebdomadaires = request.POST.get('notifications_hebdomadaires') == 'on'
            parent.notifications_evaluations = request.POST.get('notifications_evaluations') == 'on'
            parent.notifications_quiz = request.POST.get('notifications_quiz') == 'on'
            parent.save()
            
            messages.success(request, "Préférences de notifications mises à jour.")
            return redirect('parent_dashboard')
            
        except Parent.DoesNotExist:
            messages.error(request, "Profil parent introuvable.")
            return redirect('profil')


class GenererRapportParentView(LoginRequiredMixin, View):
    """Génère un rapport pour le parent"""
    
    def get(self, request):
        if getattr(request.user, "type_utilisateur", "") != "parent":
            return HttpResponseForbidden("Accès réservé aux parents.")
        
        try:
            parent = Parent.objects.get(user=request.user)
            
            periode = request.GET.get('periode', 'semaine')
            format = request.GET.get('format', 'html')
            
            from datetime import timedelta
            
            if periode == 'semaine':
                debut = timezone.now() - timedelta(days=7)
            elif periode == 'mois':
                debut = timezone.now() - timedelta(days=30)
            elif periode == 'trimestre':
                debut = timezone.now() - timedelta(days=90)
            else:
                debut = timezone.now() - timedelta(days=7)
            
            evaluations = Evaluation.objects.filter(
                eleve__in=parent.eleves.all(),
                date_creation__gte=debut
            ).select_related('cours', 'eleve')
            
            quiz_attempts = QuizAttempt.objects.filter(
                eleve__in=parent.eleves.all(),
                date_debut__gte=debut
            ).select_related('quiz', 'eleve')
            
            context = {
                'parent': parent,
                'periode': periode,
                'date_debut': debut,
                'date_fin': timezone.now(),
                'evaluations': evaluations,
                'quiz_attempts': quiz_attempts,
                'total_enfants': parent.eleves.count(),
            }
            
            if format == 'pdf':
                return render(request, 'utilisateurs/rapport_parent_pdf.html', context)
            else:
                return render(request, 'utilisateurs/rapport_parent.html', context)
            
        except Parent.DoesNotExist:
            messages.error(request, "Profil parent introuvable.")
            return redirect('profil')


# =====================================
# AUTRES VUES
# =====================================

class ParemetresView(LoginRequiredMixin, View):
    def post(self, request):
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        email_notifications = request.POST.get('email_notifications') in ['on', 'true', '1']
        sms_notifications = request.POST.get('sms_notifications') in ['on', 'true', '1']

        user = request.user
        user.email_notifications = email_notifications
        user.sms_notifications = sms_notifications
        user.save()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': "Préférences mises à jour avec succès."
            })
        else:
            messages.success(request, "Préférences mises à jour.")
            return redirect('profil')


class InscriptionView(CreateView):
    model = Utilisateur
    form_class = InscriptionForm
    template_name = 'utilisateurs/signup.html'
    success_url = reverse_lazy('connexion')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = True
        user.save()

        type_utilisateur = form.cleaned_data.get('type_utilisateur')
        if type_utilisateur == Utilisateur.EST_ELEVE:
            eleve = Eleve.objects.create(user=user)
            eleve.code_parrainage = str(uuid.uuid4())[:8].upper()
            eleve.save()
        elif type_utilisateur == Utilisateur.EST_PARENT:
            Parent.objects.create(user=user)
        elif form.cleaned_data['type_utilisateur'] == 'professeur':
            Professeur.objects.create(user=user)

        messages.success(self.request, "Inscription réussie ! Vous pouvez maintenant vous connecter.")
        return super().form_valid(form)


class ConnexionView(LoginView):
    template_name = 'utilisateurs/login.html'
    form_class = ConnexionForm

    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if user is None:
            messages.error(self.request, "Nom d'utilisateur ou mot de passe incorrect.")
            return super().form_invalid(form)
        login(self.request, user)
        return redirect('profil')


class UpdateNotificationsView(LoginRequiredMixin, View):
    def post(self, request):
        field = request.POST.get('field')
        value = request.POST.get('value') == 'true'
        if field in ['email_notifications', 'sms_notifications', 'push_notifications']:
            setattr(request.user, field, value)
            request.user.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Champ invalide'}, status=400)


class DeconnexionView(LogoutView):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse_lazy('accueil'))


class LierEnfantView(LoginRequiredMixin, SuccessMessageMixin, View):
    template_name = 'utilisateurs/lier_enfant.html'
    success_message = "L'élève a été lié à votre compte avec succès."

    def get(self, request):
        if request.user.type_utilisateur != 'parent':
            return redirect('accueil')
        parent = Parent.objects.get(user=request.user)
        form = LienParentEleveForm(parent=parent)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.type_utilisateur != 'parent':
            return redirect('accueil')
        parent = Parent.objects.get(user=request.user)
        form = LienParentEleveForm(request.POST, parent=parent)
        if form.is_valid():
            form.save(parent)
            return redirect('profil')
        return render(request, self.template_name, {'form': form})


@method_decorator(require_GET, name='dispatch')
class ChargerClassesView(View):
    def get(self, request):
        niveau = request.GET.get('niveau')
        classes = []

        user = request.user
        if user.is_authenticated and niveau:
            niveau_map = {
                'college': Eleve.NIVEAU_COLLEGE,
                'lycee': Eleve.NIVEAU_LYCEE,
                'collège': Eleve.NIVEAU_COLLEGE,
                'lycée': Eleve.NIVEAU_LYCEE,
            }
            niveau_key = niveau.lower().replace('é', 'e')
            niveau_cle = niveau_map.get(niveau_key)

            if niveau_cle == Eleve.NIVEAU_COLLEGE:
                classes = Eleve.CLASSES_COLLEGE
            elif niveau_cle == Eleve.NIVEAU_LYCEE:
                classes = Eleve.CLASSES_LYCEE

        return JsonResponse({'classes': classes})


class CustomPasswordResetView(PasswordResetView):
    template_name = 'utilisateurs/password_reset.html'
    email_template_name = 'utilisateurs/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'utilisateurs/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'utilisateurs/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'utilisateurs/password_reset_complete.html'