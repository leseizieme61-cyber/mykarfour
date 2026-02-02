from django.urls import path
from . import views

app_name = "cours"

urlpatterns = [
    # =====================================
    # URLs pour la gestion des cours
    # =====================================
    path("", views.CoursListView.as_view(), name="list"),
    path("create/", views.CoursCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CoursDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.CoursUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.CoursDeleteView.as_view(), name="delete"),
    
    # =====================================
     # Gestion unique des inscriptions des élèves
    # =====================================
    path('<int:pk>/inscrire/', views.InscrireEleveView.as_view(), name='inscrire'),
    path('<int:pk>/desinscrire/', views.DesinscrireEleveView.as_view(), name='desinscrire'),
    
    # =====================================
    # URLs pour l'évaluation des élèves
    # =====================================
    path("<int:cours_pk>/evaluer/<int:eleve_pk>/", views.evaluer_eleve, name="evaluer"),
    
    # =====================================
    # URLs pour la gestion des quiz
    # =====================================
    path("quiz/", views.QuizListView.as_view(), name="quiz_list"),
    path("quiz/create/", views.QuizCreateView.as_view(), name="quiz_create"),
    path("quiz/<int:pk>/", views.QuizDetailView.as_view(), name="quiz_detail"),
    path("quiz/<int:pk>/update/", views.QuizUpdateView.as_view(), name="quiz_update"),
    path("quiz/<int:quiz_pk>/question/add/", views.AddQuestionView.as_view(), name="add_question"),
    
    # =====================================
    # URLs pour passer les quiz (nouvelles vues)
    # ==================================== 
    path("quiz/<int:pk>/start/", views.QuizStartView.as_view(), name="quiz_start"),
    path("quiz/attempt/<int:attempt_id>/", views.QuizTakeView.as_view(), name="quiz_take"),
    path("quiz/attempt/<int:attempt_id>/submit/", views.QuizSubmitAnswerView.as_view(), name="quiz_submit"),
    path("quiz/attempt/<int:attempt_id>/finish/", views.QuizFinishView.as_view(), name="quiz_finish"),
    path("quiz/attempt/<int:attempt_id>/results/", views.QuizResultsView.as_view(), name="quiz_results"),
    
    # =====================================
    # URLs pour la génération automatique de quiz
    # =====================================
    path("quiz/create-from-ai/", views.QuizCreateFromAIView.as_view(), name="quiz_create_from_ai"),
    path("quiz/create-from-submission/", views.QuizCreateFromSubmissionView.as_view(), name="quiz_create_from_submission"),
    
    # =====================================
    # URLs pour les emplois du temps
    # =====================================
    path("emploi-du-temps/", views.EmploiDuTempsListView.as_view(), name="emploi_du_temps_list"),
    
    # =====================================
    # URLs pour les évaluations des élèves
    # =====================================
    path("mes-evaluations/", views.MesEvaluationsView.as_view(), name="mes_evaluations"),
]