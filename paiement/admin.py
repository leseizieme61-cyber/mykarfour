from django.contrib import admin

from .models import Paiement

@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'montant', 'date_paiement','date_fin_abonnement', 'statut', 'methode', 'transaction_id')
    
   