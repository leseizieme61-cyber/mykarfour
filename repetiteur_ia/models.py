from django.db import models
from django.conf import settings
from utilisateurs.models import Utilisateur, Eleve
from cours.models import EmploiDuTemps
import uuid

class SessionIA(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='sessions_ia')
    titre = models.CharField(max_length=255)
    date_creation = models.DateTimeField(auto_now_add=True)
    dernier_acces = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titre} ({self.eleve.user.username})"

class MessageIA(models.Model):
    ROLE_CHOICES = [
        ('élève', 'Élève'),
        ('ia', 'IA'),
    ]
    session = models.ForeignKey(SessionIA, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.session.titre}"

class EmbeddingIA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(MessageIA, on_delete=models.CASCADE, related_name='embedding')
    vector = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Embedding for Message {self.message.id}"



class HistoriqueConversation(models.Model):
    """Modèle pour sauvegarder l'historique des conversations avec Mrkarfour"""
    
    TYPE_CONVERSATION_CHOICES = [
        ('session', 'Session de révision'),
        ('libre', 'Conversation libre'),
        ('soumission', 'Soumission de cours'),
    ]
    
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    session = models.ForeignKey('SessionRevisionProgrammee', on_delete=models.CASCADE, null=True, blank=True, related_name='conversations')
    type_conversation = models.CharField(max_length=20, choices=TYPE_CONVERSATION_CHOICES, default='libre')
    question = models.TextField()
    reponse = models.TextField()
    contexte_utilise = models.JSONField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'date_creation']),
            models.Index(fields=['session', 'date_creation']),
        ]
        verbose_name = "Historique de conversation"
        verbose_name_plural = "Historiques de conversations"
    
    def __str__(self):
        return f"Conversation {self.utilisateur.username} - {self.date_creation.strftime('%Y-%m-%d %H:%M')}"
    


class Notification(models.Model):
    TYPE_RAPPEL = 'rappel'
    TYPE_PAIEMENT = 'paiement'
    TYPE_NOUVEAU_COURS = 'nouveau_cours'
    TYPE_QUIZ = 'quiz'
    TYPE_SESSION = 'session_revision'
    
    TYPE_CHOICES = [
        (TYPE_RAPPEL, 'Rappel'),
        (TYPE_PAIEMENT, 'Paiement'),
        (TYPE_NOUVEAU_COURS, 'Nouveau cours'),
        (TYPE_QUIZ, 'Quiz'),
        (TYPE_SESSION, 'Session de révision'),
    ]
    
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    lue = models.BooleanField(default=False)
    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    def __str__(self):
        return f"{self.utilisateur} - {self.type_notification}"
    
    class Meta:
        ordering = ['-date_creation']

# NOUVEAUX MODÈLES POUR LE SYSTÈME DE SESSIONS PROGRAMMÉES

class SessionRevisionProgrammee(models.Model):
    STATUT_PROGRAMMEE = 'programmee'
    STATUT_EN_COURS = 'en_cours'
    STATUT_TERMINEE = 'terminee'
    STATUT_ANNULEE = 'annulee'
    
    STATUT_CHOICES = [
        (STATUT_PROGRAMMEE, 'Programmée'),
        (STATUT_EN_COURS, 'En cours'),
        (STATUT_TERMINEE, 'Terminée'),
        (STATUT_ANNULEE, 'Annulée'),
    ]
    
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='sessions_revision')
    emploi_temps = models.ForeignKey(EmploiDuTemps, on_delete=models.CASCADE, related_name='sessions_revision')
    quiz_genere = models.ForeignKey(
        'cours.Quiz',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions_revision'
    )
    titre = models.CharField(max_length=200)
    date_programmation = models.DateTimeField()
    duree_prevue = models.IntegerField(default=45)  # en minutes
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_PROGRAMMEE)
    objectifs = models.TextField(blank=True)
    notes_preparation = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date_programmation']
        verbose_name = "Session de révision programmée"
        verbose_name_plural = "Sessions de révision programmées"
    
    def __str__(self):
        return f"{self.titre} - {self.eleve.user.username} - {self.date_programmation.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def matiere(self):
        return self.emploi_temps.matiere
    
    @property
    def est_en_cours(self):
        return self.statut == self.STATUT_EN_COURS
    
    def demarrer_session(self):
        self.statut = self.STATUT_EN_COURS
        self.save()
    
    def terminer_session(self):
        self.statut = self.STATUT_TERMINEE
        self.save()

