# =========================
# Base Image
# =========================
FROM python:3.12-slim

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# =========================
# Travail à la racine (car votre projet est à /)
# =========================
WORKDIR /

# =========================
# Dépendances système COMPLÈTES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    wget \
    netcat-openbsd \
    # DÉPENDANCES CRITIQUES pour numpy
    libstdc++6 \
    libgomp1 \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    # Autres
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip
# =========================
RUN python -m venv /opt/venv
RUN pip install --upgrade pip setuptools wheel

# =========================
# Installez d'abord numpy pour éviter les conflits
# =========================
RUN pip install --no-cache-dir --no-binary :all: numpy==1.24.3

# =========================
# Installez torch CPU
# =========================
RUN pip install --no-cache-dir torch==2.0.1 --index-url https://download.pytorch.org/whl/cpu

# =========================
# Copier requirements et installer le reste
# =========================
COPY requirements.txt .
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
# Commande Daphne
# =========================
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "mykarfour_app.asgi:application"]
