import openai
from django.conf import settings
import os
from datetime import datetime
import json
import tempfile
from django.core.files.storage import FileSystemStorage

# Configuration du client OpenAI
def get_openai_client():
    """Retourne le client OpenAI configuré"""
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)

def generer_contenu_ia(titre, matiere, eleve):
    """
    Version réelle avec l'API OpenAI
    """
    try:
        prompt = f"""
        Tu es un répétiteur pédagogique expert. 
        Crée une leçon sur le sujet "{titre}" dans la matière {matiere} 
        pour un élève de {eleve.get_niveau_display()} {eleve.get_classe_display()}.
        
        La leçon doit inclure:
        1. Une introduction au sujet
        2. Les concepts clés expliqués clairement
        3. Des exemples concrets adaptés au niveau
        4. Une section d'exercices pratiques
        5. Un résumé des points importants
        
        Formatte le résultat en HTML basique.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un professeur expert, clair et pédagogique."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Erreur lors de la génération IA: {e}")
        return f"<p>Contenu temporairement indisponible pour {titre} en {matiere}.</p>"

def generer_salutation_eleve(eleve):
    """
    Retourne une salutation courte pour l'élève avec fallback
    """
    try:
        if not getattr(settings, 'OPENAI_API_KEY', None):
            raise RuntimeError("OPENAI_API_KEY non configurée")

        # Vérifier si la clé API est valide
        if settings.OPENAI_API_KEY.startswith('sk-proj-'):
            # Clé probablement invalide ou sans crédits
            raise RuntimeError("Clé API sans crédits")
        
        nom = getattr(eleve.user, 'first_name', '') or getattr(eleve.user, 'username', 'élève')
        niveau = getattr(eleve, 'get_niveau_display', lambda: '')()
        
        prompt = f"Écris une salutation courte et chaleureuse en français pour l'élève {nom}"
        if niveau:
            prompt += f", niveau {niveau}"
        prompt += ". Garde la salutation en une phrase."

        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un assistant bienveillant et pédagogique."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60,
            temperature=0.6
        )
        salutation = response.choices[0].message.content.strip()
        return salutation
        
    except Exception as e:
        print(f"Erreur génération salutation: {e}")
        # Fallback simple et fiable
        try:
            nom = getattr(eleve.user, 'first_name', '') or getattr(eleve.user, 'username', 'élève')
        except Exception:
            nom = 'élève'
        
        salutations_fallback = [
            f"Bonjour {nom} ! Prêt·e pour une session de révision avec MrKarfour ?",
            f"Salut {nom} ! Bienvenue dans votre espace d'apprentissage.",
            f"Bien le bonjour {nom} ! Votre répétiteur MrKarfour est à votre service.",
            f"Enchanté {nom} ! Commençons cette session pédagogique."
        ]
        import random
        return random.choice(salutations_fallback)

def repondre_au_repetiteur(question, contexte_pedagogique=None, contexte_session=None, 
                          niveau_eleve="secondaire", historique_conversation=""):
    """
    Version améliorée avec contexte de session, historique et fallback robuste
    """
    try:
        if not getattr(settings, 'OPENAI_API_KEY', None):
            raise RuntimeError("API key non configurée")

        # Construction du contexte pédagogique
        contexte_text = ""
        if contexte_pedagogique and contexte_pedagogique.get('contenus_similaires'):
            contexte_text = "CONTEXTE PÉDAGOGIQUE DISPONIBLE:\n"
            for i, contenu in enumerate(contexte_pedagogique['contenus_similaires'][:3], 1):  # Limiter à 3 contenus
                contexte_text += f"{i}. {contenu}\n\n"
        
        # Construction du contexte de session
        contexte_session_text = ""
        if contexte_session:
            matiere = contexte_session.get('matiere', 'Non spécifiée')
            objectifs = contexte_session.get('objectifs', 'Aucun objectif spécifique')
            soumissions_count = len(contexte_session.get('soumissions', []))
            
            contexte_session_text = f"""
