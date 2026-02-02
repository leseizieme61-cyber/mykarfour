from django.urls import path
from .views import DetailQuizView, SoumettreQuizView

urlpatterns = [
    path('<int:pk>/', DetailQuizView.as_view(), name='detail_quiz'),
    path('<int:pk>/soumettre/', SoumettreQuizView.as_view(), name='soumettre_quiz'),
]