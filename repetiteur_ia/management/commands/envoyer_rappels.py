# repetiteur_ia/management/commands/envoyer_rappels.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.mail import send_mail
from django.conf import settings
from utilisateurs.models import Eleve
from repetiteur_ia.models import RappelRevision, SessionRevisionProgrammee
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envoie les rappels automatiques aux élèves pour les révisions et connexions'
    
    def handle(self, *args, **options):
        self.stdout.write('📧 Démarrage de l\'envoi des rappels automatiques...')
        
        # 1. Rappels de sessions programmées aujourd'hui
        rappels_sessions = self.envoyer_rappels_sessions_aujourdhui()
        
        # 2. Rappels pour élèves inactifs (3+ jours sans connexion)
        rappels_inactivite = self.envoyer_rappels_inactivite()
        
        # 3. Rappels de révision hebdomadaires
        rappels_hebdo = self.envoyer_rappels_hebdomadaires()
        
        total = rappels_sessions + rappels_inactivite + rappels_hebdo
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ {total} rappel(s) envoyé(s) avec succès')
        )
        self.stdout.write(f'   - Sessions aujourd\'hui: {rappels_sessions}')
        self.stdout.write(f'   - Inactivité: {rappels_inactivite}')
        self.stdout.write(f'   - Hebdomadaires: {rappels_hebdo}')
    
    def envoyer_rappels_sessions_aujourdhui(self):
        """Envoie les rappels pour les sessions programmées aujourd'hui"""
        aujourdhui = timezone.now().date()
        demain = aujourdhui + timedelta(days=1)
        
        # Sessions d'aujourd'hui et de demain
        sessions = SessionRevisionProgrammee.objects.filter(
            date_programmation__date__in=[aujourdhui, demain],
            statut='programmee'
        ).select_related('eleve__user', 'emploi_temps')
        
        rappels_envoyes = 0
        
        for session in sessions:
            if session.eleve.user.email:
                try:
                    # Déterminer si c'est aujourd'hui ou demain
                    if session.date_programmation.date() == aujourdhui:
                        delai = "aujourd'hui"
                        heure = session.date_programmation.strftime('à %H:%M')
                    else:
                        delai = "demain"
                        heure = session.date_programmation.strftime('à %H:%M')
                    
                    sujet = f"📚 Rappel : Votre session de révision {delai} {heure}"
                    
                    message = f"""
Bonjour {session.eleve.user.first_name} 👋,

Ceci est un rappel amical pour votre session de révision :

📖 **Matière :** {session.emploi_temps.matiere if session.emploi_temps else session.titre}
⏰ **Quand :** {delai} {heure}
🎯 **Objectif :** {session.objectifs}

Votre répétiteur IA MrKarfour vous attend pour vous aider à réviser efficacement !

🔗 **Accédez directement à votre session :**
{getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')}/repetiteur/chat/

N'oubliez pas que la régularité est la clé du succès ! 💪

Cordialement,
L'équipe MyKarfour 🎓
                    """.strip()
                    
                    send_mail(
                        sujet,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [session.eleve.user.email],
                        fail_silently=False,
                    )
                    
                    # Créer le rappel en base
                    RappelRevision.objects.create(
                        eleve=session.eleve,
                        session_programmee=session,
                        titre=f"Rappel session {session.emploi_temps.matiere if session.emploi_temps else session.titre}",
                        message=message,
                        date_rappel=timezone.now(),
                        envoye=True
                    )
                    
                    rappels_envoyes += 1
                    self.stdout.write(f'  ✓ Rappel envoyé à {session.eleve.user.username} pour {session.titre}')
                    
                except Exception as e:
                    logger.error(f"Erreur envoi rappel session {session.id}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Erreur envoi à {session.eleve.user.username}: {e}')
                    )
        
        return rappels_envoyes
    
    def envoyer_rappels_inactivite(self):
        """Envoie des rappels aux élèves inactifs depuis 3+ jours"""
        il_y_a_3_jours = timezone.now() - timedelta(days=3)
        
        # Élèves avec abonnement actif mais inactifs
        eleves_inactifs = Eleve.objects.filter(
            abonnement_actif=True,
            user__last_login__lt=il_y_a_3_jours
        ).exclude(user__last_login__isnull=True)
        
        rappels_envoyes = 0
        
        for eleve in eleves_inactifs:
            if eleve.user.email:
                try:
                    jours_inactivite = (timezone.now() - eleve.user.last_login).days
                    
                    sujet = f"🔄 On vous attend ! {jours_inactivite} jours sans révision"
                    
                    message = f"""
Salut {eleve.user.first_name} ! 🌟

Ça fait {jours_inactivite} jours que nous ne vous avons pas vu sur MyKarfour...

Votre progression nous manque ! 😢
Chaque jour sans révision est une opportunité manquée d'atteindre vos objectifs.

🎯 **Pourquoi revenir maintenant ?**
• Reprendre le rythme de révision
• Consoliderez vos acquis
• Éviter l'accumulation de retard
• MrKarfour a préparé de nouveaux exercices pour vous !

🚀 **Reconnectez-vous en 2 clics :**
{getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')}/utilisateurs/connexion/

N'oubliez pas : 15 minutes de révision valent mieux que zéro ! ⏰

On compte sur vous ! 💪

L'équipe MyKarfour 🎓
                    """.strip()
                    
                    send_mail(
                        sujet,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [eleve.user.email],
                        fail_silently=False,
                    )
                    
                    # Créer le rappel en base
                    RappelRevision.objects.create(
                        eleve=eleve,
                        titre=f"Rappel inactivité ({jours_inactivite} jours)",
                        message=message,
                        date_rappel=timezone.now(),
                        envoye=True
                    )
                    
                    rappels_envoyes += 1
                    self.stdout.write(f'  ✓ Rappel inactivité envoyé à {eleve.user.username} ({jours_inactivite} jours)')
                    
                except Exception as e:
                    logger.error(f"Erreur envoi rappel inactivité {eleve.id}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Erreur envoi à {eleve.user.username}: {e}')
                    )
        
        return rappels_envoyes
    
    def envoyer_rappels_hebdomadaires(self):
        """Envoie des rappels de révision hebdomadaires (le dimanche soir)"""
        # Uniquement le dimanche soir
        if timezone.now().weekday() != 6:  # 6 = dimanche
            return 0
        
        eleves_actifs = Eleve.objects.filter(abonnement_actif=True)
        rappels_envoyes = 0
        
        for eleve in eleves_actifs:
            if eleve.user.email:
                try:
                    sujet = "📅 Préparez votre semaine de révision !"
                    
                    message = f"""
Bonsoir {eleve.user.first_name} ! 🌙

La semaine se termine, mais pas vos progrès ! 

🎯 **Objectifs pour la semaine à venir :**
• Réviser chaque jour 15-30 minutes
• Compléter au moins 2 sessions avec MrKarfour
• Faire les quiz générés automatiquement
• Consulter votre rapport de progression

📊 **Votre progression cette semaine :**
• Sessions complétées : [À calculer]
• Quiz réussis : [À calculer]  
• Temps total : [À calculer]

🚀 **Commencez la semaine du bon pied :**
{getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')}/dashboard/

La régularité est votre meilleur allié pour la réussite ! 📚

Bonne semaine et bon courage ! 💪

L'équipe MyKarfour 🎓
                    """.strip()
                    
                    send_mail(
                        sujet,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [eleve.user.email],
                        fail_silently=False,
                    )
                    
                    # Créer le rappel en base
                    RappelRevision.objects.create(
                        eleve=eleve,
                        titre="Rappel hebdomadaire",
                        message=message,
                        date_rappel=timezone.now(),
                        envoye=True
                    )
                    
                    rappels_envoyes += 1
                    self.stdout.write(f'  ✓ Rappel hebdomadaire envoyé à {eleve.user.username}')
                    
                except Exception as e:
                    logger.error(f"Erreur envoi rappel hebdomadaire {eleve.id}: {e}")
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Erreur envoi à {eleve.user.username}: {e}')
                    )
        
        return rappels_envoyes
