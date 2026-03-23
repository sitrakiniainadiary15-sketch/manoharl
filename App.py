from flask import Flask, render_template, request, jsonify, session
import random
import math
import json
import os
import requests
import time

app = Flask(__name__)
app.secret_key = 'musique_rl_secret'

# ═══════════════════════════════════════════════════
# MÉMOIRE PERSISTANTE
# ═══════════════════════════════════════════════════
MEMORY_FILE = 'musicrl_memory.json'

def charger_memoire():
    """
    Charge la mémoire depuis le fichier JSON.
    Si la mémoire a un nombre de genres différent du catalogue actuel,
    elle est ignorée pour éviter les erreurs d'index.
    """
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Vérification critique : le nombre de genres doit correspondre
            if (len(data.get('likes', [])) == N and
                len(data.get('propositions', [])) == N):
                return data
            else:
                print(f"Mémoire ignorée : {len(data.get('likes', []))} genres sauvegardés vs {N} actuels")
                os.remove(MEMORY_FILE)  # Supprime l'ancienne mémoire incompatible
        except Exception as e:
            print(f"Erreur lecture mémoire: {e}")
    return None

def sauvegarder_memoire(data):
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur sauvegarde: {e}")

# ═══════════════════════════════════════════════════
# DEEZER API — aucune clé, aucun compte requis
# ═══════════════════════════════════════════════════
DEEZER_URL = "https://api.deezer.com/search"

# Cache pour éviter trop de requêtes Deezer
_cache_deezer = {}
_cache_time   = {}
CACHE_DUREE   = 3600  # 1 heure

GENRES_DEEZER = {
    "Rock":      "rock",
    "Pop":       "pop",
    "Hip-Hop":   "hip hop",
    "Jazz":      "jazz",
    "Classique": "classical",
    "Electro":   "electronic",
    "R&B":       "rnb soul",
    "Metal":     "metal",
}

def chercher_chansons_deezer(genre, limite=20):
    """
    Recherche des chansons sur Deezer par genre.
    Retourne une liste de chansons enrichies avec pochette et preview.
    Utilise un cache pour éviter de surcharger l'API.
    """
    now = time.time()

    # Retourner le cache si encore valide
    if genre in _cache_deezer and now - _cache_time.get(genre, 0) < CACHE_DUREE:
        return _cache_deezer[genre]

    query = GENRES_DEEZER.get(genre, genre.lower())

    try:
        response = requests.get(
            DEEZER_URL,
            params={"q": query, "limit": limite},
            timeout=5
        )
        data = response.json()

        chansons = []
        for track in data.get('data', []):
            # Garder seulement les chansons avec preview audio
            if not track.get('preview'):
                continue

            chansons.append({
                "titre":      track['title'],
                "artiste":    track['artist']['name'],
                "cover":      track['album'].get('cover_big', track['album'].get('cover', '')),
                "preview":    track['preview'],
                "popularite": track.get('rank', 0),
                "deezer_id":  track['id'],
                "bpm":        0,  # Deezer ne donne pas le BPM directement
            })

        if chansons:
            _cache_deezer[genre] = chansons
            _cache_time[genre]   = now
            return chansons

    except Exception as e:
        print(f"Erreur Deezer pour {genre}: {e}")

    # Fallback : catalogue statique si Deezer ne répond pas
    return catalogue_statique.get(genre, {}).get('chansons', [])

