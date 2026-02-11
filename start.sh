#!/bin/bash
set -e

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# =========================
# Attente PostgreSQL
# =========================
if [ -n "$DATABASE_URL" ]; then
    DB_HOST=$(echo "$DATABASE_URL" | grep -oP "@\K[^:]+" || echo "")
    DB_PORT=$(echo "$DATABASE_URL" | grep -oP ":[0-9]+(?=/)" | tr -d ":" || echo "")
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        echo "⏳ En attente de PostgreSQL à $DB_HOST:$DB_PORT..."
        for i in {1..30}; do
            if nc -z $DB_HOST $DB_PORT 2>/dev/null; then
                echo "✅ PostgreSQL prêt!"
                break
            fi
            sleep 1
        done
    fi
fi

# =========================
# Migrations Django
# =========================
echo "🔄 Application des migrations..."
python manage.py migrate --noinput

# =========================
# Collectstatic
# =========================
echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# =========================
# Permissions
# =========================
chmod -R 755 /app/staticfiles /app/media

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
" || echo "⚠️  Impossible de créer le superutilisateur"

# =========================
# Lancement Daphne
# =========================
echo "🚀 Démarrage de Daphne sur $HOST:$PORT..."
exec daphne -b $HOST -p $PORT mykarfour_app.asgi:application
