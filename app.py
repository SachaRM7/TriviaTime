from flask import Flask, render_template, request, session, jsonify, redirect, url_for
import json
import random
import os
import glob

app = Flask(__name__)
app.secret_key = 'TrivialSecretKeySuperSecurise'  # Nécessaire pour gérer les sessions

# Chargement des questions
def load_questions():
    questions = []
    id_counter = 1 # On commence le comptage à 1
    
    # On cherche tous les fichiers .json dans le dossier 'data'
    # Assure-toi d'avoir créé le dossier 'data' à côté de app.py
    path = os.path.join(os.path.dirname(__file__), 'data', '*.json')
    files = glob.glob(path)
    
    print(f"Chargement des fichiers : {files}") # Pour voir ce qui se passe dans la console
    
    for file_name in files:
        with open(file_name, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # On ajoute chaque question à la liste principale en lui donnant un ID
                for q in data:
                    q['id'] = id_counter
                    questions.append(q)
                    id_counter += 1
            except json.JSONDecodeError:
                print(f"Erreur de lecture dans le fichier {file_name}. Vérifie les virgules !")

    print(f"Total questions chargées : {len(questions)}")
    return questions

ALL_QUESTIONS = load_questions()

# --- ALGORITHME DE DIFFICULTÉ ---
def filter_questions(age, difficulty, theme, asked_ids):
    current_year = 2025
    birth_year = current_year - int(age)

    # --- 1. CALCUL DYNAMIQUE (Fenêtre Glissante) ---
    comfort_eras = []
    all_decades = [1960, 1970, 1980, 1990, 2000, 2010, 2020]

    for decade in all_decades:
        age_start = decade - birth_year
        age_end = (decade + 9) - birth_year
        
        # On garde la décennie si le joueur avait entre 10 et 40 ans
        if age_end >= 10 and age_start <= 40:
            comfort_eras.append(f"{decade}s")
            
    # Note : On ne met PAS "INTEMPOREL" dans comfort_eras, c'est normal.

    # --- 2. FILTRAGE DES QUESTIONS ---
    candidates = []  # <--- IMPORTANT : On initialise la liste ICI, avant de scanner les questions

    for q in ALL_QUESTIONS:
        if q['theme'] != theme:
            continue

        # A. Logique SPÉCIALE pour INTEMPOREL
        # Ici, l'âge ne compte pas, seule la difficulté compte.
        if q['era'] == "INTEMPOREL":
            if (difficulty == "facile" and q['notoriety'] == 1) or \
               (difficulty == "moyen" and q['notoriety'] == 2) or \
               (difficulty == "difficile" and q['notoriety'] == 3):
                candidates.append(q)
            continue  # On passe à la question suivante, celle-ci est traitée

        # B. Logique STANDARD pour les époques (1980s, etc.)
        if difficulty == "facile":
            # Facile = Tout le monde connait (1) OU Connu (2) dans ma zone de confort
            if q['notoriety'] == 1 or (q['notoriety'] == 2 and q['era'] in comfort_eras):
                candidates.append(q)
        
        elif difficulty == "moyen":
            # Moyen = Connu (2) hors zone OU Expert (3) dans ma zone
            if (q['notoriety'] == 2 and q['era'] not in comfort_eras) or \
               (q['notoriety'] == 3 and q['era'] in comfort_eras):
                candidates.append(q)

        elif difficulty == "difficile":
            # Difficile = Expert (3) hors zone de confort (Le cauchemar !)
            if (q['notoriety'] == 3 and q['era'] not in comfort_eras):
                candidates.append(q)

    # --- 3. SÉCURITÉS ---
    # Si la liste est vide (trop restrictif), on élargit la recherche
    if not candidates:
        target_noto = 1 if difficulty == "facile" else 2 if difficulty == "moyen" else 3
        candidates = [q for q in ALL_QUESTIONS if q['theme'] == theme and q['notoriety'] == target_noto]
    
    # Si vraiment toujours rien, on prend tout le thème
    if not candidates:
         candidates = [q for q in ALL_QUESTIONS if q['theme'] == theme]
    
    if not candidates: return None

    # --- 4. ANTI-RÉPÉTITION ---
    # On privilégie les questions jamais posées
    unasked_candidates = [q for q in candidates if q['id'] not in asked_ids]

    if unasked_candidates:
        return random.choice(unasked_candidates)
    else:
        # Si tout a été posé, on pioche dans les anciennes (reshuffle)
        return random.choice(candidates)

# --- ROUTES ---

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/setup', methods=['POST'])
def setup():
    # Récupération des joueurs depuis le formulaire
    players_data = []
    names = request.form.getlist('name')
    ages = request.form.getlist('age')
    
    for n, a in zip(names, ages):
        if n and a:
            players_data.append({'name': n, 'age': int(a), 'score': 0})
    
    session['players'] = players_data
    session['current_player_idx'] = 0
    session['asked_ids'] = []
    return redirect(url_for('game'))

@app.route('/game')
def game():
    if 'players' not in session:
        return redirect(url_for('index'))
    
    current_idx = session.get('current_player_idx', 0)
    players = session['players']
    current_player = players[current_idx]
    
    # Choix aléatoire d'un thème pour ce tour
    themes = list(set([q['theme'] for q in ALL_QUESTIONS]))
    current_theme = random.choice(themes)
    
    return render_template('game.html', 
                           player=current_player, 
                           players=players, 
                           theme=current_theme)

@app.route('/api/get_question', methods=['POST'])
def api_get_question():
    data = request.json
    diff = data.get('difficulty')
    theme = data.get('theme')
    age = data.get('age')
    
    # On récupère la liste des ID déjà utilisés (ou une liste vide si bug)
    asked_ids = session.get('asked_ids', [])
    
    # On passe asked_ids à la fonction
    question = filter_questions(age, diff, theme, asked_ids)
    
    if question:
        # --- SAUVEGARDE ---
        # On ajoute l'ID de la question choisie à la liste
        # Note : En Flask, pour modifier une liste dans la session, il faut la réassigner
        session['asked_ids'] = asked_ids + [question['id']]
        
        return jsonify({'success': True, 'question': question})
    else:
        return jsonify({'success': False, 'message': "Pas de question trouvée..."})

@app.route('/api/validate', methods=['POST'])
def api_validate():
    data = request.json
    points = data.get('points')
    correct = data.get('correct') # Booléen
    
    if correct:
        idx = session['current_player_idx']
        session['players'][idx]['score'] += points
        session.modified = True # Important pour sauvegarder la session
    
    # Passer au joueur suivant
    total_players = len(session['players'])
    session['current_player_idx'] = (session['current_player_idx'] + 1) % total_players
    
    return jsonify({'success': True})

if __name__ == '__main__':
    # host='0.0.0.0' permet aux autres PC du réseau de se connecter
    app.run(debug=True, host='0.0.0.0', port=5000)