# ═══════════════════════════════════════════════════
# CATALOGUE STATIQUE — fallback si pas internet
# ═══════════════════════════════════════════════════
catalogue_statique = {
    "Rock": {
        "emoji": "🎸", "couleur": "#e74c3c",
        "chansons": [
            {"titre": "Bohemian Rhapsody",       "artiste": "Queen",   "bpm": 120, "cover": "", "preview": ""},
            {"titre": "Smells Like Teen Spirit", "artiste": "Nirvana", "bpm": 117, "cover": "", "preview": ""},
            {"titre": "Back in Black",           "artiste": "AC/DC",   "bpm": 94,  "cover": "", "preview": ""},
        ]
    },
    "Pop": {
        "emoji": "🎤", "couleur": "#e91e8c",
        "chansons": [
            {"titre": "Billie Jean",        "artiste": "Michael Jackson", "bpm": 117, "cover": "", "preview": ""},
            {"titre": "Rolling in the Deep","artiste": "Adele",           "bpm": 105, "cover": "", "preview": ""},
            {"titre": "Shape of You",       "artiste": "Ed Sheeran",      "bpm": 96,  "cover": "", "preview": ""},
        ]
    },
    "Hip-Hop": {
        "emoji": "🎤", "couleur": "#f39c12",
        "chansons": [
            {"titre": "HUMBLE.",     "artiste": "Kendrick Lamar", "bpm": 150, "cover": "", "preview": ""},
            {"titre": "God's Plan",  "artiste": "Drake",          "bpm": 77,  "cover": "", "preview": ""},
            {"titre": "Lose Yourself","artiste": "Eminem",        "bpm": 171, "cover": "", "preview": ""},
        ]
    },
    "Jazz": {
        "emoji": "🎷", "couleur": "#9b59b6",
        "chansons": [
            {"titre": "So What",       "artiste": "Miles Davis",  "bpm": 136, "cover": "", "preview": ""},
            {"titre": "Take Five",     "artiste": "Dave Brubeck", "bpm": 172, "cover": "", "preview": ""},
            {"titre": "Autumn Leaves", "artiste": "Bill Evans",   "bpm": 98,  "cover": "", "preview": ""},
        ]
    },
    "Classique": {
        "emoji": "🎼", "couleur": "#e67e22",
        "chansons": [
            {"titre": "Fur Elise",          "artiste": "Beethoven", "bpm": 84,  "cover": "", "preview": ""},
            {"titre": "Clair de Lune",      "artiste": "Debussy",   "bpm": 60,  "cover": "", "preview": ""},
            {"titre": "Les Quatre Saisons", "artiste": "Vivaldi",   "bpm": 128, "cover": "", "preview": ""},
        ]
    },
    "Electro": {
        "emoji": "🎧", "couleur": "#3498db",
        "chansons": [
            {"titre": "One More Time", "artiste": "Daft Punk", "bpm": 123, "cover": "", "preview": ""},
            {"titre": "Strobe",        "artiste": "deadmau5",  "bpm": 128, "cover": "", "preview": ""},
            {"titre": "Levels",        "artiste": "Avicii",    "bpm": 126, "cover": "", "preview": ""},
        ]
    },
    "R&B": {
        "emoji": "🎵", "couleur": "#1abc9c",
        "chansons": [
            {"titre": "Crazy in Love", "artiste": "Beyonce",      "bpm": 99, "cover": "", "preview": ""},
            {"titre": "Kiss",          "artiste": "Prince",        "bpm": 108,"cover": "", "preview": ""},
            {"titre": "No Scrubs",     "artiste": "TLC",           "bpm": 98, "cover": "", "preview": ""},
        ]
    },
    "Metal": {
        "emoji": "🤘", "couleur": "#c0392b",
        "chansons": [
            {"titre": "Enter Sandman",      "artiste": "Metallica",    "bpm": 123, "cover": "", "preview": ""},
            {"titre": "Paranoid",           "artiste": "Black Sabbath","bpm": 164, "cover": "", "preview": ""},
            {"titre": "Master of Puppets",  "artiste": "Metallica",    "bpm": 220, "cover": "", "preview": ""},
        ]
    },
}

# Infos visuelles par genre
GENRE_INFO = {
    "Rock":      {"emoji": "🎸", "couleur": "#e74c3c"},
    "Pop":       {"emoji": "🎤", "couleur": "#e91e8c"},
    "Hip-Hop":   {"emoji": "🎤", "couleur": "#f39c12"},
    "Jazz":      {"emoji": "🎷", "couleur": "#9b59b6"},
    "Classique": {"emoji": "🎼", "couleur": "#e67e22"},
    "Electro":   {"emoji": "🎧", "couleur": "#3498db"},
    "R&B":       {"emoji": "🎵", "couleur": "#1abc9c"},
    "Metal":     {"emoji": "🤘", "couleur": "#c0392b"},
}

genres = list(GENRE_INFO.keys())
N      = len(genres)

