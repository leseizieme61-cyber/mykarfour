from django.utils import timezone
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
import os
from django.db.models import Avg

class Cours(models.Model):
    # Liste des matières disponibles
    MATIERE_CHOICES = [
        ('mathématiques', 'Mathématiques'),
        ('physique', 'Physique'),
        ('chimie', 'Chimie'),
        ('français', 'Français'),
        ('anglais', 'Anglais'),
        ('espagnol', 'Espagnol'),
        ('histoire', 'Histoire'),
        ('géographie', 'Géographie'),
        ('philosophie', 'Philosophie'),
        ('svt', 'SVT'),
        ('technologie', 'Technologie'),
        ('eps', 'EPS'),
        ('musique', 'Musique'),
        ('arts plastiques', 'Arts Plastiques'),
    ]

    NIVEAU_CHOICES = [
        ('6ème', 'Sixième'),
        ('5ème', 'Cinquième'),
        ('4ème', 'Quatrième'),
        ('3ème', 'Troisième'),
        ('2nde', 'Seconde'),
        ('1ère', 'Première'),
        ('Tle', 'Terminale'),
    ]

    CYCLES_CHOICES = [
        ('collège', 'Collège'),
        ('lycée', 'Lycée'),
    ]

    titre = models.CharField(max_length=200, verbose_name="Titre du cours")
    matiere = models.CharField(
        max_length=100, 
        choices=MATIERE_CHOICES,
        verbose_name="Matière"
    )
    niveau = models.CharField(
        max_length=20, 
        choices=NIVEAU_CHOICES, 
        blank=True, 
        null=True,
        verbose_name="Niveau scolaire"
    )
    cycle = models.CharField(
        max_length=20,
        choices=CYCLES_CHOICES,
        blank=True,
        null=True,
        verbose_name="Cycle scolaire"
    )
    contenu = models.TextField(verbose_name="Contenu du cours")
    professeur = models.ForeignKey(
        "utilisateurs.Professeur", 
        on_delete=models.CASCADE, 
        related_name="cours"
    )
    eleves = models.ManyToManyField(
        "utilisateurs.Eleve",
        through="CoursCoursEleves",  
        related_name="cours_suivis",
        blank=True
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    # Champ pour le fichier du cours
    fichier = models.FileField(
        upload_to='cours_fichiers/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Document du cours",
        help_text="Téléchargez un document support (PDF, PowerPoint, Word, etc.) - Max 10MB"
    )

    # Nouveaux champs pour enrichir le cours
    objectifs = models.TextField(
        blank=True,
        verbose_name="Objectifs pédagogiques",
        help_text="Objectifs d'apprentissage pour ce cours"
    )
    duree_estimee = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Durée estimée (minutes)",
        help_text="Durée estimée pour compléter ce cours"
    )
    est_public = models.BooleanField(
        default=True,
        verbose_name="Cours public",
        help_text="Si cochée, le cours est visible par tous les élèves du niveau"
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Mots-clés",
        help_text="Mots-clés séparés par des virgules"
    )

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ['matiere', 'niveau', 'titre']
        indexes = [
            models.Index(fields=['matiere', 'niveau']),
            models.Index(fields=['professeur']),
            models.Index(fields=['date_creation']),
        ]

    def __str__(self):
        niveau_str = f" - {self.get_niveau_display()}" if self.niveau else ""
        return f"{self.titre} - {self.get_matiere_display()}{niveau_str}"

    def get_absolute_url(self):
        return reverse('cours:detail', kwargs={'pk': self.pk})

    def clean(self):
        """Validation des données du cours"""
        if self.fichier and self.fichier.size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError("La taille du fichier ne peut pas dépasser 10MB.")
        
        # Déterminer automatiquement le cycle si le niveau est défini
        if self.niveau and not self.cycle:
            if self.niveau in ['6ème', '5ème', '4ème', '3ème']:
                self.cycle = 'collège'
            else:
                self.cycle = 'lycée'

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # Méthodes pour le fichier
    def get_file_extension(self):
        if self.fichier and hasattr(self.fichier, 'name'):
            return self.fichier.name.split('.')[-1].lower()
        return None

    def get_filename(self):
        if self.fichier:
            return os.path.basename(self.fichier.name)
        return None

    def is_pdf(self):
        return self.get_file_extension() == 'pdf'

    def is_image(self):
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.get_file_extension() in image_extensions

    def is_document(self):
        document_extensions = ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'ods']
        return self.get_file_extension() in document_extensions

    def is_video(self):
        video_extensions = ['mp4', 'avi', 'mov', 'wmv', 'flv']
        return self.get_file_extension() in video_extensions

    def get_file_type_display(self):
        if self.is_pdf():
            return "PDF"
        elif self.is_image():
            return "Image"
        elif self.is_document():
            return "Document"
        elif self.is_video():
            return "Vidéo"
        elif self.fichier:
            return "Fichier"
        return "Aucun fichier"

    # Méthodes statistiques
    def get_eleves_inscrits_count(self):
        return self.eleves_inscrits.count()

    def get_moyenne_evaluations(self):
        moyenne = self.evaluation_set.aggregate(Avg('note'))['note__avg']
        return round(moyenne, 2) if moyenne else None

    def get_quiz_count(self):
        return self.quiz_set.count()


