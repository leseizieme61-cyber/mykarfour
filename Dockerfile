# =========================
# Image de Base (Slim est plus léger et rapide)
# =========================
FROM python:3.12-slim

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# On évite de travailler à la racine / pour plus de sécurité
WORKDIR /app

# =========================
# Dépendances système
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    git \
    libgomp1 \
    libopenblas-dev \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip
# =========================
RUN python -m venv /opt/venv
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# =========================
# Installation de NumPy et Torch (Versions compatibles 3.12)
# =========================
# 1. NumPy 1.26.0 est la version minimale stable pour Python 3.12
# 2. On retire --no-binary pour utiliser les fichiers pré-compilés (beaucoup plus rapide)
RUN pip install --no-cache-dir "numpy>=1.26.0"

# 3. Torch 2.2.0+ est requis pour un support natif de Python 3.12
RUN pip install --no-cache-dir torch==2.2.1 --index-url https://download.pytorch.org/whl/cpu

# =========================
# Installation du reste des dépendances
# =========================
COPY requirements.txt .
# CONSEIL : Retirez 'numpy' et 'torch' de votre requirements.txt pour éviter les conflits
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# Copier le projet
# =========================
COPY . .

# Permissions et dossiers
RUN mkdir -p staticfiles media && chmod -R 755 staticfiles media

# Migration et collectstatic
# Note : 'python manage.py migrate' devrait plutôt être dans start.sh
RUN python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Script d'entrée
COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]

# Commande par défaut
CMD ["gunicorn", "mykarfour_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
