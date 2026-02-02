# repetiteur_ia/management/commands/programmer_sessions.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from utilisateurs.models import Eleve
from cours.models import EmploiDuTemps
from repetiteur_ia.models import SessionRevisionProgrammee

class Command(BaseCommand):
    help = 'Programme automatiquement les sessions de révision basées sur l\'emploi du temps'
    
    def handle(self, *args, **options):
        aujourdhui = timezone.now().date()
        debut_semaine = aujourdhui - timedelta(days=aujourdhui.weekday())
        
        eleves_actifs = Eleve.objects.filter(abonnement_actif=True)
        self.stdout.write(f"📅 Programmation des sessions pour {eleves_actifs.count()} élève(s) actif(s)")
        
        for eleve in eleves_actifs:
            sessions_creees = self.programmer_sessions_eleve(eleve, debut_semaine)
            self.stdout.write(
                self.style.SUCCESS(f'✓ {eleve.user.username}: {sessions_creees} session(s) programmée(s)')
            )
        
        self.stdout.write(
            self.style.SUCCESS('✅ Programmation des sessions terminée avec succès')
        )
    
    def programmer_sessions_eleve(self, eleve, debut_semaine):
        """Programme les sessions pour un élève spécifique"""
        emplois = EmploiDuTemps.objects.filter(eleve=eleve, actif=True)
        sessions_creees = 0
        
        for emploi in emplois:
            # Programmer une session 1 jour après chaque cours
            jour_cours = self.get_jour_semaine_numero(emploi.jour_semaine)
            date_session = debut_semaine + timedelta(days=jour_cours + 1)  # +1 = jour suivant
            
            # Utiliser l'heure du cours ou une heure par défaut (17h00)
            heure_session = emploi.heure_debut if emploi.heure_debut else datetime.strptime("17:00", "%H:%M").time()
            
            # Créer la datetime complète
            date_complete = timezone.make_aware(
                datetime.combine(date_session, heure_session)
            )
            
            # Vérifier si la session existe déjà cette semaine
            session_existante = SessionRevisionProgrammee.objects.filter(
                eleve=eleve,
                emploi_temps=emploi,
                date_programmation__date=date_session
            ).exists()
            
            if not session_existante and date_complete > timezone.now():
                # Créer la session programmée
                SessionRevisionProgrammee.objects.create(
                    eleve=eleve,
                    emploi_temps=emploi,
                    titre=f"Révision {emploi.matiere}",
                    date_programmation=date_complete,
                    duree_prevue=45,
                    objectifs=f"Revoir le cours de {emploi.matiere} du {emploi.jour_semaine} et consolider les acquis",
                    notes_preparation=f"Session programmée automatiquement basée sur l'emploi du temps. Cours le {emploi.jour_semaine} à {emploi.heure_debut}."
                )
                sessions_creees += 1
        
        return sessions_creees

    def get_jour_semaine_numero(self, jour_semaine):
        """Convertit le jour de la semaine en numéro"""
        jours = {
            'lundi': 0, 'mardi': 1, 'mercredi': 2, 
            'jeudi': 3, 'vendredi': 4, 'samedi': 5, 'dimanche': 6
        }
        return jours.get(jour_semaine.lower(), 0)