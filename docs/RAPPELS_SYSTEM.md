# Système de Rappels Automatiques - MyKarfour

## 📋 Overview

Le système de rappels automatiques MyKarfour permet d'envoyer des notifications email aux élèves pour les encourager à se connecter et réviser régulièrement.

## 🎯 Fonctionnalités

### 1. Types de Rappels

#### **Rappels de Sessions**
- **Quand**: Jour même et veille des sessions programmées
- **Heure**: 8h00 (matin) et 18h30 (soir)
- **Destinataires**: Élèves avec sessions programmées
- **Contenu**: Matière, heure, objectif, lien direct vers le chat

#### **Rappels d'Inactivité**
- **Quand**: Pour les élèves inactifs depuis 3+ jours
- **Heure**: 10h00 tous les jours
- **Destinataires**: Élèves avec abonnement actif mais inactifs
- **Contenu**: Encouragement à se reconnecter, statistiques d'inactivité

#### **Rappels Hebdomadaires**
- **Quand**: Tous les dimanches soir
- **Heure**: 20h00
- **Destinataires**: Tous les élèves actifs
- **Contenu**: Bilan de la semaine, objectifs pour la semaine suivante

#### **Rappels Manuels**
- **Quand**: À la demande des parents
- **Destinataires**: Élève spécifique
- **Contenu**: Message personnalisé du parent

## 🏗️ Architecture

### **Modèles de Données**

```python
# RappelRevision - Stocke tous les rappels envoyés
class RappelRevision(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    session_programmee = models.ForeignKey(SessionRevisionProgrammee, null=True)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_rappel = models.DateTimeField()
    envoye = models.BooleanField(default=False)
```

### **Commandes Management**

#### **`envoyer_rappels`**
- **Fichier**: `repetiteur_ia/management/commands/envoyer_rappels.py`
- **Action**: Envoie tous les types de rappels
- **Usage**: `python manage.py envoyer_rappels`

#### **`programmer_sessions`**
- **Fichier**: `repetiteur_ia/management/commands/programmer_sessions.py`
- **Action**: Crée automatiquement les sessions de révision
- **Usage**: `python manage.py programmer_sessions`

### **Tâches Celery**

```python
# Tâches périodiques configurées dans celery_schedule.py
beat_schedule = {
    'envoyer-rappels-quotidiens': {
        'task': 'repetiteur_ia.envoyer_rappels_automatiques',
        'schedule': crontab(hour=8, minute=0),
    },
    'verifier-inactivite': {
        'task': 'repetiteur_ia.verifier_inactivite',
        'schedule': crontab(hour=10, minute=0),
    },
}
```

## 🚀 Installation

### **1. Configuration de Base**

Les fichiers sont déjà créés, il suffit de configurer la planification:

#### **Option A: Cron (Linux/Mac)**

```bash
# Rendre le script exécutable
chmod +x scripts/setup_rappels_cron.sh

# Exécuter le script d'installation
./scripts/setup_rappels_cron.sh

# Ou manuellement:
crontab scripts/setup_rappels_cron.sh
```

#### **Option B: Planificateur de Tâches (Windows)**

```cmd
# Exécuter le script d'installation
scripts\setup_rappels_windows.bat

# Ou manuellement via le Panneau de configuration
# Outils d'administration > Planificateur de tâches
```

#### **Option C: Celery Beat (Production)**

```python
# Dans settings.py
CELERY_BEAT_SCHEDULE = {
    'envoyer-rappels-quotidiens': {
        'task': 'repetiteur_ia.envoyer_rappels_automatiques',
        'schedule': crontab(hour=8, minute=0),
    },
}

# Démarrer Celery Beat
celery -A mykarfour beat -l info
```

### **2. Configuration Email**

Assurez-vous que les settings email sont configurés:

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'votre-email@gmail.com'
EMAIL_HOST_PASSWORD = 'votre-mot-de-passe'
DEFAULT_FROM_EMAIL = 'MyKarfour <noreply@mykarfour.com>'
SITE_URL = 'https://votre-domaine.com'
```

## 📱 Interface Utilisateur

### **Pour les Élèves**

- **URL**: `/repetiteur/rappels/`
- **Fonctionnalités**: Voir l'historique de ses rappels
- **Permissions**: Uniquement ses propres rappels

### **Pour les Parents**

- **URL**: `/repetiteur/rappels/`
- **Fonctionnalités**: 
  - Voir les rappels de tous ses enfants
  - Envoyer des rappels manuels
  - Détails par enfant: `/repetiteur/rappels/enfant/{id}/`
- **Permissions**: Rappels de ses enfants uniquement

### **Pour les Admins**

- **URL**: `/repetiteur/rappels/test/`
- **Fonctionnalités**: Tester l'envoi des rappels
- **Permissions**: Super-utilisateur uniquement

## 🧪 Tests

### **Test Manuel**

```bash
# Tester l'envoi des rappels
python manage.py envoyer_rappels

