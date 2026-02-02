from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('a-propos/', views.about, name='about'),
    path('fonctionnalites/', views.features, name='features'),
    path('comment-ca-marche/', views.how_it_works, name='how_it_works'),
    path('tarifs/', views.pricing, name='pricing'),
    path('technologie/', views.tech, name='tech'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
]
