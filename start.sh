#!/bin/bash

echo "🔄 Migrations..."
python manage.py migrate --noinput

echo "📦 Collect static..."
python manage.py collectstatic --noinput

echo "🚀 Lancement serveur ASGI..."
daphne -b 0.0.0.0 -p $PORT mykarfour_app.asgi:application