CONTEXTE DE SESSION:
- Matière en cours: {matiere}
- Objectifs: {objectifs}
- Documents soumis: {soumissions_count}
"""
        
        # Construction du contexte historique
        contexte_historique_text = ""
        if historique_conversation:
            contexte_historique_text = f"""
HISTORIQUE RÉCENT DE LA CONVERSATION:
{historique_conversation}

CONSIGNES POUR L'HISTORIQUE:
- Prends en compte cet historique pour maintenir la cohérence
- Évite les répétitions des explications déjà données
- Fais des liens avec les sujets précédemment abordés
- Si l'élève revient sur un point déjà discuté, approfondis ou donne une nouvelle perspective
- Utilise l'historique pour mieux comprendre le niveau et les besoins de l'élève
"""
        
        # Construction du prompt amélioré
        prompt = f"""
Tu es MrKarfour, un répétiteur pédagogique bienveillant pour des élèves de {niveau_eleve}.

{contexte_historique_text}

{contexte_session_text}

{contexte_text}

QUESTION ACTUELLE DE L'ÉLÈVE:
"{question}"

TA MISSION:
1. Réponds de façon claire et adaptée au niveau {niveau_eleve}
2. Si une session est active, relie ta réponse aux objectifs de révision
3. Utilise le contexte pédagogique si pertinent
4. Prends en compte l'historique de conversation pour:
   - Maintenir la cohérence
   - Éviter les répétitions inutiles
   - Faire des liens avec les échanges précédents
   - Adapter ton approche en fonction du profil de l'élève
5. Sois encourageant et pédagogique
6. Utilise des exemples concrets si nécessaire
7. Si la question fait suite à un échange précédent, fais explicitement le lien
8. Termine par une question ouverte pour encourager la poursuite du dialogue

RÉPONSE (en français, naturelle et conversationnelle, en maintenant une continuité avec l'historique):
"""
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": """Tu es MrKarfour, un répétiteur pédagogique exceptionnel. 
                    Tes qualités: bienveillant, patient, clair, encourageant.
                    Tu adaptes toujours tes explications au niveau de l'élève.
                    Tu es spécialisé dans l'aide aux révisions et l'explication des concepts difficiles.
                    Tu gardes en mémoire l'historique des conversations pour fournir des réponses cohérentes
                    et éviter les répétitions tout en approfondissant les sujets."""
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0.7
        )

        reponse = response.choices[0].message.content.strip()
        return reponse

    except Exception as e:
        print(f"[ERREUR IA Répétiteur]: {e}")
        # Réponse de fallback contextuelle avec prise en compte de l'historique
        if contexte_session and contexte_session.get('matiere'):
            matiere = contexte_session['matiere']
            return f"Bonjour ! Je suis MrKarfour. Pour votre question sur {matiere}, je suis actuellement en cours de configuration. En attendant, n'hésitez pas à explorer vos documents de cours pour {matiere} !"
        else:
            # Essayer de personnaliser même en fallback
            if historique_conversation:
                return f"Bonjour ! Je vois que nous avons déjà échangé. Pour votre question '{question[:50]}...', je suis temporairement en maintenance. Je me souviens de notre conversation précédente et serai bientôt de retour pour poursuivre !"
            else:
                return f"Bonjour ! Je suis MrKarfour, votre répétiteur IA. Pour votre question '{question[:50]}...', je suis actuellement en cours de configuration. En attendant, n'hésitez pas à explorer vos cours et exercices !"

def transcrire_audio(fichier_audio):
    """
    Convertit la voix de l'élève en texte grâce à Whisper
    """
    try:
        if not getattr(settings, 'OPENAI_API_KEY', None) or settings.OPENAI_API_KEY.startswith('sk-proj-'):
            return "Fonctionnalité audio temporairement indisponible. Veuillez taper votre question."
        
        # Sauvegarder le fichier temporairement
        fs = FileSystemStorage()
        filename = fs.save(fichier_audio.name, fichier_audio)
        file_path = fs.path(filename)
        
        # Transcrire avec Whisper
        with open(file_path, "rb") as audio_file:
            transcript = get_openai_client().audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="fr"  # Spécifier le français pour de meilleurs résultats
            )
        
        # Nettoyer le fichier temporaire
        fs.delete(filename)
        
        return transcript.strip()

    except Exception as e:
        print(f"[ERREUR TRANSCRIPTION]: {e}")
        return "Je n'ai pas compris la question audio. Pouvez-vous répéter ou écrire votre question ?"

def generer_audio(texte):
    """
    Transforme la réponse texte en audio via TTS
    """
    try:
        if not getattr(settings, 'OPENAI_API_KEY', None) or settings.OPENAI_API_KEY.startswith('sk-proj-'):
            return ""  # Retourner une chaîne vide si pas d'API fonctionnelle
        
        if not texte or len(texte.strip()) < 10:
            return ""
            
        # Conversion du texte en parole
        response = get_openai_client().audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=texte[:1000]  # Limiter la longueur
        )
        
        # Sauvegarder dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            response.stream_to_file(tmp_file.name)
            return tmp_file.name

    except Exception as e:
        print(f"[ERREUR AUDIO]: {e}")
        return ""

def generer_quiz_ia(cours):
    """
    Version réelle avec l'API OpenAI pour générer un quiz
    """
    try:
        prompt = f"""
        En te basant sur le cours suivant: {cours.titre} en {cours.matiere},
        génère un quiz de 5 questions avec 4 options de réponse chaque et indique la réponse correcte.
        
        Format attendu: une liste JSON où chaque élément a:
        - "question": le texte de la question
        - "options": une liste de 4 options
        - "reponse_correcte": l'option correcte (exactement comme dans la liste)
        
        Retourne uniquement le JSON, sans autre texte.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en création de quiz pédagogiques."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.5
        )
        
        questions = json.loads(response.choices[0].message.content)
        return questions
    
    except Exception as e:
        print(f"Erreur lors de la génération du quiz: {e}")
        return []

