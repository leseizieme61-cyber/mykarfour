from pathlib import Path
import os
import environ

# =========================
# 📁 BASE DIR
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# 🌱 ENVIRONNEMENT
# =========================

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# =========================
# 🔐 SÉCURITÉ
# =========================

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["*"]
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# =========================
# 📦 APPLICATIONS
# =========================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Apps locales
    "utilisateurs",
    "cours",
    "notifications",
    "paiement",
    "quiz",
    "repetiteur_ia",
    "core",

    # Tierces
    "rest_framework",
    "django_bootstrap5",
    "crispy_forms",
    "channels",
]

# =========================
# 🧱 MIDDLEWARE
# =========================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =========================
# 🌐 URLS / TEMPLATES
# =========================

ROOT_URLCONF = "mykarfour_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mykarfour_app.wsgi.application"
ASGI_APPLICATION = "mykarfour_app.asgi.application"

# =========================
# 🗄️ BASE DE DONNÉES (POSTGRES)
# =========================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

# =========================
# 🔐 AUTH
# =========================

AUTH_USER_MODEL = "utilisateurs.Utilisateur"

LOGIN_URL = "connexion"
LOGIN_REDIRECT_URL = "profil"
LOGOUT_REDIRECT_URL = "accueil"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# 🌍 INTERNATIONALISATION
# =========================

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Libreville"

USE_I18N = True
USE_TZ = True

# =========================
# 📁 STATIC & MEDIA
# =========================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================
# 🎨 CRISPY
# =========================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# =========================
# 🤖 OPENAI
# =========================

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")

# =========================
# ✉️ EMAIL
# =========================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# =========================
# 🔄 CHANNELS / REDIS
# =========================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://redis:6379/0")],
        },
    },
}

# =========================
# 🌐 SITE
# =========================

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# =========================
# 🆔 DIVERS
# =========================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
