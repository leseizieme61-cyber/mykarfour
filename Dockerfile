FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc libpq-dev netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Script de démarrage
RUN echo '#!/bin/sh\n\
set -e\n\
\n\
echo "🚀 Démarrage Django avec Daphne"\n\
\n\
python --version\n\
\n\
# Créer staticfiles si absent\n\
mkdir -p staticfiles\n\
\n\
# Attente PostgreSQL\n\
if [ -n "$DATABASE_URL" ]; then\n\
  DB_HOST=$(echo "$DATABASE_URL" | sed -n "s|.*@\\([^:/]*\\).*|\\1|p")\n\
  DB_PORT=$(echo "$DATABASE_URL" | sed -n "s|.*:\\([0-9]*\\)/.*|\\1|p")\n\
  echo "⏳ Attente DB $DB_HOST:$DB_PORT"\n\
  for i in $(seq 1 30); do\n\
    nc -z $DB_HOST $DB_PORT && break\n\
    sleep 1\n\
  done\n\
fi\n\
\n\
echo "🔄 Migrations"\n\
python manage.py migrate --noinput\n\
\n\
echo "📦 Collectstatic"\n\
python manage.py collectstatic --noinput\n\
\n\
echo "🚀 Lancement Daphne"\n\
exec daphne -b 0.0.0.0 -p 8000 mykarfour_app.asgi:application\n\
' > /start.sh

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
