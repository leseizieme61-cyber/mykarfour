from django.urls import path
from .views import (
    AbonnementsView,
    ProcessusPaiementSingPayView,
    PaiementSingPayCallbackView,
    PaiementSuccessView,
    PaiementErrorView,
    HistoriquePaiementsView
)

urlpatterns = [
    path('abonnements/', AbonnementsView.as_view(), name='abonnements'),
    path('paiement/singpay/<int:forfait_id>/', ProcessusPaiementSingPayView.as_view(), name='processus_paiement_singpay'),
    path('singpay/callback/', PaiementSingPayCallbackView.as_view(), name='singpay_callback'),
    path('paiement/singpay/success/', PaiementSuccessView.as_view(), name='paiement_success'),
    path('paiement/singpay/error/', PaiementErrorView.as_view(), name='paiement_error'),
    path('historique/', HistoriquePaiementsView.as_view(), name='historique_paiements'),
]
