from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import Http404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import ValidationError

from repetiteur_ia.models import SoumissionCours, SessionRevisionProgrammee
from .forms import QuizForm, QuestionForm, ChoiceForm, CoursForm
from .models import Cours, Quiz, Evaluation, CoursCoursEleves, EmploiDuTemps, Question, Choice, QuestionAttempt, QuizAttempt, QuizSession
from utilisateurs.models import Professeur, Eleve
import json
from django.db import transaction


class ProfesseurRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = getattr(self.request, "user", None)
        return user and user.is_authenticated and getattr(user, "type_utilisateur", "") == "professeur"
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return HttpResponseForbidden("Accès réservé aux professeurs.")
    

class CoursListView(LoginRequiredMixin, ListView):
    model = Cours
    template_name = "cours/cours_list.html"
    context_object_name = "cours_list"
    paginate_by = 12

    def get_queryset(self):
        # VERSION SIMPLIFIÉE POUR TEST - Retourne TOUS les cours
        queryset = Cours.objects.all()
        print(f"DEBUG - Total cours: {queryset.count()}")
        return queryset.order_by("-date_creation")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Debug info
        print(f"DEBUG - User: {user.username}, Type: {getattr(user, 'type_utilisateur', 'None')}")
        print(f"DEBUG - Cours dans contexte: {context['cours_list'].count()}")
        
        # Matières disponibles
        context['matieres_disponibles'] = Cours.objects.exclude(
            matiere__isnull=True
        ).exclude(
            matiere__exact=''
        ).values_list('matiere', flat=True).distinct().order_by('matiere')
        
        context['matiere_actuelle'] = self.request.GET.get('matiere', '')
        context['niveau_actuel'] = self.request.GET.get('niveau', '')
        
        # Pour les élèves
        if getattr(user, "type_utilisateur", "") == "élève":
            try:
                eleve = Eleve.objects.get(user=user)
                context['niveau_eleve'] = eleve.niveau
                # IDs des cours où l'élève est inscrit
                cours_inscrits_ids = CoursCoursEleves.objects.filter(
                    eleve=eleve
                ).values_list('cours_id', flat=True)
                context['cours_inscrits_ids'] = list(cours_inscrits_ids)
                print(f"DEBUG - Élève inscrit à {len(cours_inscrits_ids)} cours")
            except Eleve.DoesNotExist:
                context['cours_inscrits_ids'] = []
                context['niveau_eleve'] = None
        else:
            context['cours_inscrits_ids'] = []
            context['niveau_eleve'] = None
        
        return context



class CoursDetailView(LoginRequiredMixin, DetailView):
    model = Cours
    template_name = "cours/cours_detail.html"
    context_object_name = "cours"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["quiz_list"] = self.object.quiz.all()
        
        # Ajouter la liste des élèves inscrits pour les professeurs
        if getattr(self.request.user, "type_utilisateur", "") == "professeur":
            try:
                prof = Professeur.objects.get(user=self.request.user)
                if self.object.professeur == prof:
                    inscriptions = CoursCoursEleves.objects.filter(cours=self.object)
                    eleves_inscrits = [inscription.eleve for inscription in inscriptions]
                    ctx['eleves_inscrits'] = eleves_inscrits
                    
                    # Récupérer les évaluations existantes
                    evaluations = Evaluation.objects.filter(cours=self.object)
                    ctx['evaluations'] = {eval.eleve_id: eval for eval in evaluations}
            except Professeur.DoesNotExist:
                pass
        
        # Vérifier si l'élève est inscrit au cours
        if getattr(self.request.user, "type_utilisateur", "") == "élève":
            try:
                eleve = Eleve.objects.get(user=self.request.user)
                est_inscrit = CoursCoursEleves.objects.filter(
                    cours=self.object, 
                    eleve=eleve
                ).exists()
                ctx['est_inscrit'] = est_inscrit
                
                # Récupérer l'évaluation de l'élève s'il y en a une
                try:
                    evaluation = Evaluation.objects.get(cours=self.object, eleve=eleve)
                    ctx['evaluation_eleve'] = evaluation
                except Evaluation.DoesNotExist:
                    ctx['evaluation_eleve'] = None
                    
            except Eleve.DoesNotExist:
                ctx['est_inscrit'] = False
        
        return ctx



class CoursCreateView(LoginRequiredMixin, ProfesseurRequiredMixin, CreateView):
    model = Cours
    form_class = CoursForm  # Utiliser le formulaire personnalisé
    template_name = "cours/cours_form.html"
    success_url = reverse_lazy("cours:list")

    def form_valid(self, form):
        try:
            # Récupérer le profil professeur via la relation OneToOne
            prof = Professeur.objects.get(user=self.request.user)
            form.instance.professeur = prof
            messages.success(self.request, "Cours créé avec succès.")
            return super().form_valid(form)
            
        except Professeur.DoesNotExist:
            messages.error(self.request, "Profil professeur introuvable. Veuillez compléter votre profil.")
            return redirect('profil')



class CoursUpdateView(LoginRequiredMixin, ProfesseurRequiredMixin, UpdateView):
    model = Cours
    fields = ["titre", "matiere", "contenu", "niveau"]
    template_name = "cours/cours_form.html"
    success_url = reverse_lazy("cours:list")

    def dispatch(self, request, *args, **kwargs):
        # Vérifier que le professeur est propriétaire du cours
        self.object = self.get_object()
        prof = getattr(request.user, "professeur_profile", None)
        if not prof or self.object.professeur_id != prof.id:
            return HttpResponseForbidden("Vous n'avez pas le droit de modifier ce cours.")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, "Cours mis à jour avec succès.")
        return super().form_valid(form)

