#!/bin/bash

# Attendre que la base de données soit prête (optionnel)
# while ! nc -z $DB_HOST $DB_PORT; do
#   sleep 0.1
# done

# Appliquer les migrations
python manage.py migrate --noinput

# Collecter les fichiers statiques
python manage.py collectstatic --noinput

# Créer le superutilisateur si nécessaire (optionnel)
# python manage.py createsuperuser --noinput || true

# Démarrer Daphne ou Gunicorn
if [ "$USE_ASGI" = "true" ]; then
    echo "Starting Daphne (ASGI)..."
    daphne -b 0.0.0.0 -p 8000 mykarfour_app.asgi:application
else
    echo "Starting Gunicorn (WSGI)..."
    gunicorn mykarfour_app.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --worker-class sync
fi
