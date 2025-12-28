import json
import glob
import os
import unicodedata
from difflib import SequenceMatcher

DATA_DIR = 'data'

def normalize_text(text):
    """Nettoie le texte pour la comparaison (minuscule, sans accent, sans 'le', 'la'...)"""
    text = text.lower().strip()
    # Enlever les accents
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Enlever les articles courants (facultatif mais aide)
    words = text.split()
    stopwords = {'le', 'la', 'les', 'l', 'un', 'une', 'des', 'du', 'de', 'd'}
    filtered_words = [w for w in words if w not in stopwords]
    return " ".join(filtered_words)

def similarity(a, b):
    """Calcule le % de ressemblance entre deux phrases (0 à 1)"""
    return SequenceMatcher(None, a, b).ratio()

def check_semantic_duplicates():
    # Dictionnaire : Réponse Normalisée -> Liste de questions {fichier, texte, id...}
    answers_map = {}
    total_questions = 0
    
    files = glob.glob(os.path.join(DATA_DIR, '*.json'))
    print(f"🕵️  Analyse sémantique de {len(files)} fichiers...")

    # 1. SCAN ET REGROUPEMENT PAR RÉPONSE
    for filepath in files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                for q in data:
                    total_questions += 1
                    ans_norm = normalize_text(q['answer'])
                    
                    if ans_norm not in answers_map:
                        answers_map[ans_norm] = []
                    
                    answers_map[ans_norm].append({
                        'file': filename,
                        'text': q['text'],
                        'original_answer': q['answer'],
                        'era': q.get('era', '?'),
                        'notoriety': q.get('notoriety', '?')
                    })
            except:
                pass

    print(f"Total analysé : {total_questions} questions.")
    print("-" * 60)

    # 2. DÉTECTION DES CONFLITS
    duplicates_found = 0
    
    for answer, occurrences in answers_map.items():
        # S'il y a plus d'une question avec cette réponse
        if len(occurrences) > 1:
            # On vérifie si les questions se ressemblent aussi (pour éviter le cas "Paris" capitale vs "Paris" JO)
            # Ou si c'est simplement louche d'avoir 3 fois la même réponse.
            
            print(f"🚩 RÉPONSE COMMUNE : '{occurrences[0]['original_answer'].upper()}' trouvée {len(occurrences)} fois")
            
            # Affichage des variantes
            for i, occ in enumerate(occurrences):
                print(f"   {i+1}. [{occ['file']} | Era:{occ['era']} | N:{occ['notoriety']}]")
                print(f"      Q: {occ['text']}")
            
            # Calcul de similarité entre la 1ère et les autres pour info
            ref_text = occurrences[0]['text']
            for i in range(1, len(occurrences)):
                sim = similarity(ref_text, occurrences[i]['text'])
                if sim > 0.4: # Si plus de 40% de ressemblance, c'est quasi sûr un doublon
                    print(f"      ⚠️  Similitude texte avec la n°1 : {int(sim*100)}% (Doublon probable)")
            
            print("-" * 60)
            duplicates_found += 1

    if duplicates_found == 0:
        print("✅ Incroyable, aucun conflit de réponse détecté !")
    else:
        print(f"⚠️  {duplicates_found} groupes de réponses identiques détectés.")

if __name__ == "__main__":
    check_semantic_duplicates()