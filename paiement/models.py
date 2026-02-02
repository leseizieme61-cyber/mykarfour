from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from utilisateurs.models import Eleve


class Paiement(models.Model):
    STATUT_COMPLET = 'complet'
    STATUT_EN_ATTENTE = 'en_attente'
    STATUT_ECHOUE = 'echoue'

    STATUT_CHOICES = [
        (STATUT_COMPLET, 'Complété'),
        (STATUT_EN_ATTENTE, 'En attente'),
        (STATUT_ECHOUE, 'Échoué'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateTimeField(default=timezone.now)  # <-- modifié
    date_debut_abonnement = models.DateField(null=True, blank=True)
    date_fin_abonnement = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_ATTENTE)
    methode = models.CharField(max_length=50, default="")  # tu l’utilises dans create()
    transaction_id = models.CharField(max_length=100, blank=True, null=True)  # idem

    class Meta:
        verbose_name_plural = "Paiements"

    def str(self):
        return f"{self.eleve} - {self.montant} ({self.statut})"

# SIGNAL : activer ou désactiver automatiquement l'abonnement après paiement
@receiver(post_save, sender=Paiement)
def activer_abonnement_apres_paiement(sender, instance, created, **kwargs):
    """
    Gère automatiquement l'abonnement de l'élève quand un paiement est enregistré ou mis à jour.
    """
    eleve = instance.eleve
    aujourd_hui = timezone.now().date()

    if instance.statut == Paiement.STATUT_COMPLET:
        # Cas 1 : Paiement validé et période d'abonnement en cours
        if instance.date_debut_abonnement <= aujourd_hui <= instance.date_fin_abonnement:
            if not eleve.abonnement_actif:
                eleve.abonnement_actif = True
                eleve.save()
        else:
            # Cas 2 : Paiement complété mais abonnement expiré
            if eleve.abonnement_actif:
                eleve.abonnement_actif = False
                eleve.save()

    else:
        # Cas 3 : Paiement en attente ou échoué → désactiver l'abonnement
        if eleve.abonnement_actif:
            eleve.abonnement_actif = False
            eleve.save()