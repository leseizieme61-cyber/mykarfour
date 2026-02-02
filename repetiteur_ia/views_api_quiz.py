# repetiteur_ia/views_api_quiz.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from cours.models import QuizAttempt, QuestionAttempt
from django.utils import timezone

@login_required
def detail_quiz_api(request, quiz_attempt_id):
    """API pour récupérer les détails d'une tentative de quiz"""
    try:
        attempt = QuizAttempt.objects.get(id=quiz_attempt_id)
        
        # Vérifier les permissions
        if hasattr(request.user, 'eleve'):
            # Élève ne voit que ses propres quiz
            if attempt.eleve != request.user.eleve:
                return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
        elif hasattr(request.user, 'parent'):
            # Parent voit les quiz de ses enfants
            parent = request.user.parent
            if attempt.eleve not in parent.eleves.all():
                return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
        
        # Récupérer les réponses du quiz
        reponses = []
        question_attempts = QuestionAttempt.objects.filter(tentative=attempt).select_related('question')
        
        for answer in question_attempts:
            # Récupérer les choix sélectionnés
            choix_textes = [choix.texte for choix in answer.choix_selectionnes.all()]
            
            # Vérifier si la réponse est correcte
            choix_corrects = [choix.texte for choix in answer.question.get_correct_choices()]
            est_correcte = set(choix_textes) == set(choix_corrects)
            
            reponses.append({
                'numero': answer.question.ordre,
                'question_texte': answer.question.texte[:100] + '...' if len(answer.question.texte) > 100 else answer.question.texte,
                'reponse_choisie': ', '.join(choix_textes) if choix_textes else 'Aucune réponse',
                'correcte': est_correcte,
                'points_obtenus': getattr(answer, 'points_obtenus', 0),
                'points_max': answer.question.points,
            })
        
        response_data = {
            'status': 'success',
            'quiz_titre': attempt.quiz.titre,
            'quiz_matiere': attempt.quiz.cours.matiere if attempt.quiz.cours else 'Général',
            'quiz_description': attempt.quiz.description,
            'date_debut': attempt.date_debut.strftime('%d/%m/%Y %H:%M'),
            'date_fin': attempt.date_fin.strftime('%d/%m/%Y %H:%M') if attempt.date_fin else None,
            'temps_passe': str(attempt.duree_secondes) + ' secondes' if attempt.duree_secondes else None,
            'score': attempt.score,
            'statut': attempt.statut,
            'statut_label': dict(QuizAttempt.STATUT_CHOICES).get(attempt.statut, attempt.statut),
            'questions_repondues': question_attempts.count(),
            'total_questions': attempt.quiz.questions.count(),
            'points_obtenus': attempt.points_obtenus,
            'points_max': attempt.points_max,
            'reponses': reponses,
        }
        
        return JsonResponse(response_data)
        
    except QuizAttempt.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Tentative de quiz introuvable'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
