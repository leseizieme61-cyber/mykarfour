# repetiteur_ia/views_api_rappels.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from repetiteur_ia.models import RappelRevision
from django.utils import timezone

@login_required
def detail_rappel_api(request, rappel_id):
    """API pour récupérer les détails d'un rappel"""
    try:
        rappel = RappelRevision.objects.get(id=rappel_id)
        
        # Vérifier les permissions
        if hasattr(request.user, 'eleve'):
            # Élève ne voit que ses propres rappels
            if rappel.eleve != request.user.eleve:
                return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
        elif hasattr(request.user, 'parent'):
            # Parent voit les rappels de ses enfants
            parent = request.user.parent
            if rappel.eleve not in parent.eleves.all():
                return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
        
        response_data = {
            'status': 'success',
            'id': rappel.id,
            'titre': rappel.titre,
            'message': rappel.message,
            'date_rappel': rappel.date_rappel.strftime('%d/%m/%Y %H:%M'),
            'envoye': rappel.envoye,
            'date_creation': rappel.date_creation.strftime('%d/%m/%Y %H:%M'),
        }
        
        # Ajouter les informations optionnelles
        if rappel.eleve:
            response_data['eleve'] = f"{rappel.eleve.user.username} ({rappel.eleve.user.first_name})"
        
        if rappel.session_programmee:
            response_data['session'] = rappel.session_programmee.titre
            response_data['session_matiere'] = rappel.session_programmee.emploi_temps.matiere if rappel.session_programmee.emploi_temps else 'N/A'
        
        return JsonResponse(response_data)
        
    except RappelRevision.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Rappel introuvable'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
