# =========================
# Image de base Python légère
# =========================
FROM python:3.12-slim As prod

# =========================
# Variables d'environnement
# =========================
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# =========================
# Dépendances système
# =========================
RUN apt-get update && \
    apt-get install -y gcc libpq-dev curl netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# =========================
# Dépendances Python
# =========================
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# =========================
# Copier l'application
# =========================
COPY . .

# =========================
# Script de démarrage
# =========================
RUN echo '#!/bin/bash
set -e

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}

# =========================
# Attente PostgreSQL si nécessaire
# =========================
if [ -n "$DATABASE_URL" ]; then
    DB_HOST=$(echo "$DATABASE_URL" | grep -oP "@\K[^:]+" || echo "")
    DB_PORT=$(echo "$DATABASE_URL" | grep -oP ":[0-9]+(?=/)" | tr -d ":" || echo "")
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        echo \"⏳ En attente de PostgreSQL à $DB_HOST:$DB_PORT...\"
        for i in {1..30}; do
            if nc -z $DB_HOST $DB_PORT 2>/dev/null; then
                echo \"✅ PostgreSQL prêt!\"
                break
            fi
            sleep 1
        done
    fi
fi

# =========================
# Migrations Django
# =========================
echo \"🔄 Application des migrations...\"
python manage.py migrate --noinput

# =========================
# Collectstatic
# =========================
echo \"📁 Collecte des fichiers statiques...\"
python manage.py collectstatic --noinput

# =========================
# Permissions
# =========================
chmod -R 755 /app/staticfiles /app/media

# =========================
# Lancement Daphne
# =========================
echo \"🚀 Démarrage de Daphne sur $HOST:$PORT...\"
exec daphne -b $HOST -p $PORT mykarfour_app.asgi:application
' > /start.sh

RUN chmod +x /start.sh

# =========================
# Exposer le port
# =========================
EXPOSE 8000

ENTRYPOINT ["/start.sh"]
