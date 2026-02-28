import streamlit as st
import pandas as pd
import json
import os
import uuid
import random
import io
import re
import unicodedata
from datetime import datetime, timedelta
from gtts import gTTS
import speech_recognition as sr
from github import Github

# --- CONFIGURATION ---
st.set_page_config(page_title="LingoClone", page_icon="🦉", layout="centered")

# --- CODE D'ACCÈS (À modifier ici) ---
ACCESS_PIN = "0104" 

# --- INITIALISATION DE L'AUTHENTIFICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- FENÊTRE D'AUTHENTIFICATION ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
            .auth-container {
                text-align: center;
                padding: 50px;
                border-radius: 20px;
                background-color: #f8f9fa;
                border: 2px solid #58CC02;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.title("🦉 Bienvenue sur LingoClone")
    st.write("Veuillez entrer votre code PIN à 4 chiffres pour accéder à vos révisions.")
    
    pin_input = st.text_input("Code PIN", type="password", max_chars=4, help="Entrez les 4 chiffres")
    
    if pin_input:
        if pin_input == ACCESS_PIN:
            st.session_state.authenticated = True
            st.success("Accès autorisé ! Chargement...")
            st.rerun()
        elif len(pin_input) == 4:
            st.error("Code PIN incorrect.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # Arrête l'exécution ici tant que l'utilisateur n'est pas authentifié

# --- RESTE DU CODE (S'exécute uniquement si authentifié) ---

# --- CSS RESPONSIVE POUR MOBILE ---
st.markdown("""
<style>
    .flashcard { height: 300px; font-size: 3em; padding: 20px; }
    .question-card { padding: 30px; }
    .question-title { font-size: 2.5em; }
    @media (max-width: 768px) {
        .flashcard { height: 200px !important; font-size: 2em !important; padding: 10px !important; }
        .question-card { padding: 15px !important; }
        .question-title { font-size: 1.8em !important; }
        .stButton button { white-space: normal !important; word-wrap: break-word !important; min-height: auto !important; }
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = "vocab_db.json"
DUOLINGO_GREEN = "#58CC02"
QUIZLET_BLUE = "#4255FF"
ORAL_ORANGE = "#FF9600"

# --- UTILITAIRE TEXTE ---
def normalize_text(text):
    if not text: return ""
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())

# --- LOGIQUE BASE DE DONNÉES ---
def load_db():
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            file_content = repo.get_contents(DB_PATH)
            data = json.loads(file_content.decoded_content.decode("utf-8"))
            return data
        except Exception as e:
            pass
    
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"vocabulary": []}

def save_db(db):
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
    except:
        pass

# --- GÉNÉRATION AUDIO ---
def get_audio_bytes(text, lang='pt', tld='pt'):
    try:
        tts = gTTS(text=text, lang=lang, tld=tld)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

# --- RECONNAISSANCE VOCALE ---
def recognize_speech_from_audio(audio_file_bytes):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_bytes) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language='pt-PT')
    except: return "[Incompréhensible]"

# --- INITIALISATION STATE GLOBALE ---
if "db" not in st.session_state: st.session_state.db = load_db()
if "play_queue" not in st.session_state: st.session_state.play_queue = []
if "current_step" not in st.session_state: st.session_state.current_step = 0
if "exercise_initialized" not in st.session_state: st.session_state.exercise_initialized = False
if "answer_checked" not in st.session_state: st.session_state.answer_checked = False
if "is_correct" not in st.session_state: st.session_state.is_correct = False
if "user_input_val" not in st.session_state: st.session_state.user_input_val = ""
if "is_flipped" not in st.session_state: st.session_state.is_flipped = False
if "has_failed" not in st.session_state: st.session_state.has_failed = False
if "retry_counter" not in st.session_state: st.session_state.retry_counter = 0

# Filtres par défaut
ALL_CATEGORIES = sorted(list(set([c.get("category", "Général") for c in st.session_state.db["vocabulary"]])))
if "multiselect_cats" not in st.session_state: st.session_state.multiselect_cats = ALL_CATEGORIES
if "nb_mots_limit" not in st.session_state: st.session_state.nb_mots_limit = 20
if "direction_choice" not in st.session_state: st.session_state.direction_choice = "Aléatoire"
if "exo_choice" not in st.session_state: st.session_state.exo_choice = "Mixte"
if "active_direction" not in st.session_state: st.session_state.active_direction = "Aléatoire"
if "active_exo" not in st.session_state: st.session_state.active_exo = "Mixte"
if "session_mode" not in st.session_state: st.session_state.session_mode = "srs"

# --- FONCTIONS DE GESTION ---
def select_all_cats(): st.session_state.multiselect_cats = ALL_CATEGORIES
def deselect_all_cats(): st.session_state.multiselect_cats = []

def reset_exercise_state():
    st.session_state.exercise_initialized = False
    st.session_state.answer_checked = False
    st.session_state.is_flipped = False
    st.session_state.user_input_val = ""
    st.session_state.has_failed = False
    st.session_state.retry_counter = 0

def quit_session():
    st.session_state.play_queue = []
    st.session_state.current_step = 0
    reset_exercise_state()

def generate_session(mode_type, current_mode):
    st.session_state.session_mode = mode_type
    st.session_state.active_direction = st.session_state.direction_choice
    st.session_state.active_exo = st.session_state.exo_choice
    all_cards = st.session_state.db["vocabulary"]
    valid_cards = [c for c in all_cards if c.get("category", "Général") in st.session_state.multiselect_cats]
    if mode_type == "srs":
        now = datetime.now()
        key = "next_review_date_apprentissage" if current_mode == "Apprentissage (Quizlet)" else "next_review_date"
        valid_cards = [c for c in valid_cards if now >= datetime.fromisoformat(c["srs_data"].get(key, now.isoformat()))]
    if not valid_cards: return
    random.shuffle(valid_cards)
    st.session_state.play_queue = [random.choice(valid_cards)] if mode_type == "infini" else valid_cards[:st.session_state.nb_mots_limit]
    st.session_state.current_step = 0
    reset_exercise_state()

def next_question(card_id, success, current_mode):
    db = st.session_state.db
    for card in db["vocabulary"]:
        if card["id"] == card_id:
            s_key = "score_apprentissage" if current_mode == "Apprentissage (Quizlet)" else "score"
            d_key = "next_review_date_apprentissage" if current_mode == "Apprentissage (Quizlet)" else "next_review_date"
            card["srs_data"][s_key] = card["srs_data"].get(s_key, 0) + (1 if success else -1)
            score = card["srs_data"][s_key]
            days = {0:0, 1:1, 2:3, 3:7, 4:14}.get(score, 30 if score > 0 else 0)
            card["srs_data"][d_key] = (datetime.now() + timedelta(days=days)).isoformat()
            break
    save_db(db)
    if st.session_state.session_mode == "infini":
        valid = [c for c in db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats]
        if valid: st.session_state.play_queue.append(random.choice(valid))
    st.session_state.current_step += 1
    reset_exercise_state()

# --- BARRE LATÉRALE ---
st.sidebar.title("🦉 LingoClone")
if "GITHUB_TOKEN" in st.secrets:
    if st.sidebar.button("☁️ Sauvegarder ma progression", type="primary", use_container_width=True):
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(DB_PATH)
            repo.update_file(contents.path, "Sync LingoClone", json.dumps(st.session_state.db, indent=4, ensure_ascii=False), contents.sha)
            st.sidebar.success("Synchronisé !")
        except: st.sidebar.error("Erreur Sync")

st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️", "Dictionnaires 📖", "Bibliothèque", "Paramètres"])

if menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"] and st.session_state.play_queue:
    st.sidebar.button("🛑 Quitter", on_click=quit_session, use_container_width=True)

# --- PAGES ---
if menu == "Paramètres":
    st.header("⚙️ Configuration")
    list_name = st.text_input("Nom de la liste", value="Général")
    uploaded_file = st.file_uploader("Importer Excel", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        for _, row in df.iterrows():
            if not pd.isna(row.iloc[0]) and not any(i['term_target'] == str(row.iloc[0]) for i in st.session_state.db["vocabulary"]):
                st.session_state.db["vocabulary"].append({"id": str(uuid.uuid4()), "category": list_name.strip(), "term_target": str(row.iloc[0]).strip(), "term_primary": str(row.iloc[1]).strip(), "srs_data": {"score": 0, "score_apprentissage": 0, "next_review_date": datetime.now().isoformat(), "next_review_date_apprentissage": datetime.now().isoformat()}})
        save_db(st.session_state.db)
        st.success("Importé !")
    if st.button("🗑️ Vider la base"): st.session_state.db = {"vocabulary": []}; save_db(st.session_state.db); st.rerun()

elif menu == "Dictionnaires 📖":
    st.link_button("🌐 Ouvrir Lexilogos", "https://www.lexilogos.com/frances_lingua_dicionario.htm", use_container_width=True)

elif menu == "Bibliothèque":
    st.header("📚 Bibliothèque")
    if st.session_state.db["vocabulary"]:
        st.dataframe(pd.DataFrame([{"Liste": c["category"], "Portugais": c["term_target"], "Français": c["term_primary"], "Score Quiz": c["srs_data"]["score"]} for c in st.session_state.db["vocabulary"]]), use_container_width=True)

elif menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"]:
    if not st.session_state.play_queue or st.session_state.current_step >= len(st.session_state.play_queue):
        st.title("Prêt à étudier ?")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.button("Tout cocher", on_click=select_all_cats)
                st.button("Tout décocher", on_click=deselect_all_cats)
                st.multiselect("Listes", options=ALL_CATEGORIES, key="multiselect_cats")
                valid_count = len([c for c in st.session_state.db["vocabulary"] if c["category"] in st.session_state.multiselect_cats])
                st.number_input("Nombre de mots", min_value=1, max_value=max(1, valid_count), key="nb_mots_limit")
            with c2:
                if menu == "Expression Orale 🎙️": st.info("Français ➡️ Portugais (Oral)"); st.session_state.direction_choice = "Français ➡️ Portugais"
                else: st.radio("Sens", ["Aléatoire", "Français ➡️ Portugais", "Portugais ➡️ Français"], key="direction_choice")
                if menu == "Entraînement (Quiz)": st.radio("Type", ["Mixte", "Quiz Écrit", "QCM"], key="exo_choice")
        if st.session_state.multiselect_cats:
            col_a, col_b, col_c = st.columns(3)
            col_a.button("LANCER (SRS)", on_click=generate_session, args=("srs", menu), type="primary")
            col_b.button("LIBRE", on_click=generate_session, args=("libre", menu))
            col_c.button("INFINI", on_click=generate_session, args=("infini", menu))
    else:
        card = st.session_state.play_queue[st.session_state.current_step]
        if not st.session_state.exercise_initialized:
            show_pt = st.session_state.active_direction == "Portugais ➡️ Français" if st.session_state.active_direction != "Aléatoire" else random.choice([True, False])
            st.session_state.current_question = card["term_target"] if show_pt else card["term_primary"]
            st.session_state.current_answer = card["term_primary"] if show_pt else card["term_target"]
            st.session_state.pt_audio = get_audio_bytes(card["term_target"])
            if menu == "Entraînement (Quiz)":
                st.session_state.ex_type = random.choice(["ecrit", "qcm"]) if st.session_state.active_exo == "Mixte" else ("ecrit" if st.session_state.active_exo == "Quiz Écrit" else "qcm")
                if st.session_state.ex_type == "qcm":
                    others = [c["term_target"] if not show_pt else c["term_primary"] for c in st.session_state.db["vocabulary"] if c["id"] != card["id"]]
                    st.session_state.options = random.sample(others, min(len(others), 3)) + [st.session_state.current_answer]
                    random.shuffle(st.session_state.options)
            st.session_state.exercise_initialized = True

        if st.session_state.session_mode != "infini": st.progress(st.session_state.current_step / len(st.session_state.play_queue))
        
        # RENDU DES MODES
        if menu == "Apprentissage (Quizlet)":
            txt = st.session_state.current_answer if st.session_state.is_flipped else st.session_state.current_question
            st.markdown(f'<div class="flashcard" style="background-color:{"#f0f8ff" if st.session_state.is_flipped else "white"}; display:flex; align-items:center; justify-content:center; border-radius:15px; border:2px solid #e0e0e0; margin-bottom:20px;"><h1 style="text-align:center;">{txt}</h1></div>', unsafe_allow_html=True)
            if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
            if not st.session_state.is_flipped:
                if st.button("🔄 Tourner"): st.session_state.is_flipped = True; st.rerun()
            else:
                c1, c2 = st.columns(2)
                c1.button("❌ À revoir", on_click=next_question, args=(card["id"], False, menu))
                c2.button("✅ Acquis", on_click=next_question, args=(card["id"], True, menu), type="primary")

        elif menu == "Entraînement (Quiz)":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-radius:15px; border-left:10px solid #58CC02; margin-bottom:20px;"><h2 class="question-title">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if not st.session_state.answer_checked:
                if st.session_state.ex_type == "qcm":
                    for o in st.session_state.options:
                        if st.button(o, use_container_width=True): st.session_state.is_correct = (o == st.session_state.current_answer); st.session_state.user_input_val = o; st.session_state.answer_checked = True; st.rerun()
                else:
                    user_t = st.text_input("Traduction")
                    if st.button("Vérifier"): st.session_state.is_correct = (normalize_text(user_t) == normalize_text(st.session_state.current_answer)); st.session_state.user_input_val = user_t; st.session_state.answer_checked = True; st.rerun()
                if st.button("🤷 Je ne sais pas"): st.session_state.is_correct = False; st.session_state.user_input_val = "Inconnu"; st.session_state.answer_checked = True; st.rerun()
            else:
                if st.session_state.is_correct: st.success(f"Bravo ! C'était {st.session_state.current_answer}")
                else: st.error(f"Oups... C'était {st.session_state.current_answer}")
                st.button("Continuer", on_click=next_question, args=(card["id"], st.session_state.is_correct, menu))

        elif menu == "Expression Orale 🎙️":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-left:10px solid #FF9600; margin-bottom:20px;"><h2 class="question-title">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if not st.session_state.answer_checked:
                audio = st.audio_input("Parlez")
                if audio:
                    voice_txt = recognize_speech_from_audio(audio)
                    st.session_state.is_correct = (normalize_text(voice_txt) == normalize_text(st.session_state.current_answer))
                    st.session_state.user_input_val = voice_txt; st.session_state.answer_checked = True; st.rerun()
            else:
                if st.session_state.is_correct: st.success(f"Entendu : {st.session_state.user_input_val}")
                else: st.error(f"J'ai entendu : {st.session_state.user_input_val}. Il fallait dire : {st.session_state.current_answer}")
                if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                st.button("Continuer", on_click=next_question, args=(card["id"], st.session_state.is_correct, "Quiz"))
