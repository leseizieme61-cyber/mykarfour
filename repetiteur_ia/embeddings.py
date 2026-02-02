from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
import os
from django.conf import settings
from sentence_transformers import SentenceTransformer

#  NOUVEAU : Classe d'embeddings compatible avec SentenceTransformer
class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        """Embed search docs."""
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        """Embed query text."""
        return self.model.encode([text])[0].tolist()

# Choix de la méthode d'embedding
USE_LOCAL_EMBEDDINGS = True  # Changez à False pour utiliser OpenAI

if USE_LOCAL_EMBEDDINGS:
    embeddings = SentenceTransformerEmbeddings()
else:
    from langchain_openai import OpenAIEmbeddings
    embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

# Chemin du stockage des vecteurs
VECTOR_STORE_PATH = os.path.join(settings.BASE_DIR, "data", "vector_store.faiss")

# Créer le dossier data s'il n'existe pas
os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)

def create_vector_store_from_texts(texts):
    """
    Crée un vector store FAISS à partir d'une liste de textes.
    """
    documents = [Document(page_content=text) for text in texts]
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(documents, embeddings)
    return vector_store

def get_vector_store():
    """Charger le Vector Store existant ou en créer un nouveau"""
    if os.path.exists(VECTOR_STORE_PATH):
        try:
            return FAISS.load_local(
                VECTOR_STORE_PATH, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"❌ Erreur chargement vectorstore: {e}")
            # Recréer si corrompu
            return create_vector_store_from_texts(["Base de connaissances MrKarfour - Conversations élèves"])
    else:
        return create_vector_store_from_texts(["Base de connaissances MrKarfour - Conversations élèves"])

def search_similar_content(query, k=3):
    """Effectuer une recherche sémantique dans les embeddings"""
    try:
        vectorstore = get_vector_store()
        docs = vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    except Exception as e:
        print(f"❌ Erreur recherche vectorstore: {e}")
        return []

def ajouter_texte_au_vectorstore(texte):
    """Ajouter un texte au vectorstore existant"""
    try:
        vectorstore = get_vector_store()
        vectorstore.add_texts([texte])
        vectorstore.save_local(VECTOR_STORE_PATH)
        return True
    except Exception as e:
        print(f"❌ Erreur ajout au vectorstore: {e}")
        return False
