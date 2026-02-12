#!/bin/bash
set -e

# =========================
# Configuration
# =========================
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-3}

# =========================
# Attendre PostgreSQL
# =========================
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
    echo "⏳ En attente de PostgreSQL à $DB_HOST:$DB_PORT..."
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 1
    done
    echo "✅ PostgreSQL prêt !"
fi

# =========================
# Créer dossiers statiques et media
# =========================
mkdir -p /app/staticfiles /app/media
chmod -R 755 /app/staticfiles /app/media

# =========================
# Vérifier si le port est libre
# =========================
echo "🔍 Vérification du port $PORT..."
if command -v ss >/dev/null 2>&1; then
    PIDS=$(ss -tulpn | grep ":$PORT " | awk '{print $6}' | sed 's/.*pid=\([0-9]*\),.*/\1/')
elif command -v lsof >/dev/null 2>&1; then
    PIDS=$(lsof -t -i:$PORT)
else
    echo "⚠️ ss ou lsof non installés, impossible de vérifier le port"
    PIDS=""
fi

if [ -n "$PIDS" ]; then
    echo "⚠️ Port $PORT occupé, arrêt des processus existants : $PIDS"
    kill -9 $PIDS || true
    sleep 1
fi

# =========================
# Migrations Django
# =========================
echo "🛠 Application des migrations..."
python manage.py migrate --noinput

# =========================
# Collecte des fichiers statiques
# =========================
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# =========================
# Création superutilisateur
# =========================
echo "👤 Vérification du superutilisateur..."
python - <<END
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
END

# =========================
# Lancement de Gunicorn
# =========================
echo "🚀 Démarrage de Gunicorn sur $HOST:$PORT..."
# Note : --keep-alive est le bon argument
exec gunicorn mykarfour_app.wsgi:application \
    --bind "$HOST:$PORT" \
    --workers $WORKERS \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -
