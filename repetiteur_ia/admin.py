# repetiteur_ia/admin.py
from django.contrib import admin
from .models import (
    SessionIA, MessageIA, EmbeddingIA, Notification,
    SessionRevisionProgrammee, SoumissionCours, PlanificationAutomatique,
    HistoriqueChat, DocumentPedagogique, ProgressionRevision, RappelRevision, HistoriqueConversation
)

@admin.register(SessionIA)
class SessionIAAdmin(admin.ModelAdmin):
    list_display = ['titre', 'eleve', 'date_creation', 'dernier_acces']
    list_filter = ['date_creation', 'eleve__user__username']
    search_fields = ['titre', 'eleve__user__username']
    readonly_fields = ['date_creation', 'dernier_acces']

@admin.register(MessageIA)
class MessageIAAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'date_envoi', 'contenu_preview']
    list_filter = ['role', 'date_envoi']
    search_fields = ['contenu', 'session__titre']
    readonly_fields = ['date_envoi']
    
    def contenu_preview(self, obj):
        return obj.contenu[:50] + "..." if len(obj.contenu) > 50 else obj.contenu
    contenu_preview.short_description = 'Contenu'

@admin.register(EmbeddingIA)
class EmbeddingIAAdmin(admin.ModelAdmin):
    list_display = ['message', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'type_notification', 'message_preview', 'date_creation', 'lue']
    list_filter = ['type_notification', 'lue', 'date_creation']
    search_fields = ['message', 'utilisateur__username']
    list_editable = ['lue']
    readonly_fields = ['date_creation']
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

@admin.register(SessionRevisionProgrammee)
class SessionRevisionProgrammeeAdmin(admin.ModelAdmin):
    list_display = ['titre', 'eleve', 'matiere', 'date_programmation', 'statut', 'duree_prevue']
    list_filter = ['statut', 'date_programmation', 'emploi_temps__matiere']
    search_fields = ['titre', 'eleve__user__username', 'objectifs']
    readonly_fields = ['date_creation', 'date_modification']
    list_editable = ['statut']
    
    def matiere(self, obj):
        return obj.emploi_temps.matiere
    matiere.short_description = 'Matière'

@admin.register(SoumissionCours)
class SoumissionCoursAdmin(admin.ModelAdmin):
    list_display = ['session', 'type_soumission', 'matiere', 'date_soumission', 'resume_preview']
    list_filter = ['type_soumission', 'date_soumission']
    search_fields = ['session__titre', 'contenu_texte', 'matiere']
    readonly_fields = ['date_soumission']
    
    def resume_preview(self, obj):
        return obj.resume_automatique[:50] + "..." if obj.resume_automatique else "Aucun résumé"
    resume_preview.short_description = 'Résumé automatique'

@admin.register(PlanificationAutomatique)
class PlanificationAutomatiqueAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'matiere', 'frequence_revision', 'duree_session', 'actif']
    list_filter = ['actif', 'matiere']
    search_fields = ['eleve__user__username', 'matiere']
    list_editable = ['actif']

@admin.register(HistoriqueChat)
class HistoriqueChatAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'session_info', 'type_echange', 'date_echange', 'question_preview']
    list_filter = ['type_echange', 'date_echange', 'utilisateur']
    search_fields = ['question', 'reponse', 'utilisateur__username']
    readonly_fields = ['date_echange']
    
    def session_info(self, obj):
        if obj.session_revision:
            return f"Révision: {obj.session_revision.titre}"
        elif obj.session_ia:
            return f"IA: {obj.session_ia.titre}"
        return "Sans session"
    session_info.short_description = 'Session'
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'

@admin.register(DocumentPedagogique)
class DocumentPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_document', 'matiere', 'niveau', 'est_public', 'date_creation']
    list_filter = ['type_document', 'matiere', 'niveau', 'est_public']
    search_fields = ['titre', 'matiere', 'contenu_texte', 'mots_cles']
    list_editable = ['est_public']

@admin.register(ProgressionRevision)
class ProgressionRevisionAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'matiere', 'chapitre', 'pourcentage_maitrise', 'date_revision']
    list_filter = ['matiere', 'pourcentage_maitrise']
    search_fields = ['eleve__user__username', 'matiere', 'chapitre']
    readonly_fields = ['date_debut']

@admin.register(RappelRevision)
class RappelRevisionAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'titre', 'date_rappel', 'envoye']
    list_filter = ['envoye', 'date_rappel']
    search_fields = ['titre', 'eleve__user__username', 'message']
    list_editable = ['envoye']


@admin.register(HistoriqueConversation)
class HistoriqueConversationAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'session', 'question', 'reponse', 'contexte_utilise',  'date_creation']
    list_filter = ['date_creation', 'contexte_utilise']
    search_fields = ['utilisateur__username', 'session__titre', 'question', 'reponse']
    readonly_fields = ['date_creation']