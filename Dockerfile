# =========================
# Base Image - Utilisez python:3.12 complet au lieu de slim
# =========================
FROM python:3.12

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# =========================
# Travail dans / (car votre projet est à la racine)
# =========================
WORKDIR /

# =========================
# Dépendances système COMPLÈTES pour numpy, torch, transformers, etc.
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    wget \
    git \
    netcat-openbsd \
    # DÉPENDANCES CRITIQUES pour numpy
    libstdc++6 \
    libgomp1 \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    # Dépendances pour torch et autres bibliothèques scientifiques
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    # Autres
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip
# =========================
RUN python -m venv /opt/venv
RUN pip install --upgrade pip setuptools wheel

# =========================
# Copier requirements et installer AVEC optimisation
# =========================
COPY requirements.txt .

# Installez d'abord numpy avec compilation pour éviter les problèmes
RUN pip install --no-cache-dir --no-binary :all: numpy==1.24.3

# Puis installez torch avec la version CPU pour éviter les problèmes GPU
RUN pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# Enfin, installez le reste des dépendances
RUN pip install --no-cache-dir -r requirements.txt

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
RUN python manage.py collectstatic --noinput --clear

# =========================
# Exposer le port
# =========================
EXPOSE 8000

# =========================
# Script d'entrée amélioré
# =========================
COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]

# =========================
# Commande par défaut (fallback)
# =========================
CMD ["gunicorn", "mykarfour_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