# ═══════════════════════════════════════════════════
# SESSION
# ═══════════════════════════════════════════════════
def init_session():
    # Toujours réinitialiser si la taille ne correspond pas
    if 'ucb' in session:
        ucb = session['ucb']
        if (len(ucb.get('likes', [])) != N or
            len(ucb.get('propositions', [])) != N):
            session.pop('ucb', None)

    if 'ucb' not in session:
        memoire = charger_memoire()
        if memoire:
            session['ucb'] = {
                'likes':            memoire.get('likes',       [0.0] * N),
                'propositions':     memoire.get('propositions',[0]   * N),
                'total':            memoire.get('total',        0),
                'likes_count':      memoire.get('likes_count',  0),
                'genre_actuel':     0,
                'chanson_actuelle': None,
                'historique':       memoire.get('historique',  []),
            }
        else:
            session['ucb'] = {
                'likes':            [0.0] * N,
                'propositions':     [0]   * N,
                'total':            0,
                'likes_count':      0,
                'genre_actuel':     0,
                'chanson_actuelle': None,
                'historique':       [],
            }

def sauvegarder_session(ucb):
    sauvegarder_memoire({
        'likes':        ucb['likes'],
        'propositions': ucb['propositions'],
        'total':        ucb['total'],
        'likes_count':  ucb.get('likes_count', 0),
        'historique':   ucb.get('historique', []),
    })

# ═══════════════════════════════════════════════════
# ALGORITHME HYBRIDE UCB1 + WARMSTART + EPSILON
# ═══════════════════════════════════════════════════
def epsilon_adaptatif(likes_count):
    base    = 0.40
    minimum = 0.05
    return max(minimum, base - likes_count * 0.018)

def ucb_score(likes, propositions, total, c=1.5):
    scores = []
    n = len(propositions)  # utilise la taille réelle, pas N global
    for i in range(n):
        if propositions[i] == 0:
            scores.append(float('inf'))
        else:
            taux  = likes[i] / propositions[i]
            bonus = c * math.sqrt(math.log(total + 1) / propositions[i])
            scores.append(taux + bonus)
    return scores

def choisir_genre(ucb):
    likes        = ucb['likes']
    propositions = ucb['propositions']
    total        = ucb['total']
    likes_count  = ucb.get('likes_count', 0)

    # Nouveau visiteur → UCB1 pur
    if likes_count == 0:
        scores    = ucb_score(likes, propositions, total)
        max_s     = max(scores)
        candidats = [i for i, s in enumerate(scores) if s == max_s]
        return random.choice(candidats)

    # Visiteur connu → epsilon adaptatif
    eps = epsilon_adaptatif(likes_count)
    if random.random() < eps:
        min_props  = min(propositions)
        peu_testes = [i for i, p in enumerate(propositions) if p <= min_props + 1]
        return random.choice(peu_testes)
    else:
        meilleur_idx  = 0
        meilleur_taux = -1.0
        for i in range(N):
            taux = likes[i] / propositions[i] if propositions[i] > 0 else 0.0
            if taux > meilleur_taux:
                meilleur_taux = taux
                meilleur_idx  = i
        return meilleur_idx

def decay_likes(likes, genre_idx, alpha=0.92):
    likes[genre_idx] *= alpha
    return likes

def choisir_chanson(genre_idx):
    """
    Choisit une chanson depuis Deezer.
    Récompense enrichie selon la popularité.
    """
    genre    = genres[genre_idx]
    chansons = chercher_chansons_deezer(genre)
    if not chansons:
        chansons = catalogue_statique.get(genre, {}).get('chansons', [])
    chanson = random.choice(chansons)

    # Récompense enrichie avec la popularité Deezer
    # Sera utilisée dans aimer() pour un signal plus riche
    popularite = chanson.get('popularite', 0)
    chanson['bonus_popularite'] = round((popularite / 1000000) * 0.2, 3) if popularite > 0 else 0.0

    return chanson

def formater_scores(likes, propositions, total):
    scores = ucb_score(likes, propositions, total)
    return [round(s, 3) if s != float('inf') else '∞' for s in scores]

def construire_reponse(ucb, genre_idx, chanson):
    """Construit la réponse JSON standard."""
    scores = formater_scores(ucb['likes'], ucb['propositions'], ucb['total'])
    info   = GENRE_INFO[genres[genre_idx]]
    return {
        'genre':        genres[genre_idx],
        'emoji':        info['emoji'],
        'couleur':      info['couleur'],
        'chanson':      chanson,
        'choix':        genre_idx,
        'likes':        [round(l, 2) for l in ucb['likes']],
        'propositions': ucb['propositions'],
        'scores':       scores,
        'total':        ucb['total'],
        'likes_count':  ucb.get('likes_count', 0),
        'epsilon':      round(epsilon_adaptatif(ucb.get('likes_count', 0)), 2),
    }

