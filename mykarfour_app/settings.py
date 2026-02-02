from pathlib import Path
import os
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9-dq6zswi368l8_4qt)-7f+m22hyi^l0elh+1nv1x8^w!$*ikm'

DEBUG = True

APPEND_SLASH = False

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    "https://c9d34914b191.ngrok-free.app"
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'utilisateurs',
    'django_extensions',
    'cours',
    'notifications',
    'paiement',
    'quiz',
    'repetiteur_ia',
    'rest_framework',
    'django_bootstrap5',
    'crispy_forms',
    'core',
    'channels'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mykarfour_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mykarfour_app.wsgi.application'
ASGI_APPLICATION = 'mykarfour_app.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.postgresql',
         'NAME': os.getenv('DB_NAME', 'mykarfour_db'),
         'USER': os.getenv('DB_USER', 'postgres'),
         'PASSWORD': os.getenv('DB_PASSWORD', ''),
         'HOST': os.getenv('DB_HOST', 'localhost'),
         'PORT': os.getenv('DB_PORT', 5432),
     }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Libreville'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configuration Vectorstore
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "data", "vector_store.faiss")

AUTH_USER_MODEL = 'utilisateurs.Utilisateur'

LOGIN_URL = 'connexion'
LOGIN_REDIRECT_URL = 'profil'
LOGOUT_REDIRECT_URL = 'accueil'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'


# Configuration de l'API IA
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')


# IA_API_URL = 'https://api.openai.com/v1/completions'

# # Configuration email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "maildev")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 1025))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "angominkohyirimjohann@gmail.com")


# # Configuration SMS
# SMS_PROVIDER = config('SMS_PROVIDER', default='airtel')
# AIRTEL_SMS_API_KEY = config('AIRTEL_SMS_API_KEY', default='')
# AIRTEL_SMS_API_URL = config('AIRTEL_SMS_API_URL', default='https://api.airtel.africa/sms/v1/send')
# AIRTEL_SENDER_ID = config('AIRTEL_SENDER_ID', default='REPETITEUR')
# LIBERTIS_SMS_API_KEY = config('LIBERTIS_SMS_API_KEY', default='')
# LIBERTIS_SMS_API_URL = config('LIBERTIS_SMS_API_URL', default='https://api.libertis.ci/sms/send')
# LIBERTIS_SENDER_ID = config('LIBERTIS_SENDER_ID', default='REPETITEUR')

# Configuration SINGPAY
SINGPAY_CLIENT_ID = "46abf755-d18c-46f8-a7c1-6f12cab94673"
SINGPAY_CLIENT_SECRET = "f49c4e98162452e796e2c08aae032dd77b5cbf712bb619e33f8011052885488f"
SINGPAY_WALLET = "64c151d6da4b4c7e9abc691c"
SINGPAY_DISBURSEMENT = "660051e9fb48d1d824589b97"

# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# channel layer (Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# site url (utilisé pour lien dans emails, optionnel)
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
