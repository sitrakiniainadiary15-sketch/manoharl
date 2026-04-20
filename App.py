from flask import Flask, render_template, request, jsonify, session
import random
import math
import json
import os
import requests
import time
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'musique_rl_secret')

# ═══════════════════════════════════════════════════
# MÉMOIRE PERSISTANTE
# ═══════════════════════════════════════════════════
MEMORY_FILE = 'musicrl_memory.json'

def charger_memoire():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if (len(data.get('likes', [])) == N and
                len(data.get('propositions', [])) == N):
                return data
            else:
                print(f"Mémoire ignorée : {len(data.get('likes', []))} genres sauvegardés vs {N} actuels")
                os.remove(MEMORY_FILE)
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
# DEEZER API
# ═══════════════════════════════════════════════════
DEEZER_URL = "https://api.deezer.com/search"

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

# ═══════════════════════════════════════════════════
# CATALOGUE STATIQUE — fallback si pas internet
# ═══════════════════════════════════════════════════
catalogue_statique = {
    "Rock": {
        "emoji": "🎸", "couleur": "#e74c3c",
        "chansons": [
            {"titre": "Bohemian Rhapsody",       "artiste": "Queen",   "bpm": 120, "cover": "https://upload.wikimedia.org/wikipedia/en/9/9f/Bohemian_Rhapsody.png", "preview": "", "popularite": 0},
            {"titre": "Smells Like Teen Spirit", "artiste": "Nirvana", "bpm": 117, "cover": "https://upload.wikimedia.org/wikipedia/en/b/b7/NirvanaNevermindalbumcover.jpg", "preview": "", "popularite": 0},
            {"titre": "Back in Black",           "artiste": "AC/DC",   "bpm": 94,  "cover": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Acdc_backinblack.jpg/400px-Acdc_backinblack.jpg", "preview": "", "popularite": 0},
        ]
    },
    "Pop": {
        "emoji": "🎤", "couleur": "#e91e8c",
        "chansons": [
            {"titre": "Billie Jean",         "artiste": "Michael Jackson", "bpm": 117, "cover": "https://upload.wikimedia.org/wikipedia/en/5/55/Michael_Jackson_-_Thriller.png", "preview": "", "popularite": 0},
            {"titre": "Rolling in the Deep", "artiste": "Adele",           "bpm": 105, "cover": "https://upload.wikimedia.org/wikipedia/en/1/1b/Adele_-_21.png", "preview": "", "popularite": 0},
            {"titre": "Shape of You",        "artiste": "Ed Sheeran",      "bpm": 96,  "cover": "https://upload.wikimedia.org/wikipedia/en/3/35/Ed_Sheeran_-_%C3%B7_%28Divide%29.png", "preview": "", "popularite": 0},
        ]
    },
    "Hip-Hop": {
        "emoji": "🎤", "couleur": "#f39c12",
        "chansons": [
            {"titre": "HUMBLE.",      "artiste": "Kendrick Lamar", "bpm": 150, "cover": "https://upload.wikimedia.org/wikipedia/en/7/7c/Damn._Kendrick_Lamar.jpg", "preview": "", "popularite": 0},
            {"titre": "God's Plan",   "artiste": "Drake",          "bpm": 77,  "cover": "https://upload.wikimedia.org/wikipedia/en/9/90/Scorpion_by_Drake.jpg", "preview": "", "popularite": 0},
            {"titre": "Lose Yourself","artiste": "Eminem",         "bpm": 171, "cover": "https://upload.wikimedia.org/wikipedia/en/4/43/Eminem_-_Lose_Yourself.jpg", "preview": "", "popularite": 0},
        ]
    },
    "Jazz": {
        "emoji": "🎷", "couleur": "#9b59b6",
        "chansons": [
            {"titre": "So What",       "artiste": "Miles Davis",  "bpm": 136, "cover": "https://upload.wikimedia.org/wikipedia/en/c/c4/Miles_Davis_-_Kind_of_Blue.jpg", "preview": "", "popularite": 0},
            {"titre": "Take Five",     "artiste": "Dave Brubeck", "bpm": 172, "cover": "https://upload.wikimedia.org/wikipedia/en/a/a0/Take_Five.PNG", "preview": "", "popularite": 0},
            {"titre": "Autumn Leaves", "artiste": "Bill Evans",   "bpm": 98,  "cover": "https://upload.wikimedia.org/wikipedia/en/1/17/Portrait_in_Jazz.jpg", "preview": "", "popularite": 0},
        ]
    },
    "Classique": {
        "emoji": "🎼", "couleur": "#e67e22",
        "chansons": [
            {"titre": "Fur Elise",          "artiste": "Beethoven", "bpm": 84,  "cover": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Beethoven.jpg/400px-Beethoven.jpg", "preview": "", "popularite": 0},
            {"titre": "Clair de Lune",      "artiste": "Debussy",   "bpm": 60,  "cover": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/48/Claude_Debussy_circa_1908%2C_foto_av_Nadar.jpg/400px-Claude_Debussy_circa_1908%2C_foto_av_Nadar.jpg", "preview": "", "popularite": 0},
            {"titre": "Les Quatre Saisons", "artiste": "Vivaldi",   "bpm": 128, "cover": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bd/Vivaldi.jpg/400px-Vivaldi.jpg", "preview": "", "popularite": 0},
        ]
    },
    "Electro": {
        "emoji": "🎧", "couleur": "#3498db",
        "chansons": [
            {"titre": "One More Time", "artiste": "Daft Punk", "bpm": 123, "cover": "https://upload.wikimedia.org/wikipedia/en/0/0d/DaftPunkDiscoveryalbumcover.jpg", "preview": "", "popularite": 0},
            {"titre": "Strobe",        "artiste": "deadmau5",  "bpm": 128, "cover": "https://upload.wikimedia.org/wikipedia/en/7/77/For_Lack_of_a_Better_Name.jpg", "preview": "", "popularite": 0},
            {"titre": "Levels",        "artiste": "Avicii",    "bpm": 126, "cover": "https://upload.wikimedia.org/wikipedia/en/f/f5/Avicii_True_album_cover.png", "preview": "", "popularite": 0},
        ]
    },
    "R&B": {
        "emoji": "🎵", "couleur": "#1abc9c",
        "chansons": [
            {"titre": "Crazy in Love", "artiste": "Beyonce", "bpm": 99,  "cover": "https://upload.wikimedia.org/wikipedia/en/a/a2/Beyonc%C3%A9_-_Dangerously_in_Love.png", "preview": "", "popularite": 0},
            {"titre": "Kiss",          "artiste": "Prince",  "bpm": 108, "cover": "https://upload.wikimedia.org/wikipedia/en/b/b4/Parade_%28album_cover%29.png", "preview": "", "popularite": 0},
            {"titre": "No Scrubs",     "artiste": "TLC",     "bpm": 98,  "cover": "https://upload.wikimedia.org/wikipedia/en/a/a5/Tlc-fanmail.jpg", "preview": "", "popularite": 0},
        ]
    },
    "Metal": {
        "emoji": "🤘", "couleur": "#c0392b",
        "chansons": [
            {"titre": "Enter Sandman",     "artiste": "Metallica",    "bpm": 123, "cover": "https://upload.wikimedia.org/wikipedia/en/d/d8/Metallica_-_Metallica_%28album%29.jpg", "preview": "", "popularite": 0},
            {"titre": "Paranoid",          "artiste": "Black Sabbath","bpm": 164, "cover": "https://upload.wikimedia.org/wikipedia/en/2/26/Black_Sabbath_-_Paranoid.jpg", "preview": "", "popularite": 0},
            {"titre": "Master of Puppets","artiste": "Metallica",    "bpm": 220, "cover": "https://upload.wikimedia.org/wikipedia/en/b/b2/Metallica_-_Master_of_Puppets_cover.jpg", "preview": "", "popularite": 0},
        ]
    },
}

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
# CATALOGUE DEEZER — chargé une seule fois au démarrage
# ═══════════════════════════════════════════════════
# Dictionnaire global : genre → liste de chansons Deezer
catalogue_deezer = {}
_catalogue_lock  = threading.Lock()
_catalogue_pret  = False   # True quand tous les genres sont chargés

def charger_catalogue_deezer():
    """
    Appelé dans un thread au démarrage.
    Remplit catalogue_deezer pour chaque genre depuis l'API Deezer.
    Si un genre échoue → fallback statique conservé.
    """
    global _catalogue_pret
    print("🎵 Chargement du catalogue Deezer en arrière-plan…")

    for genre in genres:
        query = GENRES_DEEZER.get(genre, genre.lower())
        try:
            response = requests.get(
                DEEZER_URL,
                params={"q": query, "limit": 20},
                timeout=8
            )
            data = response.json()
            chansons = []
            for track in data.get('data', []):
                if not track.get('preview'):
                    continue
                chansons.append({
                    "titre":      track['title'],
                    "artiste":    track['artist']['name'],
                    "cover":      track['album'].get('cover_big', track['album'].get('cover', '')),
                    "preview":    track['preview'],
                    "popularite": track.get('rank', 0),
                    "deezer_id":  track['id'],
                    "bpm":        0,
                    "bonus_popularite": round((track.get('rank', 0) / 1_000_000) * 0.2, 3),
                })

            if chansons:
                with _catalogue_lock:
                    catalogue_deezer[genre] = chansons
                print(f"  ✓ {genre} : {len(chansons)} chansons")
            else:
                print(f"  ✗ {genre} : aucune chanson avec preview → fallback statique")

        except Exception as e:
            print(f"  ✗ {genre} : erreur Deezer ({e}) → fallback statique")

        time.sleep(0.3)  # respecter l'API Deezer

    _catalogue_pret = True
    print("✅ Catalogue Deezer prêt !")

def get_chansons(genre):
    """
    Retourne les chansons Deezer si disponibles, sinon le fallback statique.
    """
    with _catalogue_lock:
        if genre in catalogue_deezer:
            return catalogue_deezer[genre]
    return catalogue_statique.get(genre, {}).get('chansons', [])

def get_catalogue_complet():
    """
    Retourne le catalogue complet (Deezer ou statique) pour tous les genres.
    Utilisé pour passer au template.
    """
    resultat = {}
    for genre in genres:
        chansons = get_chansons(genre)
        # Limiter à 10 chansons max par genre pour le template
        resultat[genre] = chansons[:10]
    return resultat

# ═══════════════════════════════════════════════════
# LANCEMENT DU CHARGEMENT EN ARRIÈRE-PLAN
# ═══════════════════════════════════════════════════
_thread_catalogue = threading.Thread(target=charger_catalogue_deezer, daemon=True)
_thread_catalogue.start()

# ═══════════════════════════════════════════════════
# SESSION
# ═══════════════════════════════════════════════════
def init_session():
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
# ALGORITHME UCB1 + EPSILON ADAPTATIF
# ═══════════════════════════════════════════════════
def epsilon_adaptatif(likes_count):
    return max(0.05, 0.40 - likes_count * 0.018)

def ucb_score(likes, propositions, total, c=1.5):
    scores = []
    for i in range(len(propositions)):
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

    if likes_count == 0:
        scores    = ucb_score(likes, propositions, total)
        max_s     = max(scores)
        candidats = [i for i, s in enumerate(scores) if s == max_s]
        return random.choice(candidats)

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
    genre    = genres[genre_idx]
    chansons = get_chansons(genre)
    chanson  = random.choice(chansons)
    popularite = chanson.get('popularite', 0)
    chanson['bonus_popularite'] = round((popularite / 1_000_000) * 0.2, 3) if popularite > 0 else 0.0
    return chanson

def formater_scores(likes, propositions, total):
    scores = ucb_score(likes, propositions, total)
    return [round(s, 3) if s != float('inf') else '∞' for s in scores]

def construire_reponse(ucb, genre_idx, chanson):
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
        # Catalogue complet pour mettre à jour la playlist côté client
        'catalogue':    get_catalogue_complet(),
        'catalogue_pret': _catalogue_pret,
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
        # Catalogue complet passé au template
        catalogue=get_catalogue_complet(),
        catalogue_pret=_catalogue_pret,
    )

@app.route('/aimer', methods=['POST'])
def aimer():
    init_session()
    ucb       = session['ucb']
    genre_idx = ucb['genre_actuel']
    chanson   = ucb.get('chanson_actuelle', {})

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

@app.route('/catalogue', methods=['GET'])
def voir_catalogue():
    """Route pour récupérer le catalogue Deezer actuel (polling côté client)."""
    return jsonify({
        'catalogue': get_catalogue_complet(),
        'pret':      _catalogue_pret,
    })

@app.route('/memoire', methods=['GET'])
def voir_memoire():
    memoire = charger_memoire()
    if not memoire:
        return jsonify({'message': 'Aucune memoire enregistree.'})
    return jsonify(memoire)

if __name__ == '__main__':
    app.run(debug=True)