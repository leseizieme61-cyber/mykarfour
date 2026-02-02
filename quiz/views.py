from django.shortcuts import get_object_or_404
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from cours.models import Quiz
from utilisateurs.models import Eleve

class DetailQuizView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'quiz/detail_quiz.html'
    context_object_name = 'quiz'
    
    def get_queryset(self):
        if self.request.user.type_utilisateur != 'élève':
            return Quiz.objects.none()
        
        try:
            eleve = Eleve.objects.get(user=self.request.user)
            return Quiz.objects.filter(cours__eleve=eleve)
        except Eleve.DoesNotExist:
            return Quiz.objects.none()

class SoumettreQuizView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if request.user.type_utilisateur != 'élève':
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
        
        try:
            eleve = Eleve.objects.get(user=request.user)
            quiz = get_object_or_404(Quiz, pk=pk, cours__eleve=eleve)
            
            # Récupérer les réponses de l'élève
            reponses_eleve = request.POST.get('reponses', {})
            
            # Ici, vous pourriez enregistrer les réponses de l'élève
            # sans les corriger (comme spécifié dans les exigences)
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Quiz soumis avec succès! Vous pouvez maintenant vérifier vos réponses.'
            })
        
        except Eleve.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Profil élève non trouvé'})