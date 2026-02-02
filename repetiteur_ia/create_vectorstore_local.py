from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

# Crée quelques documents d'exemple
docs = [
    Document(page_content="La dérivation permet de calculer la pente d'une fonction en un point."),
    Document(page_content="La photosynthèse transforme l'énergie solaire en énergie chimique chez les plantes."),
    Document(page_content="En mathématiques, une équation est une égalité contenant une ou plusieurs inconnues."),
]

# Utilise le modèle local Ollama pour créer les embeddings
embeddings = OllamaEmbeddings(model="mistral")

# Crée et sauvegarde le vector store local
vectorstore = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    persist_directory="data/vectorstore"
)

vectorstore.persist()
print("✅ Vector store local créé avec Ollama !")
