import os
from .settings import *
from .settings import BASE_DIR

DEBUG = False

ALLOWED_HOSTS = [os.environ.get('WEBSITE_HOSTNAME', '*')]
CSRF_TRUSTED_ORIGINS = [f"https://{os.environ.get('WEBSITE_HOSTNAME', '')}"]

SECRET_KEY = os.environ.get('MY_SECRET_KEY', SECRET_KEY)

MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATIC_ROOT = BASE_DIR / "staticfiles"
