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

# Commande par défaut pour lancer Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
