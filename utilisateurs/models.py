from django.utils import timezone  # Correction de l'import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.db.models import Avg


class Utilisateur(AbstractUser):
    EST_ELEVE = 'élève'
    EST_PARENT = 'parent'
    EST_PROFESSEUR = 'professeur'
    
    TYPE_UTILISATEUR = [
        (EST_ELEVE, 'Élève'),
        (EST_PARENT, 'Parent'),
        (EST_PROFESSEUR, 'Professeur'),
    ]
    
    type_utilisateur = models.CharField(max_length=20, choices=TYPE_UTILISATEUR)
    last_name = models.CharField(max_length=150, verbose_name="Nom de famille")
    first_name = models.CharField(max_length=150, verbose_name="Prénom")
    email = models.EmailField(unique=True, verbose_name="Adresse email")
    naissance = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    telephone = models.CharField(max_length=20, blank=True)
    email_notifications = models.BooleanField(default=True, verbose_name="Notifications par email")
    sms_notifications = models.BooleanField(default=False, verbose_name="Notifications par SMS")
    push_notifications = models.BooleanField(default=False, verbose_name="Notifications push")
    
    def __str__(self):
        return f"{self.username} ({self.type_utilisateur})"
    
    def peut_recevoir_sms(self):
        return self.sms_notifications and self.telephone and len(self.telephone) >= 8
class Parent(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    eleves = models.ManyToManyField('Eleve', related_name='mes_parents', blank=True)
    
    # Nouveaux champs pour les préférences de notifications
    notifications_quotidiennes = models.BooleanField(default=True, verbose_name="Notifications quotidiennes")
    notifications_hebdomadaires = models.BooleanField(default=True, verbose_name="Rapports hebdomadaires")
    notifications_evaluations = models.BooleanField(default=True, verbose_name="Nouvelles évaluations")
    notifications_quiz = models.BooleanField(default=True, verbose_name="Nouveaux quiz réalisés")
    
    def __str__(self):
        enfants = [str(eleve) for eleve in self.eleves.all()]
        if enfants:
            return f"Parent de {', '.join(enfants)}"
        return f"{self.user.get_full_name() or self.user.username} (Parent)"

class Eleve(models.Model):
    # Niveaux scolaires
    NIVEAU_COLLEGE = 'college'
    NIVEAU_LYCEE = 'lycee'

    NIVEAUX = [
        (NIVEAU_COLLEGE, 'Collège'),
        (NIVEAU_LYCEE, 'Lycée'),
    ]

    # Classes pour le collège
    CLASSES_COLLEGE = [
        ('6e', 'Sixième'),
        ('5e', 'Cinquième'),
        ('4e', 'Quatrième'),
        ('3e', 'Troisième'),
    ]

    # Classes pour le lycée
    CLASSES_LYCEE = [
        ('2nde', 'Seconde'),
        ('1ere', 'Première'),
        ('term', 'Terminale'),
    ]

    # Relations et infos utilisateur
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)

    # Champs spécifiques à l'élève
    etablissement = models.CharField(max_length=255, null=True, blank=True, verbose_name="Établissement")
    niveau = models.CharField(max_length=20, choices=NIVEAUX, null=True, blank=True, verbose_name="Niveau scolaire")
    classe = models.CharField(max_length=20, null=True, blank=True, verbose_name="Classe")
    abonnement_actif = models.BooleanField(default=False)
    date_fin_abonnement = models.DateField(null=True, blank=True)
    code_parrainage = models.CharField(max_length=10, unique=True, null=True, blank=True)

    
    def verifier_abonnement(self):
        """Met automatiquement à jour le statut selon la date d'expiration."""
        if self.date_fin_abonnement:
            if timezone.now().date() > self.date_fin_abonnement:
                self.abonnement_actif = False
            else:
                self.abonnement_actif = True
        else:
            self.abonnement_actif = False
        self.save()

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def save(self, *args, **kwargs):
        if not self.code_parrainage:
            self.code_parrainage = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def get_classes_disponibles(self):
        """Retourne les classes disponibles selon le niveau sélectionné"""
        if self.niveau == self.NIVEAU_COLLEGE:
            return self.CLASSES_COLLEGE
        elif self.niveau == self.NIVEAU_LYCEE:
            return self.CLASSES_LYCEE
        return []

    def get_classe_display(self):
        """Retourne le nom d'affichage de la classe"""
        if self.niveau == self.NIVEAU_COLLEGE:
            return dict(self.CLASSES_COLLEGE).get(self.classe, self.classe)
        elif self.niveau == self.NIVEAU_LYCEE:
            return dict(self.CLASSES_LYCEE).get(self.classe, self.classe)
        return self.classe

    def get_niveau_display(self):
        """Retourne le nom d'affichage du niveau"""
        return dict(self.NIVEAUX).get(self.niveau, self.niveau)

    def get_quiz_completed_count(self):
        """Retourne le nombre de quiz complétés"""
        try:
            from cours.models import QuizAttempt
            return QuizAttempt.objects.filter(eleve=self, statut='termine').count()
        except (ImportError, Exception):
            return 0
    
    def get_average_quiz_score(self):
        """Retourne la moyenne des scores aux quiz"""
        try:
            from cours.models import QuizAttempt
            avg = QuizAttempt.objects.filter(eleve=self, statut='termine').aggregate(Avg('score'))['score__avg']
            return round(avg, 2) if avg else 0
        except (ImportError, Exception):
            return 0
    
    def get_total_quiz_points(self):
        """Retourne le total des points obtenus"""
        try:
            from cours.models import QuizAttempt
            from django.db.models import Sum
            return QuizAttempt.objects.filter(eleve=self, statut='termine').aggregate(Sum('points_obtenus'))['points_obtenus__sum'] or 0
        except (ImportError, Exception):
            return 0
    
    def get_quiz_in_progress(self):
        """Retourne les quiz en cours"""
        try:
            from cours.models import QuizAttempt
            return QuizAttempt.objects.filter(eleve=self, statut='en_cours')
        except (ImportError, Exception):
            return QuizAttempt.objects.none()
    
    def get_recent_quiz_attempts(self, limit=5):
        """Retourne les tentatives récentes"""
        try:
            from cours.models import QuizAttempt
            return QuizAttempt.objects.filter(eleve=self, statut='termine').order_by('-date_fin')[:limit]
        except (ImportError, Exception):
            return QuizAttempt.objects.none()


class Professeur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE)
    matiere_principale = models.CharField(max_length=100, verbose_name="Matière principale")
    niveau_enseigne = models.CharField(
        max_length=20,
        choices=Eleve.NIVEAUX,
        verbose_name="Niveau enseigné"
    )
    biographie = models.TextField(blank=True, verbose_name="Biographie")
    experience = models.PositiveIntegerField(null=True, blank=True, verbose_name="Années d'expérience")
    cv = models.FileField(upload_to='cv_professeurs/', null=True, blank=True, verbose_name="CV (PDF)")

    def __str__(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=Utilisateur)
def envoyer_email_bienvenue(sender, instance, created, **kwargs):
    if created:
        subject = 'Bienvenue sur Mykarfour'
        message = f"""
        Bonjour {instance.first_name},
        
        Bienvenue sur MyKarfour! Votre compte a été créé avec succès.
        
        Commencez dès maintenant à bénéficier de notre répétiteur Mrkarfour personnalisé.
        
        Cordialement,
        L'équipe Répétiteur Mrkarfour
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
            fail_silently=False,
        )