def _analyser_intention_question(question):
    """
    Analyse l'intention pédagogique derrière la question
    """
    question_lower = question.lower()
    
    intentions = {
        'explication': ['explique', 'comment', 'pourquoi', 'qu\'est-ce que', 'définition', 'que veut dire', 'signifie'],
        'exercice': ['exercice', 'problème', 'calcul', 'résoudre', 'application', 'calcule', 'résous'],
        'methode': ['méthode', 'technique', 'procédure', 'comment faire', 'étapes', 'marche à suivre'],
        'revision': ['révision', 'rappel', 'réviser', 'préparation', 'répète', 'rappel'],
        'correction': ['corriger', 'erreur', 'faux', 'juste', 'correct', 'vérifie'],
        'approfondissement': ['aller plus loin', 'approfondir', 'en savoir plus', 'détaillé'],
        'exemple': ['exemple', 'exemples', 'cas concret', 'illustration'],
        'comparaison': ['différence', 'comparer', 'contraire', 'opposé', 'similaire']
    }
    
    for intention, mots_cles in intentions.items():
        if any(mot in question_lower for mot in mots_cles):
            return intention
            
    return 'explication'

def analyser_contenu_soumission(contenu_texte, matiere, niveau_eleve):
    """
    Analyse le contenu soumis par l'élève pour en extraire les points clés
    """
    try:
        prompt = f"""
        Analyse ce contenu pédagogique en {matiere} pour un élève de {niveau_eleve} et identifie les éléments suivants:
        
        CONTENU À ANALYSER:
        {contenu_texte[:2000]}
        
        TON ANALYSE DOIT IDENTIFIER:
        1. Les 3-5 concepts principaux abordés
        2. Les définitions importantes
        3. Les formules ou théorèmes clés (si applicable)
        4. Les exemples significatifs
        5. Les difficultés potentielles pour un élève de ce niveau
        
        Format de réponse: une liste structurée et concise en français.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse de contenu pédagogique."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur analyse contenu: {e}")
        return "Analyse automatique temporairement indisponible."

def generer_plan_revision_session(session, soumissions):
    """
    Génère un plan de révision personnalisé basé sur la session et les soumissions
    """
    try:
        matiere = session.emploi_temps.matiere
        objectifs = session.objectifs
        contenu_soumissions = "\n".join([s.contenu_texte for s in soumissions if s.contenu_texte])
        
        prompt = f"""
        Crée un plan de révision de {session.duree_prevue} minutes pour une session de {matiere}.
        
        CONTEXTE:
        - Objectifs: {objectifs}
        - Contenu soumis par l'élève: {contenu_soumissions[:1000]}
        - Durée disponible: {session.duree_prevue} minutes
        
        STRUCTURE ATTENDUE:
        1. Révision des concepts de base (X minutes)
        2. Exercices d'application (X minutes) 
        3. Points difficiles à retravailler (X minutes)
        4. Synthèse et vérification (X minutes)
        
        Sois précis dans la répartition du temps et propose des activités concrètes.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en planification de révisions pédagogiques."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.5
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur génération plan révision: {e}")
        return f"Plan de révision standard pour {matiere}:\n1. Révision des bases (15min)\n2. Exercices pratiques (20min)\n3. Synthèse (10min)"