class CoursDeleteView(LoginRequiredMixin, ProfesseurRequiredMixin, DeleteView):
    model = Cours
    template_name = "cours/cours_confirm_delete.html"
    success_url = reverse_lazy("cours:list")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        prof = getattr(request.user, "professeur_profile", None)
        if not prof or self.object.professeur_id != prof.id:
            return HttpResponseForbidden("Vous n'avez pas le droit de supprimer ce cours.")
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cours supprimé avec succès.")
        return super().delete(request, *args, **kwargs)
    

class EleveRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est un élève"""
    def test_func(self):
        user = getattr(self.request, "user", None)
        return user and user.is_authenticated and getattr(user, "type_utilisateur", "") == "élève"
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return HttpResponseForbidden("Accès réservé aux élèves.")


class InscrireEleveView(LoginRequiredMixin, EleveRequiredMixin, View):
    """Vue pour l'inscription d'un élève à un cours"""
    
    def get(self, request, pk):
        """Redirige vers la liste des cours si accès via GET"""
        messages.info(request, "Veuillez utiliser le formulaire d'inscription depuis la liste des cours.")
        return redirect("cours:list")
    
    def post(self, request, pk):
        cours = get_object_or_404(Cours, pk=pk)
        try:
            eleve = Eleve.objects.get(user=request.user)
            
            # Vérifier si l'élève est déjà inscrit
            if CoursCoursEleves.objects.filter(cours=cours, eleve=eleve).exists():
                messages.warning(request, f"Vous êtes déjà inscrit au cours {cours.titre}.")
            else:
                # Créer l'inscription via la table intermédiaire
                CoursCoursEleves.objects.create(cours=cours, eleve=eleve)
                messages.success(request, f"Inscription réussie au cours {cours.titre}.")
                
        except Eleve.DoesNotExist:
            messages.error(request, "Profil élève introuvable. Veuillez compléter votre profil.")
        
        # Rediriger vers la même page (liste des cours)
        return redirect("cours:list")

class DesinscrireEleveView(LoginRequiredMixin, EleveRequiredMixin, View):
    """Vue pour la désinscription d'un élève d'un cours"""
    
    def get(self, request, pk):
        """Redirige vers la liste des cours si accès via GET"""
        messages.info(request, "Veuillez utiliser le formulaire de désinscription depuis la liste des cours.")
        return redirect("cours:list")
    
    def post(self, request, pk):
        cours = get_object_or_404(Cours, pk=pk)
        try:
            eleve = Eleve.objects.get(user=request.user)
            
            # Supprimer l'inscription via la table intermédiaire
            inscription = CoursCoursEleves.objects.filter(cours=cours, eleve=eleve)
            if inscription.exists():
                inscription.delete()
                messages.success(request, f"Désinscription réussie du cours {cours.titre}.")
            else:
                messages.warning(request, f"Vous n'êtes pas inscrit à ce cours.")
                
        except Eleve.DoesNotExist:
            messages.error(request, "Profil élève introuvable.")
        
        # Rediriger vers la même page (liste des cours)
        return redirect("cours:list")


# Évaluation par le professeur
def evaluer_eleve(request, cours_pk, eleve_pk):
    if not request.user.is_authenticated or getattr(request.user, "type_utilisateur", "") != "professeur":
        return HttpResponseForbidden("Accès réservé aux professeurs.")
    
    try:
        prof = Professeur.objects.get(user=request.user)
        cours = get_object_or_404(Cours, pk=cours_pk)
        eleve = get_object_or_404(Eleve, pk=eleve_pk)
        
        # Vérifier que le professeur est propriétaire du cours
        if cours.professeur != prof:
            return HttpResponseForbidden("Vous ne pouvez pas évaluer pour ce cours.")
        
        # Vérifier que l'élève est inscrit au cours
        if not CoursCoursEleves.objects.filter(cours=cours, eleve=eleve).exists():
            messages.error(request, "Cet élève n'est pas inscrit à ce cours.")
            return redirect("cours:detail", pk=cours_pk)
        
        if request.method == "POST":
            note = request.POST.get("note")
            commentaire = request.POST.get("commentaire", "")
            
            # Validation de la note
            if not note:
                messages.error(request, "La note est obligatoire.")
                return redirect("cours:evaluer_eleve", cours_pk=cours_pk, eleve_pk=eleve_pk)
            
            try:
                note = int(note)
                if not (1 <= note <= 5):
                    messages.error(request, "La note doit être comprise entre 1 et 5.")
                    return redirect("cours:evaluer_eleve", cours_pk=cours_pk, eleve_pk=eleve_pk)
            except ValueError:
                messages.error(request, "La note doit être un nombre entier.")
                return redirect("cours:evaluer_eleve", cours_pk=cours_pk, eleve_pk=eleve_pk)
            
            # Créer ou mettre à jour l'évaluation
            evaluation, created = Evaluation.objects.update_or_create(
                cours=cours, 
                eleve=eleve,
                defaults={
                    "note": note, 
                    "commentaire": commentaire
                }
            )
            
            if created:
                messages.success(request, "Évaluation créée avec succès.")
            else:
                messages.success(request, "Évaluation mise à jour avec succès.")
                
            return redirect("cours:detail", pk=cours_pk)
        
        # Méthode GET : afficher formulaire d'évaluation
        evaluation_existante = Evaluation.objects.filter(cours=cours, eleve=eleve).first()
        
        context = {
            'cours': cours,
            'eleve': eleve,
            'evaluation': evaluation_existante
        }
        return render(request, 'cours/evaluer_eleve.html', context)
        
    except Professeur.DoesNotExist:
        messages.error(request, "Profil professeur introuvable.")
        return redirect("cours:list")
    except Exception as e:
        messages.error(request, f"Une erreur est survenue: {str(e)}")
        return redirect("cours:list")


class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    template_name = "cours/quiz_list.html"
    context_object_name = "quiz_list"
    paginate_by = 12

    def get_queryset(self):
        # CORRECTION : Utiliser date_creation au lieu de created_at
        queryset = Quiz.objects.all().order_by("-date_creation")
        
        # Filtrage par cours
        cours_id = self.request.GET.get('cours_id')
        if cours_id:
            queryset = queryset.filter(cours_id=cours_id)
            
        # Filtrage par statut actif pour les élèves
        if getattr(self.request.user, "type_utilisateur", "") == "élève":
            queryset = queryset.filter(est_actif=True)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques pour les professeurs
        if getattr(self.request.user, "type_utilisateur", "") == "professeur":
            try:
                prof = Professeur.objects.get(user=self.request.user)
                context['mes_quiz'] = Quiz.objects.filter(created_by=self.request.user).count()
                context['quiz_actifs'] = Quiz.objects.filter(created_by=self.request.user, est_actif=True).count()
            except Professeur.DoesNotExist:
                pass
                
        return context
    


# =====================================
# VUE : Génération de quiz à partir des soumissions
# =====================================
@method_decorator(csrf_exempt, name="dispatch")
class QuizCreateFromAIView(LoginRequiredMixin, View):
    """Vue pour créer des quiz via l'IA avec payload JSON complet"""
    
    def post(self, request, *args, **kwargs):
        # Vérifier les permissions
        if not (request.user.is_staff or request.user.has_perm("cours.add_quiz")):
            return HttpResponseForbidden("Permission refusée.")
        
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            return HttpResponseBadRequest(f"JSON invalide: {str(e)}")
        
        try:
            quiz = self._create_quiz_from_payload(payload, created_by=request.user)
            return JsonResponse({"status": "ok", "quiz_id": quiz.id, "message": "Quiz créé avec succès"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    
    def _create_quiz_from_payload(self, payload, created_by=None):
        """Crée un quiz complet avec questions et choix"""
        titre = payload.get("titre") or "Quiz sans titre"
        description = payload.get("description", "")
        cours_id = payload.get("cours_id")
        duree = payload.get("duree", 30)
        points_max = payload.get("points_max", 20)
        
        # Vérifier que le cours existe et appartient au professeur
        cours = None
        if cours_id:
            try:
                cours = Cours.objects.get(id=cours_id, professeur__user=created_by)
            except Cours.DoesNotExist:
                raise ValidationError("Cours non trouvé ou non autorisé")
        
        quiz = Quiz.objects.create(
            titre=titre, 
            description=description,
            cours=cours,
            created_by=created_by,
            duree=duree,
            points_max=points_max,
            created_by_ai=True
        )
        
        questions = payload.get("questions", [])
        for idx, q in enumerate(questions, start=1):
            texte = q.get("texte", f"Question {idx}")
            points = q.get("points", 1)
            explication = q.get("explication", "")
            
            question = Question.objects.create(
                quiz=quiz, 
                texte=texte, 
                ordre=idx,
                points=points,
                explication=explication
            )
            
            choices = q.get("choices", [])
            for c_idx, c in enumerate(choices, start=1):
                Choice.objects.create(
                    question=question, 
                    texte=c.get("texte", f"Choix {c_idx}"), 
                    est_correcte=bool(c.get("est_correcte", False)),
                    ordre=c_idx
                )
        
        return quiz

@method_decorator(csrf_exempt, name="dispatch")
class QuizCreateFromSubmissionView(LoginRequiredMixin, View):
    """Vue pour créer des quiz automatiquement à partir des soumissions d'élèves"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Récupérer la session et les soumissions
            session_id = request.POST.get('session_id')
            soumission_id = request.POST.get('soumission_id')
            
            if not session_id and not soumission_id:
                return JsonResponse({
                    "status": "error", 
                    "message": "Session ID ou Soumission ID requis"
                }, status=400)
            
            # Récupérer la session ou la soumission
            if session_id:
                quiz = self._creer_quiz_depuis_session(session_id, request.user)
            else:
                quiz = self._creer_quiz_depuis_soumission(soumission_id, request.user)
            
            return JsonResponse({
                "status": "success", 
                "quiz_id": quiz.id,
                "quiz_titre": quiz.titre,
                "questions_count": quiz.questions.count(),
                "message": "Quiz généré automatiquement avec succès"
            })
            
        except Exception as e:
            return JsonResponse({
                "status": "error", 
                "message": str(e)
            }, status=400)
    
    def _creer_quiz_depuis_session(self, session_id, user):
        """Crée un quiz à partir de toutes les soumissions d'une session"""
        try:
            from repetiteur_ia.models import SessionRevisionProgrammee, SoumissionCours
            
            session = SessionRevisionProgrammee.objects.get(id=session_id, eleve__user=user)
            soumissions = session.soumissions.all()
            
            if not soumissions.exists():
                raise Exception("Aucune soumission trouvée pour cette session")
            
            # Récupérer tout le contenu des soumissions
            contenu_complet = ""
            for soumission in soumissions:
                if soumission.contenu_texte:
                    contenu_complet += soumission.contenu_texte + "\n\n"
                if soumission.resume_automatique:
                    contenu_complet += f"Résumé: {soumission.resume_automatique}\n\n"
            
            # Générer le quiz avec l'IA
            quiz_data = self._generer_quiz_avec_ia(
                contenu=contenu_complet,
                matiere=session.emploi_temps.matiere,
                niveau=session.eleve.get_niveau_display(),
                nombre_questions=5
            )
            
            # Créer le quiz dans la base de données
            quiz = self._creer_quiz_objet(quiz_data, session, user)
            
            return quiz
            
        except SessionRevisionProgrammee.DoesNotExist:
            raise Exception("Session non trouvée")
    
    def _creer_quiz_depuis_soumission(self, soumission_id, user):
        """Crée un quiz à partir d'une soumission spécifique"""
        try:
            from repetiteur_ia.models import SoumissionCours
            
            soumission = SoumissionCours.objects.get(
                id=soumission_id, 
                session__eleve__user=user
            )
            
            # Préparer le contenu
            contenu = soumission.contenu_texte or ""
            if soumission.resume_automatique:
                contenu += f"\n\nRésumé: {soumission.resume_automatique}"
            
            # Générer le quiz avec l'IA
            quiz_data = self._generer_quiz_avec_ia(
                contenu=contenu,
                matiere=soumission.session.emploi_temps.matiere,
                niveau=soumission.session.eleve.get_niveau_display(),
                nombre_questions=3
            )
            
            # Créer le quiz dans la base de données
            quiz = self._creer_quiz_objet(quiz_data, soumission.session, user)
            
            return quiz
            
        except SoumissionCours.DoesNotExist:
            raise Exception("Soumission non trouvée")
    
    def _generer_quiz_avec_ia(self, contenu, matiere, niveau, nombre_questions=5):
        """Utilise l'IA pour générer un quiz à partir du contenu"""
        
        prompt = f"""
        Tu es un expert pédagogique. Génère un quiz basé sur le contenu suivant.
        
        MATIÈRE: {matiere}
        NIVEAU: {niveau}
        NOMBRE DE QUESTIONS: {nombre_questions}
        
        CONTENU À UTILISER:
        {contenu[:4000]}
        
        GÉNÈRE UN QUIZ AVEC:
        - {nombre_questions} questions de difficulté progressive
        - 4 choix de réponse par question
        - Une seule réponse correcte par question
        - Des explications claires pour chaque réponse
        
        FORMAT DE RÉPONSE ATTENDU (JSON):
        {{
            "titre": "Quiz sur [thème principal] - Niveau {niveau}",
            "description": "Quiz généré automatiquement à partir du contenu étudié",
            "questions": [
                {{
                    "texte": "Question claire et précise",
                    "points": 1,
                    "explication": "Explication pédagogique de la réponse correcte",
                    "choices": [
                        {{"texte": "Choix 1", "est_correcte": true/false}},
                        {{"texte": "Choix 2", "est_correcte": true/false}},
                        {{"texte": "Choix 3", "est_correcte": true/false}},
                        {{"texte": "Choix 4", "est_correcte": true/false}}
                    ]
                }}
            ]
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            
            reponse_texte = response.choices[0].message.content.strip()
            
            # Nettoyer la réponse JSON
            if reponse_texte.startswith("```json"):
                reponse_texte = reponse_texte[7:]
            if reponse_texte.endswith("```"):
                reponse_texte = reponse_texte[:-3]
            
            quiz_data = json.loads(reponse_texte)
            return quiz_data
            
        except Exception as e:
            print(f"Erreur génération IA: {e}")
            return self._quiz_par_defaut(matiere, niveau)
    
    def _quiz_par_defaut(self, matiere, niveau):
        """Retourne un quiz par défaut si l'IA échoue"""
        return {
            "titre": f"Quiz {matiere} - Niveau {niveau}",
            "description": "Quiz généré automatiquement",
            "questions": [
                {
                    "texte": f"Qu'as-tu retenu du cours de {matiere} ?",
                    "points": 1,
                    "explication": "Cette question teste ta compréhension globale du sujet.",
                    "choices": [
                        {"texte": "Les concepts principaux", "est_correcte": True},
                        {"texte": "Je ne me souviens pas", "est_correcte": False},
                        {"texte": "Des détails sans importance", "est_correcte": False},
                        {"texte": "Rien de spécifique", "est_correcte": False}
                    ]
                }
            ]
        }
    
    def _creer_quiz_objet(self, quiz_data, session, user):
        """Crée l'objet Quiz dans la base de données"""
        
        with transaction.atomic():
            # Créer le quiz
            quiz = Quiz.objects.create(
                titre=quiz_data["titre"],
                description=quiz_data.get("description", ""),
                cours=None,
                created_by=user,
                created_by_ai=True,
                duree=15,
                points_max=len(quiz_data["questions"]),
                est_actif=True
            )
            
            # Créer les questions et choix
            for idx, question_data in enumerate(quiz_data["questions"], 1):
                question = Question.objects.create(
                    quiz=quiz,
                    texte=question_data["texte"],
                    ordre=idx,
                    points=question_data.get("points", 1),
                    explication=question_data.get("explication", "")
                )
                
                # Créer les choix de réponse
                for c_idx, choice_data in enumerate(question_data["choices"], 1):
                    Choice.objects.create(
                        question=question,
                        texte=choice_data["texte"],
                        est_correcte=choice_data["est_correcte"],
                        ordre=c_idx
                    )
            
            return quiz



# =====================================
# VUE : Liste des emplois du temps
# =====================================
class EmploiDuTempsListView(LoginRequiredMixin, ListView):
    model = EmploiDuTemps
    template_name = "cours/emploi_du_temps_list.html"
    context_object_name = "emplois_du_temps"
    
    def get_queryset(self):
        user = self.request.user
        queryset = EmploiDuTemps.objects.filter(actif=True)
        
        if getattr(user, "type_utilisateur", "") == "élève":
            try:
                eleve = Eleve.objects.get(user=user)
                queryset = queryset.filter(eleve=eleve)
            except Eleve.DoesNotExist:
                return EmploiDuTemps.objects.none()
        
        elif getattr(user, "type_utilisateur", "") == "professeur":
            try:
                prof = Professeur.objects.get(user=user)
                queryset = queryset.filter(cours__professeur=prof)
            except Professeur.DoesNotExist:
                return EmploiDuTemps.objects.none()
        
        return queryset.order_by('jour_semaine', 'heure_debut')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        emplois = context['emplois_du_temps']
        
        # Statistiques
        context['cours_semaine_count'] = emplois.count()
        context['heures_semaine'] = sum(
            (emploi.heure_fin.hour - emploi.heure_debut.hour) + 
            (emploi.heure_fin.minute - emploi.heure_debut.minute) / 60 
            for emploi in emplois
        )
        context['matieres_count'] = emplois.values('matiere').distinct().count()
        
        # Prochain cours - CORRECTION: Use Django's timezone, not datetime.timezone
        from django.utils import timezone as django_timezone
        
        # Get the French day names mapping
        french_to_english_days = {
            'lundi': 'monday',
            'mardi': 'tuesday',
            'mercredi': 'wednesday',
            'jeudi': 'thursday',
            'vendredi': 'friday',
            'samedi': 'saturday',
            'dimanche': 'sunday'
        }
        
        # Get current day in French
        today_french = django_timezone.now().strftime('%A').lower()
        
        # If Django returns English day names, translate to French
        # This depends on your Django locale settings
        english_to_french = {
            'monday': 'lundi',
            'tuesday': 'mardi',
            'wednesday': 'mercredi',
            'thursday': 'jeudi',
            'friday': 'vendredi',
            'saturday': 'samedi',
            'sunday': 'dimanche'
        }
        
        today_french = english_to_french.get(today_french, today_french)
        current_time = django_timezone.now().time()
        
        context['prochain_cours'] = emplois.filter(
            jour_semaine=today_french,
            heure_debut__gte=current_time
        ).order_by('heure_debut').first()
        
        # Matières uniques pour le filtre
        context['matieres_uniques'] = sorted(set(emploi.matiere for emploi in emplois))
        
        # Structure pour la vue hebdomadaire
        today = django_timezone.now().date()
        current_weekday = today.weekday()  # Monday = 0, Sunday = 6
        
        jours_semaine = [
            {'nom': 'Lundi', 'valeur': 'lundi', 'date': today - timedelta(days=current_weekday)},
            {'nom': 'Mardi', 'valeur': 'mardi', 'date': today - timedelta(days=current_weekday-1)},
            {'nom': 'Mercredi', 'valeur': 'mercredi', 'date': today - timedelta(days=current_weekday-2)},
            {'nom': 'Jeudi', 'valeur': 'jeudi', 'date': today - timedelta(days=current_weekday-3)},
            {'nom': 'Vendredi', 'valeur': 'vendredi', 'date': today - timedelta(days=current_weekday-4)},
            {'nom': 'Samedi', 'valeur': 'samedi', 'date': today - timedelta(days=current_weekday-5)},
            {'nom': 'Dimanche', 'valeur': 'dimanche', 'date': today - timedelta(days=current_weekday-6)},
        ]
        context['jours_semaine'] = jours_semaine
        context['semaine_debut'] = jours_semaine[0]['date']
        context['semaine_fin'] = jours_semaine[-1]['date']
        
        # Heures de la journée (8h-20h)
        context['heures_journee'] = [f"{h:02d}:00" for h in range(8, 21)]
        
        # Emplois par jour et heure pour la grille
        context['emplois_par_jour_heure'] = emplois
        
        # Sessions de révision (si élève)
        if getattr(self.request.user, "type_utilisateur", "") == "élève":
            try:
                from repetiteur_ia.models import SessionRevisionProgrammee
                eleve = Eleve.objects.get(user=self.request.user)
                context['sessions_revision'] = SessionRevisionProgrammee.objects.filter(
                    eleve=eleve,
                    date_programmation__gte=django_timezone.now()
                ).order_by('date_programmation')[:6]
            except (Eleve.DoesNotExist, ImportError):
                context['sessions_revision'] = []
        
        return context

# =====================================
# VUE : Évaluations de l'élève
# =====================================
class MesEvaluationsView(LoginRequiredMixin, ListView):
    model = Evaluation
    template_name = "cours/mes_evaluations.html"
    context_object_name = "evaluations"
    
    def get_queryset(self):
        if getattr(self.request.user, "type_utilisateur", "") != "élève":
            return Evaluation.objects.none()
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            return Evaluation.objects.filter(eleve=eleve).select_related('cours').order_by('-date_creation')
        except Eleve.DoesNotExist:
            return Evaluation.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluations = context['evaluations']
        
        # Récupérer les matières depuis les évaluations de l'élève
        matieres_evaluees = Evaluation.objects.filter(
            eleve__user=self.request.user
        ).exclude(
            cours__matiere__isnull=True
        ).exclude(
            cours__matiere__exact=''
        ).values_list(
            'cours__matiere', flat=True
        ).distinct().order_by('cours__matiere')
        
        # Optionnel : Récupérer TOUTES les matières disponibles dans la plateforme
        toutes_les_matieres = Cours.objects.exclude(
            matiere__isnull=True
        ).exclude(
            matiere__exact=''
        ).values_list('matiere', flat=True).distinct().order_by('matiere')
        
        context['matieres_disponibles'] = list(matieres_evaluees)
        context['toutes_les_matieres'] = list(toutes_les_matieres)
        
        # Calcul des statistiques
        if evaluations:
            notes = [eval.note for eval in evaluations]
            context['moyenne_generale'] = round(sum(notes) / len(notes), 1)
            
            # Meilleure et pire note
            if evaluations:
                context['meilleure_note'] = max(evaluations, key=lambda x: x.note)
                context['pire_note'] = min(evaluations, key=lambda x: x.note)
            
            # Distribution des notes
            notes_distribution = {str(i): 0 for i in range(1, 6)}
            for note in notes:
                notes_distribution[str(note)] += 1
            context['notes_distribution'] = notes_distribution
            
            # Calcul de la progression
            if len(evaluations) > 1:
                recent_avg = sum([eval.note for eval in evaluations[:3]]) / min(3, len(evaluations))
                context['progression'] = int((recent_avg / 5) * 100)
            else:
                context['progression'] = int((context['moyenne_generale'] / 5) * 100)
        
        return context


class QuizCreateView(LoginRequiredMixin, ProfesseurRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = "cours/quiz_form.html"
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrer les cours pour n'afficher que ceux du professeur connecté
        prof = getattr(self.request.user, "professeur_profile", None)
        if prof:
            form.fields['cours'].queryset = Cours.objects.filter(professeur=prof)
        return form
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        with transaction.atomic():
            # Sauvegarder le quiz d'abord
            self.object = form.save()
            
            # Traiter les questions et choix
            self._process_questions(self.object, self.request.POST)
            
            messages.success(self.request, "Quiz créé avec succès avec ses questions.")
            return redirect(self.get_success_url())
    
    def _process_questions(self, quiz, post_data):
        """Traite les questions et choix du formulaire"""
        question_counter = 1
        
        # Traiter les nouvelles questions
        while True:
            question_text = post_data.get(f'new_question_texte_{question_counter}')
            if not question_text:
                break
                
            question_points = int(post_data.get(f'new_question_points_{question_counter}', 1))
            question_explication = post_data.get(f'new_question_explication_{question_counter}', '')
            
            # Créer la question
            question = Question.objects.create(
                quiz=quiz,
                texte=question_text,
                points=question_points,
                explication=question_explication,
                ordre=question_counter
            )
            
            # Traiter les choix de cette question
            choice_counter = 1
            while True:
                choice_text = post_data.get(f'new_choice_texte_{question_counter}_{choice_counter}')
                if not choice_text:
                    break
                    
                choice_ordre = int(post_data.get(f'new_choice_ordre_{question_counter}_{choice_counter}', choice_counter))
                choice_correcte = f'new_choice_correcte_{question_counter}_{choice_counter}' in post_data
                
                Choice.objects.create(
                    question=question,
                    texte=choice_text,
                    ordre=choice_ordre,
                    est_correcte=choice_correcte
                )
                
                choice_counter += 1
            
            question_counter += 1
    
    def get_success_url(self):
        return reverse_lazy('cours:quiz_detail', kwargs={'pk': self.object.pk})



class QuizUpdateView(LoginRequiredMixin, ProfesseurRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    template_name = "cours/quiz_form.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.created_by != request.user:
            return HttpResponseForbidden("Vous n'avez pas le droit de modifier ce quiz.")
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('cours:quiz_detail', kwargs={'pk': self.object.pk})

class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = "cours/quiz_detail.html"
    context_object_name = "quiz"


class AddQuestionView(LoginRequiredMixin, ProfesseurRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = "cours/question_form.html"
    
    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, pk=kwargs['quiz_pk'])
        if self.quiz.created_by != request.user:
            return HttpResponseForbidden("Vous n'avez pas le droit d'ajouter des questions à ce quiz.")
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.quiz = self.quiz
        response = super().form_valid(form)
        
        # Créer les choix de réponse
        choices_data = self.extract_choices_from_request()
        self.create_choices_for_question(choices_data)
        
        messages.success(self.request, "Question et choix ajoutés avec succès.")
        return response
    
    def extract_choices_from_request(self):
        """Extrait les données des choix du formulaire"""
        choices_data = []
        i = 1
        while True:
            texte_key = f'texte_{i}'
            est_correcte_key = f'est_correcte_{i}'
            ordre_key = f'ordre_{i}'
            
            if texte_key not in self.request.POST:
                break
                
            texte = self.request.POST.get(texte_key, '').strip()
            if texte:  # Ignorer les choix vides
                choices_data.append({
                    'texte': texte,
                    'est_correcte': self.request.POST.get(est_correcte_key) == 'on',
                    'ordre': int(self.request.POST.get(ordre_key, i))
                })
            i += 1
        
        return choices_data
    
    def create_choices_for_question(self, choices_data):
        """Crée les objets Choice pour la question"""
        for choice_data in choices_data:
            Choice.objects.create(
                question=self.object,
                texte=choice_data['texte'],
                est_correcte=choice_data['est_correcte'],
                ordre=choice_data['ordre']
            )
    
    def get_success_url(self):
        return reverse_lazy('cours:quiz_detail', kwargs={'pk': self.quiz.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.quiz
        return context
    

# Vue pour la liste des emplois du temps
class EmploiDuTempsListView(LoginRequiredMixin, ListView):
    model = EmploiDuTemps
    template_name = "cours/emploi_du_temps_list.html"
    context_object_name = "emplois_du_temps"
    
    def get_queryset(self):
        user = self.request.user
        queryset = EmploiDuTemps.objects.filter(actif=True)
        
        if getattr(user, "type_utilisateur", "") == "élève":
            try:
                eleve = Eleve.objects.get(user=user)
                queryset = queryset.filter(eleve=eleve)
            except Eleve.DoesNotExist:
                return EmploiDuTemps.objects.none()
        
        elif getattr(user, "type_utilisateur", "") == "professeur":
            try:
                prof = Professeur.objects.get(user=user)
                queryset = queryset.filter(cours__professeur=prof)
            except Professeur.DoesNotExist:
                return EmploiDuTemps.objects.none()
        
        return queryset.order_by('jour_semaine', 'heure_debut')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        emplois = context['emplois_du_temps']
        
        # Statistiques
        context['cours_semaine_count'] = emplois.count()
        context['heures_semaine'] = sum(
            (emploi.heure_fin.hour - emploi.heure_debut.hour) + 
            (emploi.heure_fin.minute - emploi.heure_debut.minute) / 60 
            for emploi in emplois
        )
        context['matieres_count'] = emplois.values('matiere').distinct().count()
        
        # Prochain cours
        aujourdhui = timezone.now().strftime('%A').lower()
        context['prochain_cours'] = emplois.filter(
            jour_semaine=aujourdhui,
            heure_debut__gte=timezone.now().time()
        ).order_by('heure_debut').first()
        
        # Matières uniques pour le filtre
        context['matieres_uniques'] = sorted(set(emploi.matiere for emploi in emplois))
        
        # Structure pour la vue hebdomadaire
        jours_semaine = [
            {'nom': 'Lundi', 'valeur': 'lundi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday())},
            {'nom': 'Mardi', 'valeur': 'mardi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-1)},
            {'nom': 'Mercredi', 'valeur': 'mercredi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-2)},
            {'nom': 'Jeudi', 'valeur': 'jeudi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-3)},
            {'nom': 'Vendredi', 'valeur': 'vendredi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-4)},
            {'nom': 'Samedi', 'valeur': 'samedi', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-5)},
            {'nom': 'Dimanche', 'valeur': 'dimanche', 'date': timezone.now().date() - timedelta(days=timezone.now().weekday()-6)},
        ]
        context['jours_semaine'] = jours_semaine
        context['semaine_debut'] = jours_semaine[0]['date']
        context['semaine_fin'] = jours_semaine[-1]['date']
        
        # Heures de la journée (8h-20h)
        context['heures_journee'] = [f"{h:02d}:00" for h in range(8, 21)]
        
        # Emplois par jour et heure pour la grille
        context['emplois_par_jour_heure'] = emplois
        
        # Sessions de révision (si élève)
        if getattr(self.request.user, "type_utilisateur", "") == "élève":
            try:
                from repetiteur_ia.models import SessionRevisionProgrammee
                eleve = Eleve.objects.get(user=self.request.user)
                context['sessions_revision'] = SessionRevisionProgrammee.objects.filter(
                    eleve=eleve,
                    date_programmation__gte=timezone.now()
                ).order_by('date_programmation')[:6]
            except (Eleve.DoesNotExist, ImportError):
                context['sessions_revision'] = []
        
        return context


# Vue pour les évaluations des élèves
class MesEvaluationsView(LoginRequiredMixin, ListView):
    model = Evaluation
    template_name = "cours/mes_evaluations.html"
    context_object_name = "evaluations"
    
    def get_queryset(self):
        if getattr(self.request.user, "type_utilisateur", "") != "élève":
            return Evaluation.objects.none()
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            return Evaluation.objects.filter(eleve=eleve).select_related('cours')
        except Eleve.DoesNotExist:
            return Evaluation.objects.none()



class QuizTakeView(LoginRequiredMixin, DetailView):
    """Vue pour passer le quiz"""
    model = QuizAttempt
    template_name = "cours/quiz_take.html"
    context_object_name = "attempt"
    
    def get_object(self, queryset=None):
        """Récupère la tentative de quiz avec l'ID de l'URL"""
        attempt_id = self.kwargs.get('attempt_id')
        from utilisateurs.models import Eleve
        
        # Vérifie que l'utilisateur est bien un élève
        try:
            eleve = Eleve.objects.get(user=self.request.user)
        except Eleve.DoesNotExist:
            raise Http404("Profil élève introuvable.")

        # On récupère la tentative sans restreindre au statut
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, eleve=eleve)
        
        # Si le quiz est déjà terminé, on affiche un message
        if attempt.statut != 'en_cours':
            messages.warning(self.request, "Cette tentative de quiz est déjà terminée.")
        
        return attempt

    def get_context_data(self, **kwargs):
        """Ajoute les données du quiz au contexte"""
        context = super().get_context_data(**kwargs)
        attempt = self.object
        
        # Récupérer la session active liée à la tentative
        session = QuizSession.objects.filter(
            quiz=attempt.quiz, 
            eleve=attempt.eleve
        ).first()
        
        # Récupérer les questions non répondues
        questions_non_repondues = []
        if session:
            questions_non_repondues = session.questions_repondues.filter(
                questionsession__repondue=False
            ).order_by('questionsession__ordre')
        
        # Si aucune question non répondue, récupérer toutes les questions du quiz
        if not questions_non_repondues.exists():
            questions_non_repondues = attempt.quiz.questions.order_by('ordre')
        
        current_question = questions_non_repondues.first() if questions_non_repondues.exists() else None
        
        context.update({
            'quiz': attempt.quiz,
            'session': session,
            'current_question': current_question,
            'questions_count': attempt.quiz.questions.count(),
            'progression': attempt.get_progression(),
            'temps_restant': session.temps_restant if session else attempt.quiz.duree * 60,
        })
        return context


class QuizStartView(LoginRequiredMixin, View):
    """Démarre un quiz pour un élève"""
    
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, est_actif=True)
        
        try:
            eleve = Eleve.objects.get(user=request.user)
            
            # Vérifier si l'élève peut tenter le quiz
            if not quiz.can_be_attempted_by(eleve):
                messages.warning(request, "Vous avez déjà une tentative en cours pour ce quiz.")
                return redirect('cours:quiz_detail', pk=pk)
            
            # Créer une nouvelle tentative
            with transaction.atomic():
                attempt = QuizAttempt.objects.create(
                    quiz=quiz,
                    eleve=eleve,
                    points_max=sum(q.points for q in quiz.questions.all())
                )
                
                # Créer une session de quiz
                date_fin_prevue = timezone.now() + timedelta(minutes=quiz.duree)
                session = QuizSession.objects.create(
                    quiz=quiz,
                    eleve=eleve,
                    date_fin_prevue=date_fin_prevue,
                    temps_restant=quiz.duree * 60  # Convertir en secondes
                )
                
                # Préparer les questions pour la session
                questions = quiz.questions.order_by('ordre')
                for ordre, question in enumerate(questions, 1):
                    session.questions_repondues.add(question, through_defaults={'ordre': ordre})
            
            messages.success(request, f"Quiz '{quiz.titre}' démarré ! Vous avez {quiz.duree} minutes.")
            return redirect('cours:quiz_take', attempt_id=attempt.id)
            
        except Eleve.DoesNotExist:
            messages.error(request, "Profil élève introuvable.")
            return redirect('cours:quiz_list')
        


class QuizSubmitAnswerView(LoginRequiredMixin, View):
    """Soumet une réponse à une question"""
    
    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, eleve__user=request.user)
        
        if attempt.statut != 'en_cours':
            return JsonResponse({'error': 'Cette tentative est terminée.'}, status=400)
        
        try:
            data = json.loads(request.body)
            question_id = data.get('question_id')
            choix_ids = data.get('choix_ids', [])
            temps_reponse = data.get('temps_reponse', 0)
            
            question = get_object_or_404(attempt.quiz.questions, id=question_id)
            choix_selectionnes = question.choices.filter(id__in=choix_ids)
            
            with transaction.atomic():
                # Créer ou mettre à jour la réponse
                question_attempt, created = QuestionAttempt.objects.get_or_create(
                    tentative=attempt,
                    question=question,
                    defaults={'temps_reponse': temps_reponse}
                )
                
                if not created:
                    question_attempt.temps_reponse = temps_reponse
                
                question_attempt.choix_selectionnes.set(choix_selectionnes)
                points_obtenus = question_attempt.evaluer_reponse()
                
                # Mettre à jour la session
                session = QuizSession.objects.filter(
                    quiz=attempt.quiz, 
                    eleve=attempt.eleve
                ).first()
                
                if session:
                    question_session = session.questionsession_set.get(question=question)
                    question_session.repondue = True
                    question_session.date_reponse = timezone.now()
                    question_session.save()
            
            return JsonResponse({
                'success': True,
                'points_obtenus': points_obtenus,
                'est_correcte': question_attempt.est_correcte,
                'progression': attempt.get_progression()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class QuizFinishView(LoginRequiredMixin, View):
    """Termine un quiz"""
    
    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, eleve__user=request.user)
        
        if attempt.statut == 'en_cours':
            attempt.terminer()
            
            # Calculer le score final
            score = attempt.score
            appreciation = attempt.get_appreciation()
            
            messages.success(
                request, 
                f"Quiz terminé ! Score: {score}% - {appreciation}"
            )
            
            return JsonResponse({
                'success': True,
                'score': score,
                'points_obtenus': attempt.points_obtenus,
                'points_max': attempt.points_max,
                'appreciation': appreciation,
                'duree': attempt.get_duree_formatee()
            })
        
        return JsonResponse({'error': 'Quiz déjà terminé.'}, status=400)

class QuizResultsView(LoginRequiredMixin, DetailView):
    """Affiche les résultats d'un quiz"""
    model = QuizAttempt
    template_name = "cours/quiz_results.html"
    context_object_name = "attempt"
    pk_url_kwarg = "attempt_id"
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(eleve__user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.object
        
        # Récupérer les réponses détaillées
        reponses = attempt.reponses.select_related('question').prefetch_related(
            'choix_selectionnes', 'question__choices'
        )
        
        context.update({
            'quiz': attempt.quiz,
            'reponses': reponses,
            'score': attempt.score,
            'points_obtenus': attempt.points_obtenus,
            'points_max': attempt.points_max,
            'duree': attempt.get_duree_formatee(),
            'appreciation': attempt.get_appreciation()
        })
        return context