class CoursCoursEleves(models.Model):
    eleve = models.ForeignKey(
        'utilisateurs.Eleve', 
        on_delete=models.CASCADE, 
        related_name='cours_suivis_table'
    )
    cours = models.ForeignKey(
        Cours, 
        on_delete=models.CASCADE, 
        related_name='eleves_inscrits'
    )
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True, verbose_name="Inscription active")

    class Meta:
        verbose_name = "Inscription à un cours"
        verbose_name_plural = "Inscriptions aux cours"
        unique_together = ['eleve', 'cours']
        indexes = [
            models.Index(fields=['eleve', 'cours']),
        ]

    def __str__(self):
        return f"{self.eleve} inscrit à {self.cours}"

    def clean(self):
        # Vérifier que l'élève et le cours ont le même niveau
        if self.eleve.niveau and self.cours.niveau and self.eleve.niveau != self.cours.niveau:
            raise ValidationError("L'élève et le cours doivent avoir le même niveau.")


class EmploiDuTemps(models.Model):
    JOUR_CHOICES = [
        ('lundi', 'Lundi'), 
        ('mardi', 'Mardi'), 
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'), 
        ('vendredi', 'Vendredi'), 
        ('samedi', 'Samedi'), 
        ('dimanche', 'Dimanche'),
    ]

    # AJOUT: Relation avec Eleve
    eleve = models.ForeignKey(
        "utilisateurs.Eleve",
        on_delete=models.CASCADE,
        related_name="emplois_du_temps",
        null=True,
        blank=True,
        verbose_name="Élève"
    )
    
    cours = models.ForeignKey(
        Cours,
        on_delete=models.CASCADE,
        related_name="emplois_du_temps",
        null=True,
        blank=True
    )
    matiere = models.CharField(max_length=100, verbose_name="Matière")
    jour_semaine = models.CharField(max_length=10, choices=JOUR_CHOICES, verbose_name="Jour")
    heure_debut = models.TimeField(verbose_name="Heure de début")
    heure_fin = models.TimeField(verbose_name="Heure de fin")
    salle = models.CharField(max_length=50, blank=True, verbose_name="Salle")
    actif = models.BooleanField(default=True, verbose_name="Actif")
    document = models.FileField(
        upload_to='emplois_du_temps/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name="Document associé"
    )
    date_creation = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Emploi du temps"
        verbose_name_plural = "Emplois du temps"
        ordering = ["jour_semaine", "heure_debut"]
        indexes = [
            models.Index(fields=['eleve', 'jour_semaine', 'heure_debut']),
        ]

    def __str__(self):
        eleve_str = f" - {self.eleve}" if self.eleve else ""
        salle_str = f" - {self.salle}" if self.salle else ""
        return f"{self.matiere}{eleve_str} - {self.jour_semaine} ({self.heure_debut.strftime('%H:%M')}-{self.heure_fin.strftime('%H:%M')}){salle_str}"


