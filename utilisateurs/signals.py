# utilisateurs/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Eleve

@receiver(post_save, sender=Eleve)
def verifier_expiration_abonnement(sender, instance, **kwargs):
    if instance.date_fin_abonnement and instance.date_fin_abonnement < timezone.now().date():
        if instance.abonnement_actif:
            instance.abonnement_actif = False
            instance.save()