def generer_suggestions_exercices(matiere, niveau_eleve, concepts_cles):
    """
    Génère des suggestions d'exercices adaptés au niveau et aux concepts
    """
    try:
        prompt = f"""
        Propose 3 exercices adaptés pour un élève de {niveau_eleve} en {matiere}.
        
        Concepts à travailler: {concepts_cles}
        
        Pour chaque exercice, indique:
        - L'énoncé clair
        - Le niveau de difficulté (Facile, Moyen, Difficile)
        - Les compétences travaillées
        - Un indice pour aider l'élève si besoin
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un créateur d'exercices pédagogiques."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.6
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur génération exercices: {e}")
        return f"Exercices standards pour {matiere}:\n1. Exercice d'application basique\n2. Problème contextualisé\n3. Question de réflexion"

def evaluer_comprehension_eleve(reponses_eleve, questions_posees):
    """
    Évalue la compréhension de l'élève basée sur ses réponses
    """
    try:
        prompt = f"""
        Évalue la compréhension d'un élève basée sur ses réponses:
        
        QUESTIONS POSÉES: {questions_posees}
        RÉPONSES DE L'ÉLÈVE: {reponses_eleve}
        
        Donne une évaluation avec:
        - Points forts identifiés
        - Points à retravailler
        - Suggestions pour progresser
        - Score global de compréhension (1-10)
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un évaluateur pédagogique bienveillant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur évaluation compréhension: {e}")
        return "Évaluation automatique temporairement indisponible."

# Fonctions de fallback améliorées
def generer_contenu_ia_fallback(titre, matiere, niveau="secondaire"):
    return f"""
    <div class="prose max-w-none">
        <h2 class="text-2xl font-bold text-gray-800 mb-4">{titre}</h2>
        <p class="text-gray-600 mb-4">Matière: <strong>{matiere}</strong> | Niveau: <strong>{niveau}</strong></p>
        
        <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
            <p class="text-blue-700">
                <strong>📚 Contenu en préparation</strong><br>
                Nos experts pédagogiques préparent actuellement le contenu pour cette leçon. 
                En attendant, vous pouvez:
            </p>
            <ul class="list-disc list-inside mt-2 text-blue-600">
                <li>Consulter vos documents de cours</li>
                <li>Réviser les chapitres précédents</li>
                <li>Poser des questions spécifiques à MrKarfour</li>
            </ul>
        </div>
    </div>
    """

