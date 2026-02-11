FROM python:3.12-slim As prod

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Dépendances système
RUN apt-get update && \
    apt-get install -y gcc libpq-dev curl netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY . .

# Copier le script de démarrage
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Exposer le port
EXPOSE 8000

ENTRYPOINT ["/start.sh"]
