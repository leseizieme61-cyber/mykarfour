from django.urls import path
from .views import (
    InscriptionView, ConnexionView, DeconnexionView, 
    ProfilView, LierEnfantView, ChargerClassesView, UpdateNotificationsView, ParemetresView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,ParentDashboardView, ParentEvaluationsDetailView, ParentQuizDetailView,
    UpdateParentNotificationsView, GenererRapportParentView
)

urlpatterns = [
    path('inscription/', InscriptionView.as_view(), name='inscription'),
    path('connexion/', ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('profil/', ProfilView.as_view(), name='profil'),
    path('update-notifications/', UpdateNotificationsView.as_view(), name='update_notifications'),
    path('profil/lier-enfant/', LierEnfantView.as_view(), name='lier_enfant'),
    # URLs pour le parent
    path('parent/dashboard/', ParentDashboardView.as_view(), name='parent_dashboard'),
    path('parent/enfant/<int:eleve_id>/evaluations/', ParentEvaluationsDetailView.as_view(), name='parent_evaluations_detail'),
    path('parent/enfant/<int:eleve_id>/quiz/', ParentQuizDetailView.as_view(), name='parent_quiz_detail'),
    path('parent/notifications/update/', UpdateParentNotificationsView.as_view(), name='parent_update_notifications'),
    path('parent/generer-rapport/', GenererRapportParentView.as_view(), name='parent_generer_rapport'),
    
    path('charger-classes/', ChargerClassesView.as_view(), name='charger_classes'),
    path('parametres/', ParemetresView.as_view(), name='parametres'),
    path('reset-password/', CustomPasswordResetView.as_view(), name='reset_password'),
    path('reset-password/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset-password/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset-password/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]