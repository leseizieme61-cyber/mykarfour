from django.apps import AppConfig

class RepetiteurIaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repetiteur_ia'
    
    def ready(self):
        import repetiteur_ia.signals
        # Nous retirons l'initialisation du vectorstore ici