from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Slot, Activity, Question, Answer
from .tasks import trigger_slot_actions
from celery import shared_task
import requests

class Slot(models.Model):
    title = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('available', 'Disponible'),
        ('running', 'En cours'),
        ('finished', 'Terminé'),
    ])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

@shared_task
def trigger_slot_actions(slot_id):
    slot = Slot.objects.get(pk=slot_id)
    slot.status = 'running'
    slot.save()

    # création d'activité (similarity search)
    query = slot.title or "révision"
    results = search_similar(query, top_k=6)
    payload = {'chunks': results, 'instructions': 'Propose 5 questions de compréhension à partir de ces extraits.'}
    Activity.objects.create(slot=slot, kind='quiz', payload=payload)

    # notification email avec lien vers le chat
    try:
        if slot.user.email:
            chat_link = f"{getattr(settings,'SITE_URL','http://localhost:8000').rstrip('/')}/repetiteur/chat/{slot.id}/"
            send_mail(
                f"Votre créneau « {slot.title} » commence",
                f"Votre créneau commence maintenant. Accédez au chat : {chat_link}",
                settings.DEFAULT_FROM_EMAIL,
                [slot.user.email],
                fail_silently=True,
            )
    except Exception:
        pass

    # Envoi WebSocket via channel layer au groupe utilisateur
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{slot.user.id}",
            {
                "type": "slot.running",   # appelle slot_running dans le consumer
                "slot_id": slot.id,
                "title": slot.title,
            },
        )
    except Exception:
        # ignorer si channel layer indisponible
        pass

    return True

@shared_task
def proposer_quiz_par_ia(payload):
    """Exemple de tâche : envoie un payload JSON à l'endpoint interne de cours pour création."""
    # endpoint interne (peut utiliser reverse en contexte Django, ici URL relative)
    url = getattr(settings, "MYKARFOUR_INTERNAL_URL", None) or "http://localhost:8000/cours/quiz/create-from-ai/"
    headers = {"Content-Type": "application/json"}
    token = getattr(settings, "AI_SERVICE_TOKEN", None)
    if token:
        headers["X-Service-Token"] = token
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    return {"status": resp.status_code, "text": resp.text}