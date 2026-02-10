# =========================
# Base Image
# =========================
FROM python:3.12

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# =========================
# Travail dans /
# =========================
WORKDIR /

# =========================
# Dépendances système pour numpy, torch, PIL, OpenCV, etc.
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    wget \
    git \
    netcat-openbsd \
    libstdc++6 \
    libgomp1 \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip AVEC setuptools 69.5.0
# IMPORTANT: setuptools 69.5.0 est compatible avec Python 3.12
# =========================
RUN python -m venv /opt/venv
RUN /opt/venv/bin/pip install --upgrade pip==24.0 wheel==0.43.0 setuptools==69.5.0

# =========================
# Copier requirements et installer les dépendances
# =========================
COPY requirements.txt .

# =========================
# Installation EN ORDRE :
# 1. setuptools 69.5.0 (déjà fait)
# 2. numpy 1.24.3 (version compatible avec Python 3.12)
# 3. torch CPU
# 4. Le reste
# =========================

# Numpy avec version spécifique pour éviter les erreurs
RUN /opt/venv/bin/pip install --no-cache-dir numpy==1.24.3

# Installer torch CPU (version compatible)
RUN /opt/venv/bin/pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# Installer le reste des dépendances
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# =========================
# Copier le projet
# =========================
COPY . .

# =========================
# Permissions et staticfiles
# =========================
RUN mkdir -p staticfiles media
RUN chmod -R 755 staticfiles media

# =========================
# Migration et collectstatic
# =========================
RUN /opt/venv/bin/python manage.py collectstatic --noinput --clear

# =========================
# Exposer le port
# =========================
EXPOSE 8000

# =========================
# Script d'entrée (start.sh) CORRIGÉ
# =========================
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "🚀 Démarrage de l’application..."\n\
\n\
# Activer le venv (au cas où)\n\
export PATH="/opt/venv/bin:$PATH"\n\
\n\
# Vérifier Python et NumPy\n\
echo "🔍 Vérification des dépendances..."\n\
python --version\n\
python -c "import numpy; print(f\"✅ NumPy {numpy.__version__}\")"\n\
\n\
# Attendre PostgreSQL si nécessaire\n\
if [ -n "$DATABASE_URL" ]; then\n\
    echo "⏳ Vérification PostgreSQL..."\n\
    DB_HOST=$(echo "$DATABASE_URL" | grep -oP "@\K[^:]+")\n\
    DB_PORT=$(echo "$DATABASE_URL" | grep -oP ":\K[0-9]+")\n\
    \n\
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then\n\
        echo "⏳ En attente de $DB_HOST:$DB_PORT..."\n\
        while ! nc -z "$DB_HOST" "$DB_PORT"; do\n\
            sleep 1\n\
        done\n\
        echo "✅ PostgreSQL prêt!"\n\
    fi\n\
fi\n\
\n\
# Migrations\n\
echo "🔄 Migrations..."\n\
python manage.py migrate --noinput\n\
\n\
# Fichiers statiques\n\
echo "📁 Fichiers statiques..."\n\
python manage.py collectstatic --noinput --clear\n\
\n\
# Démarrer Gunicorn\n\
echo "🚀 Démarrage Gunicorn sur 0.0.0.0:8000..."\n\
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
