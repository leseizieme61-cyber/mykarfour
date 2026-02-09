=========================
Dockerfile corrigé pour Django avec Gunicorn
=========================

FROM python:3.12-slim
=========================
Environnements Python
=========================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
=========================
Travail dans /app
=========================

WORKDIR /app
=========================
Dépendances système
=========================

RUN apt-get update && apt-get install -y
build-essential
libpq-dev
curl
git
netcat-openbsd
&& rm -rf /var/lib/apt/lists/*
=========================
Créer venv et mettre à jour pip
=========================

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel
=========================
Copier requirements et installer
=========================

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
=========================
Copier le projet
=========================

COPY . .
=========================
Permissions et staticfiles
=========================

RUN mkdir -p /app/staticfiles /app/media
RUN chmod -R 755 /app/staticfiles /app/media
=========================
Exposer le port
=========================

EXPOSE 8000
=========================
Script d'entrée
=========================

COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]
=========================
Commande par défaut
=========================

CMD ["gunicorn", "mykarfour_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
