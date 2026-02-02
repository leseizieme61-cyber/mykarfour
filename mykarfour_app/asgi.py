"""
ASGI config for mykarfour_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import repetiteur_ia.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            repetiteur_ia.routing.websocket_urlpatterns
        )
    ),
})