class Quiz(models.Model):
    titre = models.CharField(max_length=255, verbose_name="Titre du quiz")
    description = models.TextField(blank=True, verbose_name="Description")
    cours = models.ForeignKey(
        Cours,
        on_delete=models.CASCADE,
        related_name="quiz",
        null=True,
        blank=True,
        verbose_name="Cours associé"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name="Créé par"
    )
    created_by_ai = models.BooleanField(default=False, verbose_name="Généré par IA")
    
    # CHANGER LE NOM DU CHAMP :
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    
    est_actif = models.BooleanField(default=True, verbose_name="Quiz actif")
    duree = models.PositiveIntegerField(
        default=30,
        verbose_name="Durée (minutes)",
        help_text="Durée estimée pour compléter le quiz"
    )
    points_max = models.PositiveIntegerField(
        default=20,
        verbose_name="Points maximum"
    )

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quiz"
        ordering = ['-date_creation']  # Mettre à jour ici aussi
        indexes = [
            models.Index(fields=['cours']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse('quiz:detail', kwargs={'pk': self.pk})

    def get_questions_count(self):
        return self.questions.count()

    def get_difficulte(self):
        count = self.questions.count()
        if count == 0:
            return "Non définie"
        elif count <= 5:
            return "Facile"
        elif count <= 10:
            return "Moyen"
        else:
            return "Difficile"
        
    def get_attempts_count(self):
        """Retourne le nombre de tentatives pour ce quiz"""
        return self.attempts.count()
    
    def get_average_score(self):
        """Retourne la moyenne des scores"""
        avg = self.attempts.filter(statut='termine').aggregate(Avg('score'))['score__avg']
        return round(avg, 2) if avg else 0
    
    def get_best_score(self):
        """Retourne le meilleur score"""
        best = self.attempts.filter(statut='termine').order_by('-score').first()
        return best.score if best else 0
    
    def get_completion_rate(self):
        """Retourne le taux de complétion"""
        total_attempts = self.attempts.count()
        completed_attempts = self.attempts.filter(statut='termine').count()
        return round((completed_attempts / total_attempts * 100) if total_attempts > 0 else 0, 2)
    
    def get_questions_with_choices(self):
        """Retourne les questions avec leurs choix"""
        return self.questions.prefetch_related('choices').all()
    
    def can_be_attempted_by(self, eleve):
        """Vérifie si l'élève peut tenter le quiz"""
        # Vérifier si l'élève a déjà une tentative en cours
        attempt_in_progress = self.attempts.filter(eleve=eleve, statut='en_cours').exists()
        return not attempt_in_progress and self.est_actif



class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz, 
        related_name="questions", 
        on_delete=models.CASCADE
    )
    texte = models.TextField(verbose_name="Question")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    points = models.PositiveIntegerField(default=1, verbose_name="Points")
    explication = models.TextField(blank=True, verbose_name="Explication de la réponse")

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['ordre']
        unique_together = ['quiz', 'ordre']

    def __str__(self):
        return f"{self.quiz.titre} - Q{self.ordre}: {self.texte[:40]}"

    def get_correct_choices(self):
        return self.choices.filter(est_correcte=True)

    def is_multiple_choice(self):
        return self.get_correct_choices().count() > 1


class Choice(models.Model):
    question = models.ForeignKey(
        Question, 
        related_name="choices", 
        on_delete=models.CASCADE
    )
    texte = models.CharField(max_length=512, verbose_name="Réponse")
    est_correcte = models.BooleanField(default=False, verbose_name="Est correcte")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Choix"
        verbose_name_plural = "Choix"
        ordering = ['ordre']

    def __str__(self):
        return f"{self.question.texte[:30]} -> {self.texte[:30]}"


class Evaluation(models.Model):
    cours = models.ForeignKey(
        Cours, 
        on_delete=models.CASCADE,
        related_name="evaluations"
    )
    quiz = models.ForeignKey(
        Quiz, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="evaluations"
    )
    eleve = models.ForeignKey(
        "utilisateurs.Eleve", 
        on_delete=models.CASCADE,
        related_name="evaluations"
    )
    note = models.IntegerField(
        choices=[(i, f"{i}/5") for i in range(1, 6)],
        verbose_name="Note"
    )
    commentaire = models.TextField(blank=True, verbose_name="Commentaire")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date d'évaluation")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        unique_together = ['cours', 'eleve']
        indexes = [
            models.Index(fields=['cours', 'eleve']),
            models.Index(fields=['eleve']),
        ]

    def __str__(self):
        quiz_str = f" (Quiz: {self.quiz.titre})" if self.quiz else ""
        return f"{self.eleve} - {self.cours} ({self.note}/5){quiz_str}"

    def clean(self):
        if not (1 <= self.note <= 5):
            raise ValidationError("La note doit être comprise entre 1 et 5.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_appreciation(self):
        appreciations = {
            1: "Insuffisant",
            2: "Passable", 
            3: "Bien",
            4: "Très bien",
            5: "Excellent"
        }
        return appreciations.get(self.note, "Non évalué")



class QuizAttempt(models.Model):
    """Tentative de quiz par un élève"""
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('abandonne', 'Abandonné'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    eleve = models.ForeignKey("utilisateurs.Eleve", on_delete=models.CASCADE, related_name="quiz_attempts")
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0, verbose_name="Score (%)")
    points_obtenus = models.IntegerField(default=0, verbose_name="Points obtenus")
    points_max = models.IntegerField(default=0, verbose_name="Points maximum")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_cours')
    duree_secondes = models.IntegerField(default=0, verbose_name="Durée (secondes)")
    temps_restant = models.IntegerField(null=True, blank=True, verbose_name="Temps restant (secondes)")

    class Meta:
        verbose_name = "Tentative de quiz"
        verbose_name_plural = "Tentatives de quiz"
        indexes = [
            models.Index(fields=['quiz', 'eleve']),
            models.Index(fields=['date_debut']),
        ]

    def __str__(self):
        return f"{self.eleve} - {self.quiz} ({self.score}%)"

    def calculer_score(self):
        """Calcule le score final"""
        reponses = self.reponses.all()
        points_obtenus = sum(reponse.points_obtenus for reponse in reponses)
        points_max = sum(reponse.question.points for reponse in reponses)
        
        self.points_obtenus = points_obtenus
        self.points_max = points_max
        self.score = round((points_obtenus / points_max * 100) if points_max > 0 else 0, 2)
        self.save()

    def terminer(self):
        """Termine la tentative de quiz"""
        self.date_fin = timezone.now()
        self.statut = 'termine'
        
        # Calculer la durée en secondes
        if self.date_debut and self.date_fin:
            duree = self.date_fin - self.date_debut
            self.duree_secondes = int(duree.total_seconds())
        
        self.calculer_score()
        self.save()

    def get_duree_formatee(self):
        """Retourne la durée formatée (mm:ss)"""
        if self.duree_secondes:
            minutes = self.duree_secondes // 60
            secondes = self.duree_secondes % 60
            return f"{minutes:02d}:{secondes:02d}"
        return "00:00"

    def get_temps_restant_formate(self):
        """Retourne le temps restant formaté (mm:ss)"""
        if self.temps_restant:
            minutes = self.temps_restant // 60
            secondes = self.temps_restant % 60
            return f"{minutes:02d}:{secondes:02d}"
        return None

    def get_progression(self):
        """Retourne la progression du quiz"""
        total_questions = self.quiz.questions.count()
        questions_repondues = self.reponses.count()
        return int((questions_repondues / total_questions * 100) if total_questions > 0 else 0)

    def get_appreciation(self):
        """Retourne une appréciation basée sur le score"""
        if self.score >= 90:
            return "Excellent"
        elif self.score >= 80:
            return "Très bien"
        elif self.score >= 70:
            return "Bien"
        elif self.score >= 60:
            return "Satisfaisant"
        elif self.score >= 50:
            return "Passable"
        else:
            return "Insuffisant"


class QuestionAttempt(models.Model):
    """Réponse d'un élève à une question"""
    tentative = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="reponses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choix_selectionnes = models.ManyToManyField(Choice, blank=True)
    date_reponse = models.DateTimeField(auto_now=True)
    points_obtenus = models.IntegerField(default=0)
    est_correcte = models.BooleanField(default=False)
    temps_reponse = models.IntegerField(default=0, verbose_name="Temps de réponse (secondes)")

    class Meta:
        verbose_name = "Réponse à une question"
        verbose_name_plural = "Réponses aux questions"
        unique_together = ['tentative', 'question']
        indexes = [
            models.Index(fields=['tentative', 'question']),
        ]

    def __str__(self):
        return f"{self.tentative.eleve} - {self.question}"

    def evaluer_reponse(self):
        """Évalue la réponse et calcule les points obtenus"""
        reponses_correctes = set(self.question.get_correct_choices())
        reponses_eleve = set(self.choix_selectionnes.all())
        
        # Pour les questions à choix multiples
        if self.question.is_multiple_choice():
            # Points proportionnels aux bonnes réponses sélectionnées
            bonnes_reponses = reponses_eleve.intersection(reponses_correctes)
            mauvaises_reponses = reponses_eleve - reponses_correctes
            
            if not mauvaises_reponses and bonnes_reponses == reponses_correctes:
                # Toutes les bonnes réponses, aucune mauvaise
                self.points_obtenus = self.question.points
                self.est_correcte = True
            elif bonnes_reponses:
                # Au moins une bonne réponse
                ratio = len(bonnes_reponses) / len(reponses_correctes)
                self.points_obtenus = int(self.question.points * ratio)
                self.est_correcte = False
            else:
                # Aucune bonne réponse
                self.points_obtenus = 0
                self.est_correcte = False
        else:
            # Question à choix unique
            if reponses_eleve == reponses_correctes and len(reponses_eleve) == 1:
                self.points_obtenus = self.question.points
                self.est_correcte = True
            else:
                self.points_obtenus = 0
                self.est_correcte = False
        
        self.save()
        return self.points_obtenus

    def get_choix_selectionnes_text(self):
        """Retourne le texte des choix sélectionnés"""
        return ", ".join(choice.texte for choice in self.choix_selectionnes.all())

    def get_reponses_correctes_text(self):
        """Retourne le texte des réponses correctes"""
        return ", ".join(choice.texte for choice in self.question.get_correct_choices())


class QuizSession(models.Model):
    """Session de quiz en temps réel avec timer"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions")
    eleve = models.ForeignKey("utilisateurs.Eleve", on_delete=models.CASCADE, related_name="quiz_sessions")
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin_prevue = models.DateTimeField()
    temps_restant = models.IntegerField(verbose_name="Temps restant (secondes)")
    question_actuelle = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True)
    questions_repondues = models.ManyToManyField(Question, through='QuestionSession', related_name='sessions_quiz')

    class Meta:
        verbose_name = "Session de quiz"
        verbose_name_plural = "Sessions de quiz"
        indexes = [
            models.Index(fields=['quiz', 'eleve']),
        ]

    def __str__(self):
        return f"Session {self.quiz} - {self.eleve}"

    def est_expiree(self):
        """Vérifie si la session a expiré"""
        return timezone.now() > self.date_fin_prevue

    def get_progression(self):
        """Retourne la progression de la session"""
        total_questions = self.quiz.questions.count()
        questions_repondues = self.questions_repondues.count()
        return int((questions_repondues / total_questions * 100) if total_questions > 0 else 0)


class QuestionSession(models.Model):
    """Relation entre session et questions répondue"""
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    ordre = models.PositiveIntegerField(default=0)
    repondue = models.BooleanField(default=False)
    date_reponse = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Question de session"
        verbose_name_plural = "Questions de session"
        ordering = ['ordre']
        unique_together = ['session', 'question']

    def __str__(self):
        return f"{self.session} - Q{self.ordre}"


# Méthodes supplémentaires pour les modèles existants

def ajouter_methodes_quiz():
    """Ajoute des méthodes utiles au modèle Quiz"""
    
    def get_attempts_count(self):
        """Retourne le nombre de tentatives pour ce quiz"""
        return self.attempts.count()
    
    def get_average_score(self):
        """Retourne la moyenne des scores"""
        avg = self.attempts.filter(statut='termine').aggregate(Avg('score'))['score__avg']
        return round(avg, 2) if avg else 0
    
    def get_best_score(self):
        """Retourne le meilleur score"""
        best = self.attempts.filter(statut='termine').order_by('-score').first()
        return best.score if best else 0
    
    def get_completion_rate(self):
        """Retourne le taux de complétion"""
        total_attempts = self.attempts.count()
        completed_attempts = self.attempts.filter(statut='termine').count()
        return round((completed_attempts / total_attempts * 100) if total_attempts > 0 else 0, 2)
    
    def get_questions_with_choices(self):
        """Retourne les questions avec leurs choix"""
        return self.questions.prefetch_related('choices').all()
    
    def can_be_attempted_by(self, eleve):
        """Vérifie si l'élève peut tenter le quiz"""
        # Vérifier si l'élève a déjà une tentative en cours
        attempt_in_progress = self.attempts.filter(eleve=eleve, statut='en_cours').exists()
        return not attempt_in_progress and self.est_actif

    # Ajout des méthodes au modèle Quiz
    Quiz.get_attempts_count = get_attempts_count
    Quiz.get_average_score = get_average_score
    Quiz.get_best_score = get_best_score
    Quiz.get_completion_rate = get_completion_rate
    Quiz.get_questions_with_choices = get_questions_with_choices
    Quiz.can_be_attempted_by = can_be_attempted_by


def ajouter_methodes_eleve():
    """Ajoute des méthodes utiles au modèle Eleve"""
    
    def get_quiz_completed_count(self):
        """Retourne le nombre de quiz complétés"""
        return self.quiz_attempts.filter(statut='termine').count()
    
    def get_average_quiz_score(self):
        """Retourne la moyenne des scores aux quiz"""
        avg = self.quiz_attempts.filter(statut='termine').aggregate(Avg('score'))['score__avg']
        return round(avg, 2) if avg else 0
    
    def get_total_quiz_points(self):
        """Retourne le total des points obtenus"""
        return self.quiz_attempts.filter(statut='termine').aggregate(Sum('points_obtenus'))['points_obtenus__sum'] or 0
    
    def get_quiz_in_progress(self):
        """Retourne les quiz en cours"""
        return self.quiz_attempts.filter(statut='en_cours')
    
    def get_recent_quiz_attempts(self, limit=5):
        """Retourne les tentatives récentes"""
        return self.quiz_attempts.filter(statut='termine').order_by('-date_fin')[:limit]

    # Ajout des méthodes au modèle Eleve
    from utilisateurs.models import Eleve
    Eleve.get_quiz_completed_count = get_quiz_completed_count
    Eleve.get_average_quiz_score = get_average_quiz_score
    Eleve.get_total_quiz_points = get_total_quiz_points
    Eleve.get_quiz_in_progress = get_quiz_in_progress
    Eleve.get_recent_quiz_attempts = get_recent_quiz_attempts

