from celery import Celery
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mykarfour_ia.settings')

app = Celery('mykarfour_ia')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Dans gestionnaire/tasks.py
from celery import shared_task
from django.utils import timezone
from repetiteur_ia.utils import programmer_rappels

@shared_task
def task_programmer_rappels():
    programmer_rappels()