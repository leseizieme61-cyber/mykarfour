from datetime import timedelta
from django.utils import timezone
import json
import uuid
import logging

from django.views.generic import ListView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import requests

from utilisateurs.models import Eleve
from .models import Paiement

logger = logging.getLogger(__name__)

# ----------------------------
# Vue affichant les forfaits
# ----------------------------
class AbonnementsView(TemplateView):
    template_name = 'paiement/abonnements.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['forfaits'] = [
            {'duree': 1, 'prix': 100, 'nom': 'Mensuel'},
            {'duree': 3, 'prix': 100, 'nom': 'Trimestriel', 'economie': 15},
            {'duree': 12, 'prix': 100, 'nom': 'Annuel', 'economie': 30},
        ]
        return context

# ----------------------------
# Vue initiant le paiement SingPay
# ----------------------------
class ProcessusPaiementSingPayView(View):
    def get(self, request, forfait_id):
        # Vérification de l'utilisateur
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté pour effectuer un paiement.")
            return redirect('connexion')

        try:
            eleve = Eleve.objects.get(user=request.user)
        except Eleve.DoesNotExist:
            messages.error(request, "Profil élève non trouvé.")
            return redirect('accueil')

        # Définition des forfaits
        forfaits = {
            1: {'duree': 1, 'prix': 100, 'nom': 'Mensuel'},
            2: {'duree': 3, 'prix': 100, 'nom': 'Trimestriel'},
            3: {'duree': 12, 'prix': 100, 'nom': 'Annuel'},
        }
        forfait = forfaits.get(int(forfait_id))
        if not forfait:
            messages.error(request, "Forfait invalide.")
            return redirect('abonnements')

        # Préparation du payload pour SingPay
        payload = {
            "portefeuille": settings.SINGPAY_WALLET,
            "reference": f"abonnement_{forfait_id}_{request.user.id}_{uuid.uuid4().hex[:8]}",
            "redirect_success": request.build_absolute_uri(reverse('paiement_success')),
            "redirect_error": request.build_absolute_uri(reverse('paiement_error')),
            "amount": int(forfait['prix']),
            "disbursement": settings.SINGPAY_DISBURSEMENT,
            "logoURL": request.build_absolute_uri(settings.STATIC_URL + "img/logo.png"),
            "isTransfer": False
        }

        headers = {
            "accept": "*/*",
            "x-client-id": settings.SINGPAY_CLIENT_ID,
            "x-client-secret": settings.SINGPAY_CLIENT_SECRET,
            "x-wallet": settings.SINGPAY_WALLET,
            "Content-Type": "application/json",
        }

        # Envoi à SingPay
        try:
            response = requests.post("https://gateway.singpay.ga/v1/ext", json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            payment_link = data.get("link") or data.get("checkout_url") or data.get("url")
            if not payment_link:
                messages.error(request, "Impossible d'initialiser le paiement SingPay (réponse inattendue).")
                return redirect('abonnements')
            return redirect(payment_link)

        except Exception as e:
            logger.error("Erreur lors de l'initialisation du paiement : %s", e)
            messages.error(request, "Erreur lors de l'initialisation du paiement.")
            return redirect('abonnements')

# ----------------------------
# Callback SingPay (CSRF désactivé)
# ----------------------------
@method_decorator(csrf_exempt, name='dispatch')
class PaiementSingPayCallbackView(View):
    def post(self, request):
        try:
            payload = json.loads(request.body)
            logger.info("Callback reçu : %s", payload)
        except json.JSONDecodeError:
            messages.error(request, "Payload JSON invalide.")
            return render(request, "paiement/paiement_error.html")

        transaction = payload.get("transaction", {})
        reference = transaction.get("reference")
        transaction_id = transaction.get("id")
        result = transaction.get("result", "")
        amount = transaction.get("amount", 0)

        # Validation de la référence
        if not reference:
            messages.error(request, "Référence manquante dans le callback.")
            return render(request, "paiement/paiement_error.html")

        # Extraction des IDs depuis la référence
        parts = reference.split('_')
        if len(parts) < 3:
            messages.error(request, "Référence invalide.")
            return render(request, "paiement/paiement_error.html")

        try:
            forfait_id = int(parts[1])
            eleve_id = int(parts[2])
        except ValueError:
            messages.error(request, "Référence invalide (IDs).")
            return render(request, "paiement/paiement_error.html")

        forfaits = {
            1: {'duree': 1, 'prix': 100, 'nom': 'Mensuel'},
            2: {'duree': 3, 'prix': 100, 'nom': 'Trimestriel'},
            3: {'duree': 12, 'prix': 100, 'nom': 'Annuel'},
        }
        forfait = forfaits.get(forfait_id)
        if not forfait:
            messages.error(request, "Forfait inconnu.")
            return render(request, "paiement/paiement_error.html")

        try:
            eleve = Eleve.objects.get(user__id=eleve_id)
        except Eleve.DoesNotExist:
            messages.error(request, "Élève introuvable.")
            return render(request, "paiement/paiement_error.html")

        # Paiement réussi
        if result.lower() in ["success", "paid", "completed"]:
            date_debut = timezone.now().date()
            date_fin = date_debut + timedelta(days=30 * forfait['duree'])

            paiement = Paiement.objects.create(
                eleve=eleve,
                montant=forfait['prix'],
                date_paiement=timezone.now(),
                date_debut_abonnement=date_debut,
                date_fin_abonnement=date_fin,
                statut=Paiement.STATUT_COMPLET,
                methode='singpay',
                transaction_id=transaction_id
            )

            eleve.abonnement_actif = True
            eleve.date_fin_abonnement = date_fin
            eleve.save()

            return render(request, "paiement/paiement_success.html")

        # Paiement échoué
        else:
            Paiement.objects.create(
                eleve=eleve,
                montant=amount,
                date_paiement=timezone.now(),
                statut=Paiement.STATUT_ECHOUE,
                methode='singpay',
                transaction_id=transaction_id
            )
            messages.error(request, "Paiement échoué.")
            return render(request, "paiement/paiement_error.html")

    def get(self, request):
        """ Permet de tester ou vérifier un paiement via GET """
        reference = request.GET.get('reference')
        status = request.GET.get('status', 'unknown')
        transaction_id = request.GET.get('transaction_id', '')

        if not reference:
            messages.error(request, "Référence manquante.")
            return render(request, "paiement/paiement_error.html")

        payload = {
            "transaction": {
                "reference": reference,
                "id": transaction_id,
                "status": status,
                "result": status,
                "amount": 0,
            }
        }
        request._body = json.dumps(payload).encode('utf-8')
        return self.post(request)

# ----------------------------
# Vues de succès / échec
# ----------------------------
class PaiementSuccessView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        messages.success(request, "Paiement effectué avec succès ! Votre abonnement est maintenant actif.")
        return redirect('tableau_de_bord')

class PaiementErrorView(LoginRequiredMixin, TemplateView):
    template_name = 'paiement/paiement_error.html'

# ----------------------------
# Historique des paiements
# ----------------------------
class HistoriquePaiementsView(LoginRequiredMixin, ListView):
    model = Paiement
    template_name = 'paiements/historique_paiements.html'
    context_object_name = 'paiements'

    def get_queryset(self):
        if hasattr(self.request.user, 'eleve'):
            return Paiement.objects.filter(eleve__user=self.request.user).order_by('-date_paiement')
        return Paiement.objects.none()
