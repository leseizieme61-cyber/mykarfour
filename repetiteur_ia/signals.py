from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from django.conf import settings

# Import des fonctions FAISS
from .embeddings import get_vector_store, create_vector_store_from_texts
from .models import MessageIA, EmbeddingIA, SessionIA

# Charger le modèle une seule fois (au démarrage du serveur)
model = SentenceTransformer("all-MiniLM-L6-v2")

@receiver(post_save, sender=MessageIA)
def creer_embedding_et_mettre_a_jour_vectorstore(sender, instance, created, **kwargs):
    """
    Crée un embedding local ET met à jour le vectorstore FAISS
    à chaque nouveau message entre l'élève et le répétiteur
    """
    if created:
        try:
            # 1. Créer l'embedding local dans la base de données
            vector = model.encode(instance.contenu).tolist()
            
            EmbeddingIA.objects.create(
                message=instance,
                vector=vector
            )
            print(f"✅ Embedding local créé pour le message {instance.id}")

            # 2. Mettre à jour le vectorstore FAISS avec le nouveau message
            if instance.role == 'élève':  # Seulement les questions des élèves
                mettre_a_jour_vectorstore_avec_message_eleve(instance)
            else:  # Les réponses de l'IA aussi peuvent être utiles
                mettre_a_jour_vectorstore_avec_message_ia(instance)

        except Exception as e:
            print(f"❌ Erreur embedding/vectorstore : {e}")

def mettre_a_jour_vectorstore_avec_message_eleve(message_eleve):
    """Met à jour le vectorstore FAISS avec une question d'élève"""
    try:
        vectorstore = get_vector_store()
        
        # Formater le contenu pour le vectorstore
        eleve_nom = message_eleve.session.eleve.user.get_full_name() or message_eleve.session.eleve.user.username
        contenu_formate = f"""
        QUESTION ÉLÈVE: {message_eleve.contenu}
        Élève: {eleve_nom}
        Niveau: {message_eleve.session.eleve.get_niveau_display()}
        Classe: {message_eleve.session.eleve.get_classe_display()}
        Session: {message_eleve.session.titre}
        Date: {message_eleve.date_envoi}
        """
        
        # Ajouter au vectorstore existant
        vectorstore.add_texts([contenu_formate.strip()])
        vectorstore.save_local(settings.VECTOR_STORE_PATH)
        
        print(f"✅ Vectorstore mis à jour avec la question de {eleve_nom}")
        
    except Exception as e:
        print(f"❌ Erreur mise à jour vectorstore avec question élève: {e}")

def mettre_a_jour_vectorstore_avec_message_ia(message_ia):
    """Met à jour le vectorstore FAISS avec une réponse de l'IA"""
    try:
        vectorstore = get_vector_store()
        
        # Formater le contenu pour le vectorstore
        contenu_formate = f"""
        RÉPONSE IA: {message_ia.contenu}
        Session: {message_ia.session.titre}
        Date: {message_ia.date_envoi}
        """
        
        # Ajouter au vectorstore existant
        vectorstore.add_texts([contenu_formate.strip()])
        vectorstore.save_local(settings.VECTOR_STORE_PATH)
        
        print(f"✅ Vectorstore mis à jour avec une réponse IA")
        
    except Exception as e:
        print(f"❌ Erreur mise à jour vectorstore avec réponse IA: {e}")

@receiver(post_save, sender=SessionIA)
def initialiser_vectorstore_nouvelle_session(sender, instance, created, **kwargs):
    """Ajoute une entrée pour une nouvelle session IA"""
    if created:
        try:
            vectorstore = get_vector_store()
            
            contenu_formate = f"""
            NOUVELLE SESSION: {instance.titre}
            Élève: {instance.eleve.user.get_full_name() or instance.eleve.user.username}
            Niveau: {instance.eleve.get_niveau_display()}
            Classe: {instance.eleve.get_classe_display()}
            Date: {instance.date_creation}
            """
            
            vectorstore.add_texts([contenu_formate.strip()])
            vectorstore.save_local(settings.VECTOR_STORE_PATH)
            
            print(f"✅ Vectorstore mis à jour avec la nouvelle session: {instance.titre}")
            
        except Exception as e:
            print(f"❌ Erreur ajout session au vectorstore: {e}")

