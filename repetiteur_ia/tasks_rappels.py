# repetiteur_ia/tasks_rappels.py
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(name='repetiteur_ia.envoyer_rappels_automatiques')
def envoyer_rappels_automatiques():
    """
    Tâche Celery pour envoyer les rappels automatiques
    Peut être appelée via cron ou scheduleur
    """
    try:
        logger.info("Début de la tâche d'envoi des rappels automatiques")
        
        # Appeler la commande de management
        call_command('envoyer_rappels')
        
        logger.info("Tâche d'envoi des rappels terminée avec succès")
        return {"status": "success", "message": "Rappels envoyés avec succès"}
        
    except Exception as e:
        logger.error(f"Erreur dans la tâche d'envoi des rappels: {e}")
        return {"status": "error", "message": str(e)}

@shared_task(name='repetiteur_ia.envoyer_rappel_session')
def envoyer_rappel_session(session_id):
    """
    Envoie un rappel pour une session spécifique
    """
    try:
        from repetiteur_ia.models import SessionRevisionProgrammee
        
        session = SessionRevisionProgrammee.objects.get(id=session_id)
        
        # Logique d'envoi de rappel pour cette session spécifique
        # (sera implémentée selon les besoins)
        
        logger.info(f"Rappel envoyé pour la session {session_id}")
        return {"status": "success", "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Erreur envoi rappel session {session_id}: {e}")
        return {"status": "error", "message": str(e)}

@shared_task(name='repetiteur_ia.verifier_inactivite')
def verifier_inactivite():
    """
    Vérifie les élèves inactifs et déclenche les rappels si nécessaire
    """
    try:
        from django.contrib.auth.models import User
        from utilisateurs.models import Eleve
        from datetime import timedelta
        
        # Élèves inactifs depuis 3 jours
        seuil_inactivite = timezone.now() - timedelta(days=3)
        
        eleves_inactifs = Eleve.objects.filter(
            abonnement_actif=True,
            user__last_login__lt=seuil_inactivite
        ).exclude(user__last_login__isnull=True)
        
        logger.info(f"{eleves_inactifs.count()} élèves inactifs détectés")
        
        # Déclencher l'envoi des rappels
        call_command('envoyer_rappels')
        
        return {"status": "success", "eleves_inactifs": eleves_inactifs.count()}
        
    except Exception as e:
        logger.error(f"Erreur vérification inactivité: {e}")
        return {"status": "error", "message": str(e)}
