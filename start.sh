#!/bin/bash
set -e

# =========================
# Configuration
# =========================
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

# =========================
# Attendre PostgreSQL
# =========================
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    echo "En attente de PostgreSQL à $DB_HOST:$DB_PORT..."
    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 1
    done
    echo "PostgreSQL est prêt!"
fi

# =========================
# Créer les dossiers statiques et media
# =========================
mkdir -p /app/staticfiles /app/media
chmod -R 755 /app/staticfiles /app/media

# =========================
# Migrations Django
# =========================
echo "Application des migrations..."
python manage.py migrate --noinput

# =========================
# Collecte des fichiers statiques
# =========================
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# =========================
# Superutilisateur (optionnel)
# =========================
echo "Vérification du superutilisateur..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superutilisateur créé')
else:
    print('✅ Superutilisateur existe déjà')
" || echo "⚠️ Impossible de créer le superutilisateur"

# =========================
# Démarrer Gunicorn (WSGI)
# =========================
echo "🚀 Démarrage de Gunicorn sur $HOST:$PORT..."

# Si peu de RAM, réduire le nombre de workers à 1 ou 2
WORKERS=${WORKERS:-3}

exec gunicorn mykarfour_app.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers $WORKERS \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
