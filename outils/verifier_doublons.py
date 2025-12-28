import json
import glob
import os
from collections import defaultdict

def check_duplicates():
    # Dictionnaire pour stocker : "Texte de la question" -> [Liste des fichiers où elle apparaît]
    question_map = defaultdict(list)
    
    # On scanne tous les JSON
    files = glob.glob(os.path.join('data', '*.json'))
    print(f"Analyse de {len(files)} fichiers...")
    print("-" * 40)

    total_questions = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                for q in data:
                    total_questions += 1
                    # On nettoie le texte (minuscule + sans espace autour) pour comparer
                    clean_text = q['text'].strip().lower()
                    
                    # On stocke l'info : Ce texte est présent dans ce fichier
                    question_map[clean_text].append({
                        'file': filename,
                        'original_text': q['text'],
                        'era': q.get('era', 'Inconnue'),
                        'notoriety': q.get('notoriety', '?')
                    })
            except Exception as e:
                print(f"Erreur de lecture dans {filename}: {e}")

    # --- RÉSULTATS ---
    duplicates_count = 0
    for text, occurrences in question_map.items():
        if len(occurrences) > 1:
            duplicates_count += 1
            print(f"🔴 DOUBLON DÉTECTÉ ({len(occurrences)} fois) :")
            print(f"   Question : '{occurrences[0]['original_text']}'")
            for occ in occurrences:
                print(f"   -> Vu dans : {occ['file']} (Era: {occ['era']}, Noto: {occ['notoriety']})")
            print("-" * 40)

    print(f"\nBilan : {total_questions} questions analysées.")
    if duplicates_count == 0:
        print("✅ AUCUN DOUBLON TROUVÉ ! Tout est propre.")
    else:
        print(f"⚠️ {duplicates_count} doublons trouvés à corriger.")

if __name__ == "__main__":
    check_duplicates()