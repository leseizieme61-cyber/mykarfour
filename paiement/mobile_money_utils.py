import requests
from django.conf import settings
from django.urls import reverse

def initier_paiement_mobile_money(forfait, eleve, request):
    forfaits = {
        1: {'duree': 1, 'prix': 9.99, 'nom': 'Mensuel'},
        2: {'duree': 3, 'prix': 24.99, 'nom': 'Trimestriel'},
        3: {'duree': 12, 'prix': 89.99, 'nom': 'Annuel'},
    }
    
    forfait_info = forfaits.get(forfait)
    if not forfait_info:
        return None

    # URL de callback pour la confirmation de paiement
    callback_url = request.build_absolute_uri(
        reverse('mobile_money_callback')
    )

    # Données à envoyer à l'API mobile money
    data = {
        'amount': forfait_info['prix'],
        'currency': 'XOF',
        'customer_phone_number': eleve.user.telephone,  # Supposons que le numéro est stocké
        'merchant_code': settings.MOBILE_MONEY_CONFIG['MERCHANT_CODE'],
        'callback_url': callback_url,
        'order_id': f"abonnement_{forfait}_{eleve.user.id}",
        'description': f"Abonnement {forfait_info['nom']} - Répétiteur IA"
    }

    # Headers avec l'authentification
    headers = {
        'Authorization': f'Bearer {settings.MOBILE_MONEY_CONFIG["API_KEY"]}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            settings.MOBILE_MONEY_CONFIG['API_URL'],
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()  # Retourne la réponse de l'API (contient l'URL de paiement, etc.)
    except requests.RequestException as e:
        print(f"Erreur lors de l'appel API mobile money: {e}")
        return None