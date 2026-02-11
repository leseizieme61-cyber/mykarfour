import os

from django.core.wsgi import get_wsgi_application
settings_module = 'mykarfour_app.deployment' if os.environ.get('WEBSITE_HOSTNAME') else 'mykarfour_app.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')

application = get_wsgi_application()
