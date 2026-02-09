# =========================
# Base Image
# =========================
FROM python:3.12-slim

# =========================
# Environnements Python
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# =========================
# Travail dans /app
# =========================
WORKDIR /app

# =========================
# Dépendances système
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Créer venv et mettre à jour pip
# =========================
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel

# =========================
# Copier requirements et installer
# =========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# Copier le projet
# =========================
COPY . .

# =========================
# Créer dossier staticfiles et collect static
# =========================
RUN mkdir -p /app/staticfiles
RUN python manage.py migrate --noinput
RUN python manage.py collectstatic --noinput

# =========================
# Exposer le port (Dockploy utilise $PORT)
# =========================
ENV PORT 8000
EXPOSE ${PORT}

# =========================
# Commande de démarrage gunicorn
# =========================
CMD ["gunicorn", "mykarfour_app.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "3"]
