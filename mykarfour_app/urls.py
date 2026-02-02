from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404

handler404 = 'mykarfour_app.views.custom_404'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('repetiteur_ia.urls')),
    path('utilisateurs/', include('utilisateurs.urls')),
    path('cours/', include('cours.urls', namespace='cours')),
    path('quiz/', include('quiz.urls')),
    path('paiements/', include('paiement.urls')),
    path('', include('core.urls')),
]

# Servir les fichiers statiques et médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