def get_salutation_fallback(eleve):
    """Fallback robuste pour les salutations"""
    try:
        nom = getattr(eleve.user, 'first_name', '') or getattr(eleve.user, 'username', 'élève')
    except:
        nom = 'élève'
    
    salutations = [
        f"Bonjour {nom} ! Votre répétiteur MrKarfour est prêt à vous aider.",
        f"Salut {nom} ! Commençons cette session d'apprentissage.",
        f"Bienvenue {nom} ! Je suis MrKarfour, votre assistant pédagogique.",
        f"Enchanté {nom} ! Prêt·e pour une séance de révision ?"
    ]
    import random
    return random.choice(salutations)

# Fonction utilitaire pour nettoyer les réponses IA
def nettoyer_reponse_ia(reponse):
    """
    Nettoie et formate la réponse de l'IA pour l'affichage
    """
    if not reponse:
        return "Je n'ai pas pu générer de réponse pour le moment. Veuillez réessayer."
    
    # Supprimer les éventuels préfixes indésirables
    prefixes = ["MrKarfour:", "Assistant:", "Réponse:"]
    for prefix in prefixes:
        if reponse.startswith(prefix):
            reponse = reponse[len(prefix):].strip()
    
    return reponse

# Nouvelle fonction pour analyser l'historique et en extraire le contexte
def analyser_historique_conversation(historique_conversations):
    """
    Analyse l'historique des conversations pour en extraire les thèmes récurrents
    et le niveau de compréhension de l'élève
    """
    if not historique_conversations:
        return ""
    
    try:
        # Préparer le texte de l'historique
        historique_text = "\n".join([
            f"Échange {i+1}: Q: {conv['question']} | R: {conv['reponse'][:200]}..."
            for i, conv in enumerate(historique_conversations[-5:])  # Derniers 5 échanges
        ])
        
        prompt = f"""
        Analyse cet historique de conversation entre un élève et son répétiteur IA:
        
        {historique_text}
        
        Identifie:
        1. Les thèmes ou sujets récurrents
        2. Le niveau de compréhension apparent de l'élève
        3. Les difficultés persistantes
        4. Les intérêts manifestés
        5. Le style d'apprentissage (ex: besoin d'exemples, de schémas, etc.)
        
        Donne une analyse concise en français.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en analyse des interactions pédagogiques."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur analyse historique: {e}")
        return ""

# Fonction pour générer un résumé de session basé sur l'historique
def generer_resume_session(historique_conversations, objectifs_session):
    """
    Génère un résumé de ce qui a été accompli pendant la session
    """
    if not historique_conversations:
        return "Aucun échange enregistré pendant cette session."
    
    try:
        historique_text = "\n".join([
            f"- {conv['question']} → {conv['reponse'][:100]}..."
            for conv in historique_conversations
        ])
        
        prompt = f"""
        Résume les accomplissements de cette session de révision basée sur cet historique:
        
        OBJECTIFS INITIAUX: {objectifs_session}
        
        ÉCHANGES PENDANT LA SESSION:
        {historique_text}
        
        Crée un résumé qui:
        1. Liste les concepts abordés
        2. Évalue la progression par rapport aux objectifs
        3. Identifie les points à retravailler
        4. Donne des recommandations pour la prochaine session
        
        Format: résumé structuré en français.
        """
        
        response = get_openai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un expert en synthèse pédagogique."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Erreur génération résumé session: {e}")
        return f"Session terminée. {len(historique_conversations)} échanges réalisés."

def extraire_texte_fichier(chemin_fichier):
    """
    Extrait le texte d'un fichier (PDF, DOCX, etc.)
    À implémenter selon vos besoins
    """
    try:
        # Exemple basique pour les fichiers texte
        if chemin_fichier.endswith('.txt'):
            with open(chemin_fichier, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Pour d'autres formats, vous pouvez utiliser des bibliothèques comme:
        # - PyPDF2 pour les PDF
        # - python-docx pour les DOCX
        # - etc.
        
        return f"Contenu du fichier: {os.path.basename(chemin_fichier)}"
        
    except Exception as e:
        print(f"Erreur extraction texte fichier: {e}")
        return f"Fichier: {os.path.basename(chemin_fichier)}"