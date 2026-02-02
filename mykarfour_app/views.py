from pyexpat.errors import messages
from django.views.generic import ListView, DetailView, CreateView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

from cours.forms import CoursForm
from cours.models import Cours, Quiz
from utilisateurs.models import Eleve
from repetiteur_ia.utils import generer_contenu_ia, generer_quiz_ia

def custom_404(request, exception):
    return render(request, '404.html', status=404)

class ListeCoursView(LoginRequiredMixin, ListView):
    model = Cours
    template_name = 'cours/liste_cours.html'
    context_object_name = 'cours_list'
    
    def get_queryset(self):
        if self.request.user.type_utilisateur != 'élève':
            return Cours.objects.none()
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            return Cours.objects.filter(eleve=eleve).order_by('-date_creation')
        except Eleve.DoesNotExist:
            return Cours.objects.none()

class DetailCoursView(LoginRequiredMixin, DetailView):
    model = Cours
    template_name = 'cours/detail_cours.html'
    context_object_name = 'cours'
    
    def get_queryset(self):
        if self.request.user.type_utilisateur != 'élève':
            return Cours.objects.none()
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            return Cours.objects.filter(eleve=eleve)
        except Eleve.DoesNotExist:
            return Cours.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer le quiz associé s'il existe
        try:
            context['quiz'] = Quiz.objects.get(cours=self.object)
        except Quiz.DoesNotExist:
            context['quiz'] = None
        
        return context

class CreerCoursView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Cours
    template_name = 'cours/creer_cours.html'
    fields = ['titre', 'matiere']
    success_message = "Votre cours a été créé avec succès!"
    
    def form_valid(self, form):
        if self.request.user.type_utilisateur != 'élève':
            return redirect('accueil')
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            
            if not eleve.abonnement_actif:
                messages.error(self.request, "Vous devez avoir un abonnement actif pour créer un cours.")
                return redirect('abonnements')
            
            # Générer le contenu avec l'IA en tenant compte du niveau de l'élève
            cours = form.save(commit=False)
            cours.eleve = eleve
            cours.contenu = generer_contenu_ia(cours.titre, cours.matiere, eleve)
            cours.save()
            
            # Générer un quiz associé
            questions = generer_quiz_ia(cours)
            if questions:
                Quiz.objects.create(
                    titre=f"Quiz - {cours.titre}",
                    cours=cours,
                    questions=questions
                )
            
            return super().form_valid(form)
        
        except Eleve.DoesNotExist:
            messages.error(self.request, "Profil élève non trouvé.")
            return redirect('accueil')
    
    def get_success_url(self):
        return reverse_lazy('detail_cours', kwargs={'pk': self.object.pk})



class CreerCoursView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Cours
    form_class = CoursForm
    template_name = 'cours/creer_cours.html'
    success_message = "Votre cours a été créé avec succès!"

    def form_valid(self, form):
        form.instance.eleve = self.request.user.eleve
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('detail_cours', kwargs={'pk': self.object.pk})

# Vue pour le quiz
class DetailQuizView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'cours/detail_quiz.html'
    context_object_name = 'quiz'

    def get_queryset(self):
        return Quiz.objects.filter(cours__eleve__user=self.request.user)


class SoumettreQuizView(LoginRequiredMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, cours__eleve__user=request.user)
        reponses = request.POST.get('reponses', {})
        # Logique de correction du quiz
        # Pour l'instant, nous ne corrigeons pas, mais on peut enregistrer les réponses
        # et les afficher plus tard pour que l'élève se corrige lui-même

        # Exemple: enregistrer les réponses de l'élève dans un modèle RéponseQuiz
        # Ici, nous retournons simplement un succès
        return JsonResponse({'status': 'success', 'message': 'Quiz soumis avec succès!'})


class RechercheCoursView(LoginRequiredMixin, ListView):
    model = Cours
    template_name = 'cours/recherche_cours.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        matiere = self.request.GET.get('matiere')
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')

        if query:
            queryset = queryset.filter(titre__icontains=query)
        if matiere:
            queryset = queryset.filter(matiere=matiere)
        if date_debut and date_fin:
            queryset = queryset.filter(date_creation__range=[date_debut, date_fin])

        return queryset