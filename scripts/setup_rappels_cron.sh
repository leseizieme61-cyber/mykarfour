#!/bin/bash

# Script de configuration pour les rappels automatiques MyKarfour
# Ce script configure le cron job pour l'envoi automatique des rappels

echo "🔧 Configuration des rappels automatiques MyKarfour..."

# Vérifier si nous sommes dans le bon répertoire
if [ ! -f "manage.py" ]; then
    echo "❌ Erreur: Ce script doit être exécuté depuis le répertoire racine de Django (où se trouve manage.py)"
    exit 1
fi

# Créer le fichier de configuration cron
CRON_FILE="/tmp/mykarfour_rappels_cron"

# Créer le cron job pour les rappels quotidiens
cat > $CRON_FILE << EOF
# Rappels automatiques MyKarfour
# Envoyé tous les jours à 8h00
0 8 * * * cd $(pwd) && /usr/bin/python3 manage.py envoyer_rappels >> /var/log/mykarfour_rappels.log 2>&1

# Programmation des sessions tous les dimanches à 20h00
0 20 * * 0 cd $(pwd) && /usr/bin/python3 manage.py programmer_sessions >> /var/log/mykarfour_sessions.log 2>&1

# Nettoyage des anciens rappels (tous les lundis à 2h00)
0 2 * * 1 cd $(pwd) && /usr/bin/python3 manage.py shell << 'PYTHON_EOF'
from repetiteur_ia.models import RappelRevision
from django.utils import timezone
from datetime import timedelta

# Supprimer les rappels de plus de 30 jours
seuil = timezone.now() - timedelta(days=30)
anciens_rappels = RappelRevision.objects.filter(date_creation__lt=seuil)
count = anciens_rappels.count()
anciens_rappels.delete()
print(f"Nettoyé {count} anciens rappels")
PYTHON_EOF
EOF

echo "📝 Fichier cron créé: $CRON_FILE"
echo "Contenu du cron job:"
cat $CRON_FILE

# Instructions pour l'installation
echo ""
echo "🚀 Pour installer le cron job, exécutez:"
echo "   crontab $CRON_FILE"
echo ""
echo "📋 Pour voir les cron jobs actifs:"
echo "   crontab -l"
echo ""
echo "🗑️  Pour supprimer tous les cron jobs:"
echo "   crontab -r"
echo ""
echo "📝 Les logs seront écrits dans:"
echo "   /var/log/mykarfour_rappels.log"
echo "   /var/log/mykarfour_sessions.log"
echo ""
echo "⚠️  Assurez-vous que:"
echo "   - Python 3 est installé: /usr/bin/python3"
echo "   - L'utilisateur a les permissions d'écriture dans /var/log/"
echo "   - Le répertoire du projet est accessible en lecture/écriture"

# Option: Installation automatique si demandé
read -p "Voulez-vous installer le cron job maintenant? (o/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "📦 Installation du cron job..."
    crontab $CRON_FILE
    if [ $? -eq 0 ]; then
        echo "✅ Cron job installé avec succès!"
        echo "📋 Cron jobs actifs:"
        crontab -l
    else
        echo "❌ Erreur lors de l'installation du cron job"
        exit 1
    fi
fi

# Nettoyer le fichier temporaire
rm -f $CRON_FILE

echo ""
echo "🎉 Configuration terminée!"
echo "📚 Pour tester manuellement:"
echo "   python manage.py envoyer_rappels"
echo ""
echo "🔧 Pour modifier les horaires, éditez le cron avec: crontab -e"