class SoumissionCours(models.Model):
    TYPE_TEXTE = 'texte'
    TYPE_FICHIER = 'fichier'
    TYPE_AUDIO = 'audio'
    
    TYPE_CHOICES = [
        (TYPE_TEXTE, 'Texte'),
        (TYPE_FICHIER, 'Fichier'),
        (TYPE_AUDIO, 'Audio'),
    ]
    
    session = models.ForeignKey(SessionRevisionProgrammee, on_delete=models.CASCADE, related_name='soumissions')
    quiz_associe = models.ForeignKey(
        'cours.Quiz',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='soumissions_associees'
    )
    type_soumission = models.CharField(max_length=20, choices=TYPE_CHOICES)
    contenu_texte = models.TextField(blank=True)
    fichier = models.FileField(upload_to='soumissions_eleves/%Y/%m/%d/', blank=True, null=True)
    transcription_audio = models.TextField(blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    resume_automatique = models.TextField(blank=True)
    matiere = models.CharField(max_length=100, blank=True)  # Pour les soumissions sans session
    
    class Meta:
        ordering = ['-date_soumission']
        verbose_name = "Soumission de cours"
        verbose_name_plural = "Soumissions de cours"
    
    def __str__(self):
        return f"Soumission {self.session.titre} - {self.date_soumission.strftime('%d/%m/%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        if not self.matiere and self.session:
            self.matiere = self.session.emploi_temps.matiere
        super().save(*args, **kwargs)

class PlanificationAutomatique(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='planifications_auto')
    matiere = models.CharField(max_length=100)
    frequence_revision = models.IntegerField(default=2)  # fois par semaine
    duree_session = models.IntegerField(default=45)  # minutes
    preferences = models.JSONField(default=dict, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['eleve', 'matiere']
        verbose_name = "Planification automatique"
        verbose_name_plural = "Planifications automatiques"
    
    def __str__(self):
        return f"Planification {self.matiere} - {self.eleve.user.username}"

class HistoriqueChat(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='historique_chats')
    session_revision = models.ForeignKey(SessionRevisionProgrammee, on_delete=models.CASCADE, null=True, blank=True, related_name='historique_chats')
    session_ia = models.ForeignKey(SessionIA, on_delete=models.CASCADE, null=True, blank=True, related_name='historique_chats')
    question = models.TextField()
    reponse = models.TextField()
    date_echange = models.DateTimeField(auto_now_add=True)
    contexte_utilise = models.JSONField(default=dict, blank=True)
    type_echange = models.CharField(max_length=20, default='general', choices=[
        ('general', 'Général'),
        ('revision', 'Révision'),
        ('exercice', 'Exercice'),
        ('explication', 'Explication'),
    ])
    
    class Meta:
        ordering = ['-date_echange']
        verbose_name = "Historique de chat"
        verbose_name_plural = "Historiques de chat"
    
    def __str__(self):
        return f"Chat {self.utilisateur.username} - {self.date_echange.strftime('%d/%m/%Y %H:%M')}"

class DocumentPedagogique(models.Model):
    TYPE_COURS = 'cours'
    TYPE_EXERCICE = 'exercice'
    TYPE_CORRIGE = 'corrige'
    TYPE_RESUME = 'resume'
    TYPE_VIDEO = 'video'
    TYPE_AUDIO = 'audio'
    
    TYPE_CHOICES = [
        (TYPE_COURS, 'Cours'),
        (TYPE_EXERCICE, 'Exercice'),
        (TYPE_CORRIGE, 'Corrigé'),
        (TYPE_RESUME, 'Résumé'),
        (TYPE_VIDEO, 'Vidéo'),
        (TYPE_AUDIO, 'Audio'),
    ]
    
    titre = models.CharField(max_length=200)
    type_document = models.CharField(max_length=20, choices=TYPE_CHOICES)
    matiere = models.CharField(max_length=100)
    niveau = models.CharField(max_length=50)
    fichier = models.FileField(upload_to='documents_pedagogiques/%Y/%m/%d/', blank=True, null=True)
    contenu_texte = models.TextField(blank=True)
    auteur = models.CharField(max_length=100, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    est_public = models.BooleanField(default=False)
    mots_cles = models.TextField(blank=True, help_text="Mots-clés séparés par des virgules")
    
    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Document pédagogique"
        verbose_name_plural = "Documents pédagogiques"
    
    def __str__(self):
        return f"{self.titre} - {self.matiere} - {self.niveau}"

class ProgressionRevision(models.Model):
    """Suivi de la progression des révisions par matière"""
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='progression_revisions')
    matiere = models.CharField(max_length=100)
    chapitre = models.CharField(max_length=200)
    pourcentage_maitrise = models.IntegerField(default=0)  # 0-100%
    date_debut = models.DateTimeField(auto_now_add=True)
    date_revision = models.DateTimeField(null=True, blank=True)
    notes_personnelles = models.TextField(blank=True)
    difficultes_identifiees = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['eleve', 'matiere', 'chapitre']
        verbose_name = "Progression de révision"
        verbose_name_plural = "Progressions de révision"
    
    def __str__(self):
        return f"Progression {self.matiere} - {self.chapitre} - {self.eleve.user.username}"

class RappelRevision(models.Model):
    """Rappels automatiques pour les révisions"""
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='rappels_revision')
    session_programmee = models.ForeignKey(SessionRevisionProgrammee, on_delete=models.CASCADE, null=True, blank=True)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_rappel = models.DateTimeField()
    envoye = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date_rappel']
        verbose_name = "Rappel de révision"
        verbose_name_plural = "Rappels de révision"
    
    def __str__(self):
        return f"Rappel {self.titre} - {self.eleve.user.username}"