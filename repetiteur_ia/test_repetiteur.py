import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')
django.setup()

from repetiteur_ia.utils import repondre_au_repetiteur

try:
    response = repondre_au_repetiteur(
        question="Bonjour, pouvez-vous m'expliquer les fractions ?",
        contexte_pedagogique={},
        niveau_eleve="Collège"
    )
    print("✅ Test réussi !")
    print("Réponse:", response)
except Exception as e:
    print("❌ Erreur:", e)