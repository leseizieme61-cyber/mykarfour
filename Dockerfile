# =========================
# Image de base : Python 3.12.3 spécifique
# =========================
FROM python:3.12.3-slim-bullseye

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# =========================
# Travail à la racine (correspond à BASE_DIR = /)
# =========================
WORKDIR /

# =========================
# Dépendances système (minimales)
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    libgomp1 \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip / setuptools
# =========================
RUN python -m venv /opt/venv
RUN /opt/venv/bin/pip install --upgrade pip==24.0 setuptools==69.5.0 wheel==0.43.0

# =========================
# Installer NumPy 1.24.3 (compatible Python 3.12)
# =========================
RUN /opt/venv/bin/pip install --no-cache-dir numpy==1.24.3

# =========================
# Installer Torch CPU
# =========================
RUN /opt/venv/bin/pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# =========================
# Copier requirements et installer le reste
# =========================
COPY requirements.txt .
RUN grep -v "^numpy==" requirements.txt > /tmp/requirements_no_numpy.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements_no_numpy.txt

# =========================
# Copier le code
# =========================
COPY . .

# =========================
# Créer les dossiers staticfiles et media
# =========================
RUN mkdir -p staticfiles media
RUN chmod -R 755 staticfiles media

# =========================
# Collectstatic avec des valeurs par défaut pour le build
# =========================
RUN /opt/venv/bin/python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_app.settings')
os.environ['SECRET_KEY'] = 'dummy-key-for-build'
os.environ['ALLOWED_HOSTS'] = '*'
os.environ['DEBUG'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
import django
django.setup()
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear'])
"

EXPOSE 8000

# =========================
# Script d'entrée
# =========================
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