# Tester la programmation des sessions
python manage.py programmer_sessions

# Tester via l'interface (admin uniquement)
curl -X POST http://localhost:8000/repetiteur/rappels/test/
```

### **Test Email**

```python
# Dans le shell Django
python manage.py shell

from django.core.mail import send_mail
from django.conf import settings

send_mail(
    'Test Email MyKarfour',
    'Ceci est un test du système de rappels.',
    settings.DEFAULT_FROM_EMAIL,
    ['votre-email@test.com'],
    fail_silently=False,
)
```

## 📊 Monitoring

### **Logs**

- **Linux/Mac**: `/var/log/mykarfour_rappels.log`
- **Windows**: `logs/rappels.log`
- **Docker**: `docker-compose logs web`

### **Statistiques**

Dans l'interface admin ou via API:

```python
# Statistiques des rappels
from repetiteur_ia.models import RappelRevision
from django.utils import timezone
from datetime import timedelta

# Rappels envoyés aujourd'hui
aujourdhui = timezone.now().date()
rappels_aujourdhui = RappelRevision.objects.filter(
    date_rappel__date=aujourdhui,
    envoye=True
).count()

# Rappels de la semaine
semaine_derniere = timezone.now() - timedelta(days=7)
rappels_semaine = RappelRevision.objects.filter(
    date_rappel__gte=semaine_derniere,
    envoye=True
).count()
```

## 🔧 Personnalisation

### **Modifier les Horaires**

#### **Cron**
```bash
# Éditer le cron
crontab -e

# Modifier les heures:
0 8 * * *    # 8h00 tous les jours
0 20 * * 0   # 20h00 tous les dimanches
```

#### **Celery**
```python
# celery_schedule.py
beat_schedule = {
    'envoyer-rappels-quotidiens': {
        'task': 'repetiteur_ia.envoyer_rappels_automatiques',
        'schedule': crontab(hour=9, minute=30),  # 9h30
    },
}
```

### **Personnaliser les Messages**

Modifier les templates dans `envoyer_rappels.py`:

```python
# Message personnalisé pour l'inactivité
message = f"""
Salut {eleve.user.first_name} ! 🌟

[VOTRE MESSAGE PERSONNALISÉ ICI]

L'équipe MyKarfour 🎓
""".strip()
```

### **Ajouter de Nouveaux Types de Rappels**

1. Créer une nouvelle méthode dans `envoyer_rappels.py`
2. Ajouter la logique d'envoi email
3. Créer le `RappelRevision` en base
4. Ajouter la tâche périodique dans `celery_schedule.py`

## 🚨 Dépannage

### **Problèmes Communs**

#### **Emails non envoyés**
```bash
# Vérifier la configuration email
python manage.py shell
from django.core.mail import send_mail
send_mail('Test', 'Test', 'from@example.com', ['to@example.com'])

# Vérifier les logs
tail -f /var/log/mykarfour_rappels.log
```

#### **Tâches non exécutées**
```bash
# Vérifier les cron actifs
crontab -l

# Vérifier les logs système
grep CRON /var/log/syslog
```

#### **Permissions**
```bash
# Vérifier les permissions des fichiers
ls -la scripts/
chmod +x scripts/*.sh
```

### **Debug Mode**

Activer le debug dans les commandes:

```python
# Dans envoyer_rappels.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Améliorations Futures

1. **SMS Notifications**: Intégration Twilio pour les SMS
2. **Push Notifications**: Notifications navigateur/mobile
3. **Intelligence Artificielle**: Personnalisation des messages
4. **Dashboard Analytics**: Statistiques détaillées
5. **Multilingue**: Support de plusieurs langues

## 📞 Support

Pour toute question ou problème:
- **Documentation**: Ce fichier
- **Logs**: Voir section Monitoring
- **Code**: Voir fichiers dans `repetiteur_ia/management/commands/`
- **Tests**: Utiliser les commandes de test manuelles
