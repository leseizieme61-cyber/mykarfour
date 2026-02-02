from django.contrib import admin
from .models import Cours, CoursCoursEleves, EmploiDuTemps, Quiz, Evaluation, Question, Choice

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ("titre", "matiere", "professeur", "date_creation")
    
@admin.register(CoursCoursEleves)
class CoursCoursElevesAdmin(admin.ModelAdmin):
    list_display = ("eleve", "cours", "date_inscription")
    

@admin.register(EmploiDuTemps)
class EmploiDuTempsAdmin(admin.ModelAdmin):
    list_display = ("jour_semaine", "heure_debut", "heure_fin", "actif")
    

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("titre", "cours",  "created_by", "created_by_ai",  "date_creation", "duree", "points_max")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("texte", "quiz", "ordre")
    list_filter = ("quiz",)
    inlines = [ChoiceInline]

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("texte", "question", "est_correcte")
    list_filter = ("est_correcte",)
    

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("cours", "eleve", "note", "date_creation")

