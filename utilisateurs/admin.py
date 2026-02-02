from django.contrib import admin
from .models import Utilisateur, Eleve, Parent, Professeur

@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "type_utilisateur", "is_active")
    search_fields = ("username", "email")
    list_filter = ("type_utilisateur", "is_active")

@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ("user", "niveau", "classe")
    search_fields = ("user__username", "classe")

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username",)

@admin.register(Professeur)
class ProfesseurAdmin(admin.ModelAdmin):
    list_display = ("user", "matiere_principale", "niveau_enseigne", "experience", "biographie", "cv")
    search_fields = ("user__username", "matiere_principale")
