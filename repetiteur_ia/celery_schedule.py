# repetiteur_ia/celery_schedule.py
from celery.schedules import crontab
from .tasks_rappels import envoyer_rappels_automatiques, verifier_inactivite

# Configuration des tâches périodiques pour Celery Beat
beat_schedule = {
    # Envoyer les rappels tous les jours à 8h du matin
    'envoyer-rappels-quotidiens': {
        'task': 'repetiteur_ia.envoyer_rappels_automatiques',
        'schedule': crontab(hour=8, minute=0),  # Tous les jours à 8h00
        'options': {
            'queue': 'rappels',
        }
    },
    
    # Vérifier l'inactivité tous les jours à 10h
    'verifier-inactivite': {
        'task': 'repetiteur_ia.verifier_inactivite',
        'schedule': crontab(hour=10, minute=0),  # Tous les jours à 10h00
        'options': {
            'queue': 'rappels',
        }
    },
    
    # Rappel supplémentaire le soir à 18h pour les sessions du lendemain
    'rappel-soir-sessions-demain': {
        'task': 'repetiteur_ia.envoyer_rappels_automatiques',
        'schedule': crontab(hour=18, minute=30),  # Tous les jours à 18h30
        'options': {
            'queue': 'rappels',
        }
    },
    
    # Programmation automatique des sessions le dimanche à 20h
    'programmer-semaine': {
        'task': 'repetiteur_ia.programmer_sessions_semaine',
        'schedule': crontab(hour=20, minute=0, day_of_week=6),  # Dimanche 20h
        'options': {
            'queue': 'planning',
        }
    },
}
