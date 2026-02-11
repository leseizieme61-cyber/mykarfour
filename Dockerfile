# Utiliser une image Python légère
FROM python:3.12-slim

# Ne pas bufferiser les logs
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
RUN apt-get update && \
    apt-get install -y gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copier le fichier de dépendances Python
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --require-hashes -r requirements.txt || pip install --no-cache-dir -r requirements.txt

# Copier le reste de l'application
COPY . .

# Exposer le port 8000
EXPOSE 8000

RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Démarrage de l’application..."\n\
\n\
# Vérifier Python et les dépendances\n\
python --version\n\
python -c "import numpy; print(f\"✅ NumPy {numpy.__version__}\")"\n\
python -c "import django; print(f\"✅ Django {django.__version__}\")"\n\
\n\
# S’assurer que staticfiles existe\n\
if [ ! -d "staticfiles" ]; then\n\
    echo "📁 Création de staticfiles..."\n\
    mkdir -p staticfiles\n\
fi\n\
chmod -R 755 staticfiles\n\
\n\
# Attendre PostgreSQL si nécessaire\n\
if [ -n "$DATABASE_URL" ]; then\n\
    DB_HOST=$(echo "$DATABASE_URL" | grep -oP "@\K[^:]+" || echo "")\n\
    DB_PORT=$(echo "$DATABASE_URL" | grep -oP ":\K[0-9]+" || echo "")\n\
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then\n\
        echo "⏳ En attente de $DB_HOST:$DB_PORT..."\n\
        for i in {1..30}; do\n\
            if nc -z $DB_HOST $DB_PORT 2>/dev/null; then\n\
                echo "✅ PostgreSQL prêt!"\n\
                break\n\
            fi\n\
            sleep 1\n\
        done\n\
    fi\n\
fi\n\
\n\
# Migrations\n\
echo "🔄 Application des migrations..."\n\
python manage.py migrate --noinput\n\
\n\
# Collectstatic (au cas où)\n\
echo "📁 Collecte des fichiers statiques..."\n\
python manage.py collectstatic --noinput\n\
\n\
# Démarrer Gunicorn\n\
echo "🚀 Démarrage de Gunicorn sur 0.0.0.0:8000..."\n\
exec gunicorn mykarfour_app.wsgi:application \\\n\
    --bind 0.0.0.0:8000 \\\n\
    --workers 3 \\\n\
    --worker-class sync \\\n\
    --access-logfile - \\\n\
    --error-logfile - \\\n\
    --timeout 120\n\
' > /start.sh

RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
