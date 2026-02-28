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
from github import Github, Auth # <-- Ajout de Auth ici

# --- CONFIGURATION ---
st.set_page_config(page_title="LingoClone", page_icon="🦉", layout="centered")

# --- CODE D'ACCÈS (Récupéré depuis les Secrets Streamlit) ---
ACCESS_PIN = st.secrets.get("MY_PIN", "1234")

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
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.title("🦉 Bienvenue sur LingoClone")
    st.write("Veuillez entrer votre code PIN pour accéder à vos révisions.")
    
    pin_input = st.text_input("Code PIN", type="password", max_chars=4, help="Entrez les 4 chiffres")
    
    if pin_input:
        if pin_input == str(ACCESS_PIN):
            st.session_state.authenticated = True
            st.success("Accès autorisé ! Chargement...")
            st.rerun()
        elif len(pin_input) == 4:
            st.error("Code PIN incorrect.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()


# =====================================================================
# --- LE RESTE DU CODE S'EXÉCUTE UNIQUEMENT SI AUTHENTIFIÉ ---
# =====================================================================

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

# --- LOGIQUE BASE DE DONNÉES (CLOUD & LOCAL) ---
def load_db():
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            # CORRECTION : Nouvelle méthode d'authentification PyGithub
            auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
            g = Github(auth=auth)
            repo = g.get_repo(st.secrets["REPO_NAME"])
            file_content = repo.get_contents(DB_PATH)
            data = json.loads(file_content.decoded_content.decode("utf-8"))
            if "vocabulary" in data:
                for c in data["vocabulary"]:
                    if "category" not in c: c["category"] = "Général"
                    if "score" not in c["srs_data"]: c["srs_data"]["score"] = c["srs_data"].get("box_level", 0)
                    if "score_apprentissage" not in c["srs_data"]: c["srs_data"]["score_apprentissage"] = 0
                    if "next_review_date_apprentissage" not in c["srs_data"]: c["srs_data"]["next_review_date_apprentissage"] = c["srs_data"].get("next_review_date", datetime.now().isoformat())
            return data
        except Exception as e:
            pass 
    
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "vocabulary" in data:
                    for c in data["vocabulary"]:
                        if "category" not in c: c["category"] = "Général"
                        if "score" not in c["srs_data"]: c["srs_data"]["score"] = c["srs_data"].get("box_level", 0)
                        if "score_apprentissage" not in c["srs_data"]: c["srs_data"]["score_apprentissage"] = 0
                        if "next_review_date_apprentissage" not in c["srs_data"]: c["srs_data"]["next_review_date_apprentissage"] = c["srs_data"].get("next_review_date", datetime.now().isoformat())
                return data
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

if "ex_type" not in st.session_state: st.session_state.ex_type = "flash"
if "options" not in st.session_state: st.session_state.options = []
if "pt_audio" not in st.session_state: st.session_state.pt_audio = None

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

def set_dont_know():
    st.session_state.is_correct = False
    st.session_state.has_failed = True
    st.session_state.user_input_val = "[Je ne sais pas]"
    st.session_state.answer_checked = True

def retry_oral():
    st.session_state.answer_checked = False
    st.session_state.retry_counter += 1
    st.session_state.user_input_val = ""

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
            
            # Algorithme de répétition espacée
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

# Bouton de sauvegarde Cloud (Seulement si GitHub configuré)
if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
    # CORRECTION : Remplacement de use_container_width par width="stretch"
    if st.sidebar.button("☁️ Sauvegarder ma progression", type="primary", width="stretch"):
        try:
            with st.spinner("Sauvegarde sur le cloud en cours..."):
                # CORRECTION : Nouvelle méthode d'authentification PyGithub
                auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
                g = Github(auth=auth)
                repo = g.get_repo(st.secrets["REPO_NAME"])
                try:
                    contents = repo.get_contents(DB_PATH)
                    repo.update_file(contents.path, "Mise à jour progression LingoClone", json.dumps(st.session_state.db, indent=4, ensure_ascii=False), contents.sha)
                except:
                    repo.create_file(DB_PATH, "Création base de données", json.dumps(st.session_state.db, indent=4, ensure_ascii=False))
            st.sidebar.success("Progression sauvegardée ! ✅")
        except Exception as e:
            st.sidebar.error("Erreur de sauvegarde. Vérifiez vos clés GitHub.")

st.sidebar.divider()
menu = st.sidebar.radio("Navigation", ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️", "Dictionnaires 📖", "Bibliothèque", "Paramètres"])

if menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"] and len(st.session_state.play_queue) > 0 and st.session_state.current_step < len(st.session_state.play_queue):
    st.sidebar.divider()
    st.sidebar.button("🛑 Quitter la session", on_click=quit_session, width="stretch", type="primary")

# --- PAGES ---
if menu == "Paramètres":
    st.header("⚙️ Configuration")
    list_name = st.text_input("Nom de la liste / Catégorie", value="Général")
    uploaded_file = st.file_uploader("Importer Excel (Col 1: PT, Col 2: FR)", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        added = 0
        for _, row in df.iterrows():
            if not pd.isna(row.iloc[0]) and not pd.isna(row.iloc[1]):
                target_word = str(row.iloc[0]).strip()
                primary_word = str(row.iloc[1]).strip()
                if target_word and primary_word and not any(i['term_target'] == target_word for i in st.session_state.db["vocabulary"]):
                    st.session_state.db["vocabulary"].append({
                        "id": str(uuid.uuid4()), "category": list_name.strip(), 
                        "term_target": target_word, "term_primary": primary_word, 
                        "srs_data": {"score": 0, "score_apprentissage": 0, "next_review_date": datetime.now().isoformat(), "next_review_date_apprentissage": datetime.now().isoformat()}
                    })
                    added += 1
        save_db(st.session_state.db)
        st.success(f"✅ {added} mots importés dans '{list_name}' !")
        st.rerun()

    st.divider()
    if st.button("🔄 Forcer une révision (Tout réinitialiser à maintenant)"):
        for c in st.session_state.db["vocabulary"]:
            c["srs_data"]["next_review_date"] = datetime.now().isoformat()
            c["srs_data"]["next_review_date_apprentissage"] = datetime.now().isoformat()
        save_db(st.session_state.db)
        quit_session()
        st.success("Dates réinitialisées !")

    if st.button("🗑️ Vider TOUTE la base de données", type="secondary"): 
        st.session_state.db = {"vocabulary": []}; save_db(st.session_state.db); st.rerun()

elif menu == "Dictionnaires 📖":
    st.header("📖 Dictionnaires en ligne")
    st.write("Ouvrez le dictionnaire complet pour vos recherches :")
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("🌐 Ouvrir Lexilogos (Français ↔️ Portugais)", "https://www.lexilogos.com/frances_lingua_dicionario.htm", width="stretch")

elif menu == "Bibliothèque":
    st.header("📚 Liste de mots")
    if st.session_state.db["vocabulary"]:
        st.dataframe(pd.DataFrame([{"Liste": c.get("category", "Général"), "Portugais": c["term_target"], "Français": c["term_primary"], "Score Quiz": c["srs_data"].get("score", 0)} for c in st.session_state.db["vocabulary"]]), use_container_width=True) # use_container_width est encore valide pour st.dataframe
    else:
        st.info("Votre bibliothèque est vide.")

elif menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"]:
    
    if len(st.session_state.play_queue) == 0 or st.session_state.current_step >= len(st.session_state.play_queue):
        st.title("Prêt à étudier ? 🚀")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📚 Listes à inclure :**")
                btn_col1, btn_col2 = st.columns(2)
                btn_col1.button("Tout cocher", on_click=select_all_cats, width="stretch")
                btn_col2.button("Tout décocher", on_click=deselect_all_cats, width="stretch")
                st.multiselect("Sélection", options=ALL_CATEGORIES, key="multiselect_cats", label_visibility="collapsed")
                
                valid_count = len([c for c in st.session_state.db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats])
                if st.session_state.nb_mots_limit > max(1, valid_count): st.session_state.nb_mots_limit = max(1, valid_count)
                st.number_input(f"🔢 Limite de mots (Mode Libre)", min_value=1, max_value=max(1, valid_count), key="nb_mots_limit")
            
            with c2:
                if menu == "Expression Orale 🎙️":
                    st.info("🗣️ En mode Oral, vous traduisez du Français vers le Portugais.")
                    st.session_state.direction_choice = "Français ➡️ Portugais"
                else:
                    st.radio("🔄 Sens", ["Aléatoire", "Français ➡️ Portugais", "Portugais ➡️ Français"], key="direction_choice")
                if menu == "Entraînement (Quiz)":
                    st.radio("📝 Type", ["Mixte", "Quiz Écrit", "QCM"], key="exo_choice")
        
        st.divider()
        if not st.session_state.multiselect_cats: st.warning("⚠️ Sélectionnez au moins une liste.")
        elif valid_count == 0: st.warning("⚠️ Les listes sélectionnées sont vides.")
        else:
            col_srs, col_libre, col_infini = st.columns(3)
            with col_srs: st.button("LANCER (SRS) 📚", on_click=generate_session, args=("srs", menu), width="stretch", type="primary")
            with col_libre: st.button("SÉRIE LIBRE 🎯", on_click=generate_session, args=("libre", menu), width="stretch")
            with col_infini: st.button("MODE INFINI ♾️", on_click=generate_session, args=("infini", menu), width="stretch")

    else:
        card = st.session_state.play_queue[st.session_state.current_step]

        if not st.session_state.exercise_initialized:
            show_pt = st.session_state.active_direction == "Portugais ➡️ Français" if st.session_state.active_direction != "Aléatoire" else random.choice([True, False])
            st.session_state.current_question = card["term_target"] if show_pt else card["term_primary"]
            st.session_state.current_answer = card["term_primary"] if show_pt else card["term_target"]
            st.session_state.pt_audio = get_audio_bytes(card["term_target"], lang='pt', tld='pt')

            if st.session_state.active_exo == "Mixte": st.session_state.ex_type = random.choice(["ecrit", "qcm"])
            elif st.session_state.active_exo == "Quiz Écrit": st.session_state.ex_type = "ecrit"
            else: st.session_state.ex_type = "qcm"

            if st.session_state.ex_type == "qcm" and menu == "Entraînement (Quiz)":
                others = [c["term_primary"] if show_pt else c["term_target"] for c in st.session_state.db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats and c["id"] != card["id"]]
                st.session_state.options = random.sample(others, min(len(others), 3)) + [st.session_state.current_answer]
                random.shuffle(st.session_state.options)

            st.session_state.exercise_initialized = True

        score_disp = card['srs_data'].get('score_apprentissage', 0) if menu == "Apprentissage (Quizlet)" else card['srs_data'].get('score', 0)
        
        if st.session_state.session_mode == "infini":
            st.caption(f"🔥 **Infini** — Mot {st.session_state.current_step + 1} | Cat: {card.get('category', 'Général')} | Score: {score_disp}")
        else:
            st.progress(st.session_state.current_step / len(st.session_state.play_queue))
            st.caption(f"Mot {st.session_state.current_step + 1} / {len(st.session_state.play_queue)} | Cat: {card.get('category', 'Général')} | Score: {score_disp}")
        
        # --- MODES DE JEU ---
        if menu == "Apprentissage (Quizlet)":
            txt = st.session_state.current_answer if st.session_state.is_flipped else st.session_state.current_question
            st.markdown(f'<div class="flashcard" style="background-color:{"#f0f8ff" if st.session_state.is_flipped else "#ffffff"}; display:flex; align-items:center; justify-content:center; border-radius:15px; border:2px solid #e0e0e0; margin-bottom:20px;"><h1 style="color:#333; text-align:center; margin:0;">{txt}</h1></div>', unsafe_allow_html=True)
            if st.session_state.pt_audio: st.audio(st.session_state.pt_audio, format="audio/mp3")
            if not st.session_state.is_flipped:
                if st.button("🔄 Tourner", width="stretch"): st.session_state.is_flipped = True; st.rerun()
            else:
                if st.button("🔄 Voir la question", width="stretch"): st.session_state.is_flipped = False; st.rerun()
                st.divider()
                st.markdown("<p style='text-align: center; font-weight: bold;'>Avez-vous trouvé ?</p>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.button("❌ À revoir", on_click=next_question, args=(card["id"], False, menu), width="stretch")
                c2.button("✅ Acquis", on_click=next_question, args=(card["id"], True, menu), width="stretch", type="primary")

        elif menu == "Entraînement (Quiz)":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-radius:15px; border-left:10px solid {DUOLINGO_GREEN}; margin-bottom:20px;"><p style="color:#666; margin:0; font-weight:bold;">Traduisez ceci :</p><h2 class="question-title" style="margin:0; color:#333;">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if card["term_target"] == st.session_state.current_question and st.session_state.pt_audio and not st.session_state.answer_checked: st.audio(st.session_state.pt_audio, format="audio/mp3")

            if not st.session_state.answer_checked:
                if st.session_state.ex_type == "qcm":
                    for o in st.session_state.options:
                        if st.button(o, width="stretch"):
                            st.session_state.is_correct = (o == st.session_state.current_answer)
                            if not st.session_state.is_correct: st.session_state.has_failed = True
                            st.session_state.user_input_val = o; st.session_state.answer_checked = True; st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🤷 Je ne sais pas", width="stretch"): set_dont_know(); st.rerun()
                else:
                    user_t = st.text_input("Votre traduction").strip()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("VÉRIFIER", width="stretch", type="primary"):
                            if user_t:
                                is_cor = (normalize_text(user_t) == normalize_text(st.session_state.current_answer))
                                st.session_state.is_correct = is_cor
                                if not is_cor: st.session_state.has_failed = True
                                st.session_state.user_input_val = user_t; st.session_state.answer_checked = True; st.rerun()
                            else: st.warning("Veuillez écrire une réponse.")
                    with c2:
                        if st.button("🤷 Je ne sais pas", width="stretch"): set_dont_know(); st.rerun()
            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Correct !\nLa réponse est bien : **{st.session_state.current_answer}**")
                    if card["term_target"] == st.session_state.current_answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, menu), type="primary", width="stretch")
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]": st.info(f"### 💡 Réponse :\nLa traduction de **{question}** est : **{st.session_state.current_answer}**")
                    else: st.error(f"### ❌ Oups !\nVous avez répondu : *{st.session_state.user_input_val}*\nBonne réponse : **{st.session_state.current_answer}**")
                    if card["term_target"] == st.session_state.current_answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], False, menu), type="primary", width="stretch")

        elif menu == "Expression Orale 🎙️":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-radius:15px; border-left:10px solid {ORAL_ORANGE}; margin-bottom:20px;"><p style="color:#666; margin:0; font-weight:bold;">Traduisez à voix haute :</p><h2 class="question-title" style="margin:0; color:#333;">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if not st.session_state.answer_checked:
                audio_v = st.audio_input("Parlez ici", key=f"mic_{st.session_state.current_step}_{st.session_state.retry_counter}")
                if audio_v:
                    with st.spinner("Analyse..."):
                        txt = recognize_speech_from_audio(audio_v)
                        if not txt or txt.startswith("["): st.error(f"Mal entendu ({txt}). Répétez ?")
                        else:
                            st.session_state.user_input_val = txt
                            is_cor = (normalize_text(txt) == normalize_text(st.session_state.current_answer))
                            st.session_state.is_correct = is_cor
                            if not is_cor: st.session_state.has_failed = True
                            st.session_state.answer_checked = True; st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🤷 Je ne sais pas", width="stretch"): set_dont_know(); st.rerun()
            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Parfait !\nJ'ai entendu : **{st.session_state.user_input_val}**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, "Entraînement (Quiz)"), type="primary", width="stretch")
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]": st.info(f"### 💡 Réponse :\n**{st.session_state.current_answer}**")
                    else: st.error(f"### ❌ Presque !\nJ'ai entendu : *{st.session_state.user_input_val}*\nIl fallait dire : **{st.session_state.current_answer}**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    c1, c2 = st.columns(2)
                    c1.button("🔄 RÉESSAYER", on_click=retry_oral, width="stretch")
                    c2.button("CONTINUER ➡️", on_click=next_question, args=(card["id"], False, "Entraînement (Quiz)"), type="primary", width="stretch")