def reconstruire_vectorstore_complet():
    """Reconstruit le vectorstore complet avec tous les messages historiques"""
    try:
        texts = []
        
        # Récupérer toutes les sessions
        sessions = SessionIA.objects.all()
        print(f"🔍 Reconstruction vectorstore: {sessions.count()} sessions trouvées")
        
        for session in sessions:
            # Ajouter la session
            session_text = f"""
            SESSION: {session.titre}
            Élève: {session.eleve.user.get_full_name() or session.eleve.user.username}
            Niveau: {session.eleve.get_niveau_display()}
            Classe: {session.eleve.get_classe_display()}
            Date: {session.date_creation}
            """
            texts.append(session_text.strip())
            
            # Récupérer tous les messages de cette session
            messages = MessageIA.objects.filter(session=session).order_by('date_envoi')
            print(f"  📝 Session '{session.titre}': {messages.count()} messages")
            
            for message in messages:
                if message.role == 'élève':
                    message_text = f"""
                    QUESTION ÉLÈVE: {message.contenu}
                    Élève: {session.eleve.user.get_full_name() or session.eleve.user.username}
                    Niveau: {session.eleve.get_niveau_display()}
                    Classe: {session.eleve.get_classe_display()}
                    Session: {session.titre}
                    Date: {message.date_envoi}
                    """
                else:
                    message_text = f"""
                    RÉPONSE IA: {message.contenu}
                    Session: {session.titre}
                    Date: {message.date_envoi}
                    """
                
                texts.append(message_text.strip())
        
        if texts:
            create_vector_store_from_texts(texts)
            print(f"✅ Vectorstore reconstruit avec {len(texts)} éléments de conversation")
            return len(texts)
        else:
            print("⚠️ Aucune conversation trouvée pour le vectorstore")
            return 0
            
    except Exception as e:
        print(f"❌ Erreur reconstruction vectorstore: {e}")
        return 0

def initialiser_vectorstore():
    """Fonction pour initialiser le vectorstore au démarrage de l'application"""
    try:
        # Vérifier si le vectorstore existe déjà
        if not os.path.exists(settings.VECTOR_STORE_PATH):
            print("🔄 Initialisation du vectorstore avec les conversations existantes...")
            count = reconstruire_vectorstore_complet()
            if count > 0:
                print(f"✅ Vectorstore initialisé avec {count} éléments")
            else:
                # Vectorstore vide avec message de bienvenue
                create_vector_store_from_texts([
                    "Bienvenue dans l'assistant pédagogique MrKarfour !",
                    "Posez vos questions et le répétiteur IA vous aidera.",
                    "Les conversations précédentes aident le répétiteur à mieux vous comprendre."
                ])
                print("✅ Vectorstore initialisé avec le message de bienvenue")
        else:
            print("✅ Vectorstore déjà initialisé")
    except Exception as e:
        print(f"❌ Erreur initialisation vectorstore: {e}")

@receiver(post_delete, sender=MessageIA)
def supprimer_message_vectorstore(sender, instance, **kwargs):
    """Déclenche une reconstruction quand un message est supprimé"""
    print(f"🔄 Reconstruction vectorstore suite à suppression message {instance.id}")
    reconstruire_vectorstore_complet()

@receiver(post_delete, sender=SessionIA)
def supprimer_session_vectorstore(sender, instance, **kwargs):
    """Déclenche une reconstruction quand une session est supprimée"""
    print(f"🔄 Reconstruction vectorstore suite à suppression session {instance.id}")
    reconstruire_vectorstore_complet()