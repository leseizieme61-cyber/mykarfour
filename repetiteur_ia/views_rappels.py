# repetiteur_ia/views_rappels.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command
from utilisateurs.models import Eleve, Parent
from repetiteur_ia.models import RappelRevision, SessionRevisionProgrammee
from django.contrib.auth.decorators import user_passes_test

def is_eleve(user):
    return hasattr(user, 'eleve')

def is_parent(user):
    return hasattr(user, 'parent')

class RappelsListView(LoginRequiredMixin, ListView):
    """Liste des rappels pour l'élève connecté"""
    model = RappelRevision
    template_name = 'repetiteur_ia/rappels_list.html'
    context_object_name = 'rappels'
    paginate_by = 20
    
    def get_queryset(self):
        if hasattr(self.request.user, 'eleve'):
            return RappelRevision.objects.filter(
                eleve=self.request.user.eleve
            ).select_related('session_programmee').order_by('-date_rappel')
        elif hasattr(self.request.user, 'parent'):
            # Parent voit les rappels de ses enfants
            parent = self.request.user.parent
            enfants_ids = parent.eleves.values_list('id', flat=True)
            return RappelRevision.objects.filter(
                eleve_id__in=enfants_ids
            ).select_related('eleve__user', 'session_programmee').order_by('-date_rappel')
        return RappelRevision.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques
        queryset = self.get_queryset()
        context['total_rappels'] = queryset.count()
        context['rappels_envoyes'] = queryset.filter(envoye=True).count()
        context['rappels_recent'] = queryset.filter(
            date_rappel__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Rappels à venir
        context['rappels_venir'] = queryset.filter(
            date_rappel__gt=timezone.now(),
            envoye=False
        ).count()
        
        # Contexte spécifique selon le type d'utilisateur
        if hasattr(self.request.user, 'parent'):
            context['est_parent'] = True
            context['enfants'] = self.request.user.parent.eleves.all()
        
        return context

@login_required
def envoyer_rappel_manuel(request):
    """Envoyer un rappel manuel (pour les parents ou admin)"""
    if request.method == 'POST':
        eleve_id = request.POST.get('eleve_id')
        message = request.POST.get('message', '')
        
        if not eleve_id:
            return JsonResponse({'status': 'error', 'message': 'Élève non spécifié'})
        
        try:
            eleve = Eleve.objects.get(id=eleve_id)
            
            # Créer et envoyer le rappel
            from django.core.mail import send_mail
            from django.conf import settings
            
            if message:
                sujet = f"📚 Rappel personnalisé - MyKarfour"
                message_complet = f"""
Bonjour {eleve.user.first_name} 👋,

{message}

🔗 **Accédez à MyKarfour :**
{getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')}/

Cordialement,
L'équipe MyKarfour 🎓
                """.strip()
                
                send_mail(
                    sujet,
                    message_complet,
                    settings.DEFAULT_FROM_EMAIL,
                    [eleve.user.email],
                    fail_silently=False,
                )
                
                # Créer le rappel en base
                RappelRevision.objects.create(
                    eleve=eleve,
                    titre="Rappel manuel",
                    message=message_complet,
                    date_rappel=timezone.now(),
                    envoye=True
                )
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f'Rappel envoyé à {eleve.user.username}'
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Message vide'})
                
        except Eleve.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Élève introuvable'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

@login_required
@user_passes_test(is_parent)
def rappels_enfant_detail(request, eleve_id):
    """Détail des rappels pour un enfant spécifique (vue parent)"""
    parent = request.user.parent
    enfant = get_object_or_404(Eleve, id=eleve_id, parent=parent)
    
    rappels = RappelRevision.objects.filter(
        eleve=enfant
    ).select_related('session_programmee').order_by('-date_rappel')
    
    context = {
        'enfant': enfant,
        'rappels': rappels,
        'total_rappels': rappels.count(),
        'rappels_envoyes': rappels.filter(envoye=True).count(),
    }
    
    return render(request, 'repetiteur_ia/rappels_enfant_detail.html', context)

@login_required
def tester_envoi_rappels(request):
    """Tester l'envoi des rappels (pour développement/admin)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Accès non autorisé'})
    
    try:
        call_command('envoyer_rappels')
        return JsonResponse({
            'status': 'success', 
            'message': 'Test d\'envoi des rappels lancé avec succès'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
