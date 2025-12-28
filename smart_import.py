import json
import os
import glob
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict

# --- CONFIGURATION ---
DATA_DIR = 'data'
IMPORT_FILE = 'import.json'
MAX_QUOTA = 100           # Plafond de questions par niveau
SIMILARITY_THRESHOLD = 0.60  # ⚠️ LE SEUIL CRITIQUE : Rejet si ressemblance > 60%

# Mots-clés qui forcent le classement en INTEMPOREL
KEYWORDS_INTEMPOREL = [
    "capitale", "fleuve", "rivière", "montagne", "sommet", "altitude", 
    "océan", "mer borde", "continent", "situé en", "située en", 
    "plus grand", "plus petit", "frontière", "sépare", "forme de", "symbole de"
]

def normalize_str(text):
    """Nettoie le texte (minuscule, sans accent) pour comparaison fiable"""
    if not text: return ""
    text = text.lower().strip()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text

def get_similarity(a, b):
    """Renvoie un score de 0 à 1 (1 = identique)"""
    return SequenceMatcher(None, a, b).ratio()

def load_existing_data():
    """
    Charge la mémoire du système :
    1. existing_texts : Pour les doublons exacts.
    2. existing_answers : Dico {réponse_normalisée : [liste des questions associées]}
    3. stats : Pour les quotas.
    """
    existing_texts = set()
    existing_answers = defaultdict(list) # Clé: Réponse, Valeur: Liste de textes de questions
    stats = defaultdict(lambda: defaultdict(int))
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for filepath in glob.glob(os.path.join(DATA_DIR, '*.json')):
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                for q in data:
                    # Texte
                    clean_text = normalize_str(q['text'])
                    existing_texts.add(clean_text)
                    
                    # Réponse (pour le check sémantique)
                    clean_ans = normalize_str(q['answer'])
                    existing_answers[clean_ans].append(clean_text)
                    
                    # Stats
                    noto = q.get('notoriety', 1)
                    stats[filename][noto] += 1
            except:
                pass
                
    return existing_texts, existing_answers, stats

def detect_force_intemporel(text):
    text_lower = text.lower()
    for word in KEYWORDS_INTEMPOREL:
        if word in text_lower:
            return True
    return False

def run_import():
    if not os.path.exists(IMPORT_FILE):
        print(f"❌ Fichier {IMPORT_FILE} introuvable !")
        return

    with open(IMPORT_FILE, 'r', encoding='utf-8') as f:
        try: new_questions = json.load(f)
        except: 
            print("❌ Erreur JSON.")
            return

    if not new_questions:
        print("⚠️ Rien à importer.")
        return

    # Chargement de la mémoire
    existing_texts, existing_answers, current_stats = load_existing_data()
    
    # Compteurs
    added_count = 0
    rejected_doubles_strict = 0
    rejected_doubles_semantic = 0
    rejected_quota = 0
    redirected_count = 0

    questions_by_file = {} 
    
    print(f"🧠 Démarrage du tri intelligent sur {len(new_questions)} questions...")
    print(f"   (Seuil de similarité toléré : {int(SIMILARITY_THRESHOLD*100)}%)")

    for q in new_questions:
        # Nettoyage entrées
        text_clean = normalize_str(q['text'])
        ans_clean = normalize_str(q['answer'])
        
        # --- FILTRE 1 : Doublon STRICT (Texte identique) ---
        if text_clean in existing_texts:
            rejected_doubles_strict += 1
            continue

        # --- FILTRE 2 : Doublon SÉMANTIQUE (Même réponse + Question similaire) ---
        is_semantic_duplicate = False
        if ans_clean in existing_answers:
            # On compare la nouvelle question avec TOUTES celles qui ont déjà cette réponse
            for existing_question_text in existing_answers[ans_clean]:
                score = get_similarity(text_clean, existing_question_text)
                if score > SIMILARITY_THRESHOLD:
                    is_semantic_duplicate = True
                    break # Pas la peine de continuer, c'est grillé
        
        if is_semantic_duplicate:
            rejected_doubles_semantic += 1
            continue

        # --- LOGIQUE : Redirection Intemporel ---
        target_era = q['era']
        target_theme = q['theme'].lower()
        
        if target_theme == "geographie" and target_era != "INTEMPOREL":
            if detect_force_intemporel(q['text']):
                target_era = "INTEMPOREL"
                q['era'] = "INTEMPOREL"
                q['notoriety'] = 1 
                redirected_count += 1
        
        filename = f"{target_theme}_{target_era.lower()}.json"
        target_noto = q.get('notoriety', 1)

        # --- FILTRE 3 : Quota Max ---
        if current_stats[filename][target_noto] >= MAX_QUOTA:
            rejected_quota += 1
            continue

        # --- VALIDATION FINALE ---
        if filename not in questions_by_file:
            questions_by_file[filename] = []
        
        questions_by_file[filename].append(q)
        
        # On met à jour la mémoire vive pour que les questions suivantes de la même liste ne se marchent pas dessus
        existing_texts.add(text_clean)
        existing_answers[ans_clean].append(text_clean)
        current_stats[filename][target_noto] += 1
        added_count += 1

    # Écriture
    print("-" * 40)
    for filename, questions in questions_by_file.items():
        filepath = os.path.join(DATA_DIR, filename)
        current_data = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try: current_data = json.load(f)
                except: current_data = []
        
        current_data.extend(questions)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Ajouté {len(questions)} dans {filename}")

    # Reset import
    with open(IMPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

    print("-" * 40)
    print(f"BILAN FINAL :")
    print(f"✅ Importées           : {added_count}")
    print(f"🗑️  Rejetées (Strict)   : {rejected_doubles_strict}")
    print(f"🤖 Rejetées (Similaire) : {rejected_doubles_semantic} (Car > 60% ressemblance)")
    print(f"⛔ Rejetées (Quota)     : {rejected_quota}")
    print("-" * 40)

if __name__ == "__main__":
    run_import()