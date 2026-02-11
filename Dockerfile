# =========================
# Base PROD (OBLIGATOIRE POUR DOKPLOY)
# =========================
FROM python:3.12-slim AS prod

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# =========================
# Dépendances système
# =========================
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Dépendances Python
# =========================
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# =========================
# Code application
# =========================
COPY . .

# =========================
# Static / Media
# =========================
RUN mkdir -p staticfiles media \
    && chmod -R 755 staticfiles media

# =========================
# Collectstatic (safe)
# =========================
RUN python manage.py collectstatic --noinput || true

# =========================
# Port
# =========================
EXPOSE 8000

# =========================
# Lancement avec DAPHNE
# =========================
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "mykarfour_app.asgi:application"]
