from django.urls import path
from .views import (
    AccueilView, ListeNotificationsView, MarquerNotificationLueView,
    SupprimerNotificationView, GestionEmploiDuTempsView, AjouterEmploiDuTempsView,
    ModifierEmploiDuTempsView, SupprimerEmploiDuTempsView, ParametresView, AideView,
    MarquerToutesNotificationsLuesView, NotificationDetailView, TableauDeBordView,
    TestRepetiteurView, fonctionnalitesView, comment_ca_marcheView, a_proposView,
    contactView, RepetiteurChatView, RepetiteurChatSendView, SoumettreCoursView,
    DemarrerSessionView, TerminerSessionView, TableauSessionsView, ProgrammerSessionsView,
)
from .views_rappels import (
    RappelsListView, envoyer_rappel_manuel, rappels_enfant_detail, tester_envoi_rappels
)
from .views_api_rappels import detail_rappel_api
from .views_api_quiz import detail_quiz_api

urlpatterns = [
    # --- Pages principales ---
    path('', AccueilView.as_view(), name='accueil'),
    path('tableau-de-bord/', TableauDeBordView.as_view(), name='tableau_de_bord'),

    # --- Pages informatives ---
    path('fonctionnalites/', fonctionnalitesView.as_view(), name='fonctionnalites'),
    path('comment-ca-marche/', comment_ca_marcheView.as_view(), name='comment_ca_marche'),
    path('a-propos/', a_proposView.as_view(), name='a_propos'),
    path('contact/', contactView.as_view(), name='contact'),

    # --- Gestion du répétiteur IA ---
    path('repetiteur-ia/', RepetiteurChatView.as_view(), name='repetiteur_ia'),
    path('repetiteur/chat/', RepetiteurChatView.as_view(), name='repetiteur_chat'), 
    path('repetiteur/chat/send/', RepetiteurChatSendView.as_view(), name='repetiteur_chat_send'),
    path('repetiteur/test-repetiteur/', TestRepetiteurView.as_view(), name='test_repetiteur'),

    # --- Gestion des sessions ---
    path('repetiteur/soumettre-cours/', SoumettreCoursView.as_view(), name='soumettre_cours'),
    path('repetiteur/sessions/', TableauSessionsView.as_view(), name='tableau_sessions'),
    path('programmer-sessions/', ProgrammerSessionsView.as_view(), name='programmer_sessions'),
    path('repetiteur/session/<int:session_id>/demarrer/', DemarrerSessionView.as_view(), name='demarrer_session'),
    path('repetiteur/session/<int:session_id>/terminer/', TerminerSessionView.as_view(), name='terminer_session'),

    # --- Gestion des notifications ---
    path('notifications/', ListeNotificationsView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='detail_notification'),
    path('notifications/marquer-comme-lue/<int:notification_id>/', MarquerNotificationLueView.as_view(), name='marquer_notification_lue'),
    path('notifications/marquer-toutes-lues/', MarquerToutesNotificationsLuesView.as_view(), name='marquer_toutes_notifications_lues'),
    path('notifications/supprimer/<int:notification_id>/', SupprimerNotificationView.as_view(), name='supprimer_notification'),

    # --- Gestion de l'emploi du temps ---
    path('emploi-du-temps/', GestionEmploiDuTempsView.as_view(), name='gestion_emploi_du_temps'),
    path('emploi-du-temps/ajouter/', AjouterEmploiDuTempsView.as_view(), name='ajouter_emploi_du_temps'),
    path('emploi-du-temps/modifier/<int:pk>/', ModifierEmploiDuTempsView.as_view(), name='modifier_emploi_du_temps'),
    path('emploi-du-temps/supprimer/<int:pk>/', SupprimerEmploiDuTempsView.as_view(), name='supprimer_emploi_du_temps'),

    # --- Pages utilitaires ---
    path('parametres/', ParametresView.as_view(), name='parametres'),
    path('aide/', AideView.as_view(), name='aide'),

    # --- Gestion des rappels ---
    path('rappels/', RappelsListView.as_view(), name='rappels_list'),
    path('rappels/envoyer-manuel/', envoyer_rappel_manuel, name='envoyer_rappel_manuel'),
    path('rappels/enfant/<int:eleve_id>/', rappels_enfant_detail, name='rappels_enfant_detail'),
    path('rappels/test/', tester_envoi_rappels, name='tester_rappels'),
    path('rappels/detail/<int:rappel_id>/', detail_rappel_api, name='detail_rappel_api'),

    # --- API Quiz ---
    path('quiz/detail/<int:quiz_attempt_id>/', detail_quiz_api, name='detail_quiz_api'),
]