# ═══════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════
@app.route('/')
def index():
    init_session()
    ucb = session['ucb']

    genre_idx = choisir_genre(ucb)
    chanson   = choisir_chanson(genre_idx)

    ucb['propositions'][genre_idx] += 1
    ucb['total']            += 1
    ucb['genre_actuel']      = genre_idx
    ucb['chanson_actuelle']  = chanson
    session.modified = True

    scores    = formater_scores(ucb['likes'], ucb['propositions'], ucb['total'])
    info      = GENRE_INFO[genres[genre_idx]]
    est_connu = ucb.get('likes_count', 0) > 0

    return render_template('index.html',
        genres=genres,
        genre_info=GENRE_INFO,
        genre_actuel=genres[genre_idx],
        emoji=info['emoji'],
        couleur=info['couleur'],
        chanson=chanson,
        choix=genre_idx,
        likes=ucb['likes'],
        propositions=ucb['propositions'],
        scores=scores,
        total=ucb['total'],
        likes_count=ucb.get('likes_count', 0),
        est_connu=est_connu,
        epsilon=round(epsilon_adaptatif(ucb.get('likes_count', 0)), 2),
    )

@app.route('/aimer', methods=['POST'])
def aimer():
    init_session()
    ucb       = session['ucb']
    genre_idx = ucb['genre_actuel']
    chanson   = ucb.get('chanson_actuelle', {})

    # Récompense enrichie = base + bonus popularité Deezer
    bonus     = chanson.get('bonus_popularite', 0.0) if isinstance(chanson, dict) else 0.0
    ucb['likes'] = decay_likes(ucb['likes'], genre_idx)
    ucb['likes'][genre_idx] += 1.0 + bonus
    ucb['likes_count'] = ucb.get('likes_count', 0) + 1

    ucb['historique'].append({
        'genre':  genres[genre_idx],
        'titre':  chanson.get('titre', '?') if isinstance(chanson, dict) else '?',
        'action': 'like'
    })
    ucb['historique'] = ucb['historique'][-10:]
    sauvegarder_session(ucb)

    # Prochain
    genre_idx = choisir_genre(ucb)
    chanson   = choisir_chanson(genre_idx)
    ucb['propositions'][genre_idx] += 1
    ucb['total']            += 1
    ucb['genre_actuel']      = genre_idx
    ucb['chanson_actuelle']  = chanson
    session.modified = True

    return jsonify(construire_reponse(ucb, genre_idx, chanson))

@app.route('/suivant', methods=['POST'])
def suivant():
    init_session()
    ucb     = session['ucb']
    chanson = ucb.get('chanson_actuelle', {})

    ucb['historique'].append({
        'genre':  genres[ucb['genre_actuel']],
        'titre':  chanson.get('titre', '?') if isinstance(chanson, dict) else '?',
        'action': 'skip'
    })
    ucb['historique'] = ucb['historique'][-10:]
    sauvegarder_session(ucb)

    genre_idx = choisir_genre(ucb)
    chanson   = choisir_chanson(genre_idx)
    ucb['propositions'][genre_idx] += 1
    ucb['total']            += 1
    ucb['genre_actuel']      = genre_idx
    ucb['chanson_actuelle']  = chanson
    session.modified = True

    return jsonify(construire_reponse(ucb, genre_idx, chanson))

@app.route('/reinitialiser', methods=['POST'])
def reinitialiser():
    session.pop('ucb', None)
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    return jsonify({'ok': True})

@app.route('/memoire', methods=['GET'])
def voir_memoire():
    memoire = charger_memoire()
    if not memoire:
        return jsonify({'message': 'Aucune memoire enregistree.'})
    return jsonify(memoire)

@app.route('/chansons/<genre>', methods=['GET'])
def voir_chansons(genre):
    """Route debug — voir les chansons Deezer pour un genre."""
    chansons = chercher_chansons_deezer(genre)
    return jsonify({'genre': genre, 'count': len(chansons), 'chansons': chansons[:5]})

if __name__ == '__main__':
    app.run(debug=True)