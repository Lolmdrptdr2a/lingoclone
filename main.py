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
    # 1. Tentative de chargement depuis GitHub (si l'app est déployée)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
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
            st.warning("Chargement cloud échoué ou premier lancement. Utilisation locale.")
    
    # 2. Chargement local (si on est sur PC ou si GitHub n'est pas encore configuré)
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
    # Sauvegarde locale (mémoire temporaire du serveur pendant qu'on joue)
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
    except Exception as e:
        return None

# --- RECONNAISSANCE VOCALE ---
def recognize_speech_from_audio(audio_file_bytes):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_bytes) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language='pt-PT')
            return text
    except sr.UnknownValueError:
        return "[Incompréhensible]"
    except sr.RequestError:
        return "[Erreur de connexion à l'API vocale]"
    except Exception as e:
        return None

# --- INITIALISATION STATE GLOBALE ---
if "db" not in st.session_state: st.session_state.db = load_db()
if "play_queue" not in st.session_state: st.session_state.play_queue = []
if "current_step" not in st.session_state: st.session_state.current_step = 0
if "exercise_initialized" not in st.session_state: st.session_state.exercise_initialized = False
if "answer_checked" not in st.session_state: st.session_state.answer_checked = False
if "is_correct" not in st.session_state: st.session_state.is_correct = False
if "user_input_val" not in st.session_state: st.session_state.user_input_val = ""
if "is_flipped" not in st.session_state: st.session_state.is_flipped = False

if "ex_type" not in st.session_state: st.session_state.ex_type = "flash"
if "options" not in st.session_state: st.session_state.options = []
if "pt_audio" not in st.session_state: st.session_state.pt_audio = None

if "has_failed" not in st.session_state: st.session_state.has_failed = False
if "retry_counter" not in st.session_state: st.session_state.retry_counter = 0

# Variables de filtres par défaut
ALL_CATEGORIES = sorted(list(set([c.get("category", "Général") for c in st.session_state.db["vocabulary"]])))
if "multiselect_cats" not in st.session_state: st.session_state.multiselect_cats = ALL_CATEGORIES
if "nb_mots_limit" not in st.session_state: st.session_state.nb_mots_limit = 20
if "direction_choice" not in st.session_state: st.session_state.direction_choice = "Aléatoire"
if "exo_choice" not in st.session_state: st.session_state.exo_choice = "Mixte"

if "active_direction" not in st.session_state: st.session_state.active_direction = "Aléatoire"
if "active_exo" not in st.session_state: st.session_state.active_exo = "Mixte"
if "session_mode" not in st.session_state: st.session_state.session_mode = "srs"

# --- CALLBACKS & FONCTIONS DE GESTION ---
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

def generate_session(mode_type, current_mode="Entraînement (Quiz)"):
    st.session_state.session_mode = mode_type
    st.session_state.active_direction = st.session_state.direction_choice
    st.session_state.active_exo = st.session_state.exo_choice

    all_cards = st.session_state.db["vocabulary"]
    valid_cards = [c for c in all_cards if c.get("category", "Général") in st.session_state.multiselect_cats]
    
    if mode_type == "srs":
        now = datetime.now()
        if current_mode == "Apprentissage (Quizlet)":
            valid_cards = [c for c in valid_cards if now >= datetime.fromisoformat(c["srs_data"].get("next_review_date_apprentissage", now.isoformat()))]
        else:
            valid_cards = [c for c in valid_cards if now >= datetime.fromisoformat(c["srs_data"]["next_review_date"])]
        if not valid_cards:
            st.session_state.play_queue = []
            return

    if not valid_cards: return

    random.shuffle(valid_cards)
    
    if mode_type == "infini":
        st.session_state.play_queue = [random.choice(valid_cards)]
    else:
        st.session_state.play_queue = valid_cards[:st.session_state.nb_mots_limit]
        
    st.session_state.current_step = 0
    reset_exercise_state()

def next_question(card_id, success, current_mode):
    db = st.session_state.db
    for card in db["vocabulary"]:
        if card["id"] == card_id:
            if current_mode == "Apprentissage (Quizlet)":
                score_key = "score_apprentissage"
                date_key = "next_review_date_apprentissage"
            else:
                score_key = "score"
                date_key = "next_review_date"

            current_score = card["srs_data"].get(score_key, 0)
            if success: card["srs_data"][score_key] = current_score + 1
            else: card["srs_data"][score_key] = current_score - 1
            
            new_score = card["srs_data"][score_key]
            if new_score <= 0: days = 0
            elif new_score == 1: days = 1
            elif new_score == 2: days = 3
            elif new_score == 3: days = 7
            elif new_score == 4: days = 14
            else: days = 30
            
            card["srs_data"][date_key] = (datetime.now() + timedelta(days=days)).isoformat()
            break
            
    save_db(db)
    
    if st.session_state.session_mode == "infini":
        all_cards = st.session_state.db["vocabulary"]
        valid_cards = [c for c in all_cards if c.get("category", "Général") in st.session_state.multiselect_cats]
        if valid_cards:
            st.session_state.play_queue.append(random.choice(valid_cards))

    st.session_state.current_step += 1
    reset_exercise_state()

# --- INTERFACE BARRE LATÉRALE ---
st.sidebar.title("🦉 LingoClone")

# Bouton de sauvegarde Cloud (visible uniquement si les secrets Github sont configurés)
if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
    if st.sidebar.button("☁️ Sauvegarder ma progression", type="primary", use_container_width=True):
        try:
            with st.spinner("Sauvegarde sur le cloud en cours..."):
                g = Github(st.secrets["GITHUB_TOKEN"])
                repo = g.get_repo(st.secrets["REPO_NAME"])
                try:
                    contents = repo.get_contents(DB_PATH)
                    repo.update_file(contents.path, "Mise à jour progression LingoClone", json.dumps(st.session_state.db, indent=4, ensure_ascii=False), contents.sha)
                except:
                    repo.create_file(DB_PATH, "Création base de données LingoClone", json.dumps(st.session_state.db, indent=4, ensure_ascii=False))
            st.sidebar.success("Progression sauvegardée ! ✅")
        except Exception as e:
            st.sidebar.error("Erreur de sauvegarde. Vérifiez vos clés GitHub.")

st.sidebar.divider()

menu = st.sidebar.radio("Navigation", [
    "Apprentissage (Quizlet)", 
    "Entraînement (Quiz)", 
    "Expression Orale 🎙️",
    "Dictionnaires 📖",  
    "Bibliothèque", 
    "Paramètres"
])

if menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"]:
    if len(st.session_state.play_queue) > 0 and st.session_state.current_step < len(st.session_state.play_queue):
        st.sidebar.divider()
        st.sidebar.button("🛑 Quitter la session", on_click=quit_session, use_container_width=True, type="primary")

# --- PARAMÈTRES ---
if menu == "Paramètres":
    st.header("⚙️ Configuration")
    
    st.subheader("Importation Excel")
    list_name = st.text_input("Nom de la liste / Catégorie", value="Général")
    uploaded_file = st.file_uploader("Format : Colonne 1 (Portugais), Colonne 2 (Français)", type=["xlsx"])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        added = 0
        for _, row in df.iterrows():
            if pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]): continue
            target_word = str(row.iloc[0]).strip()
            primary_word = str(row.iloc[1]).strip()
            if not target_word or not primary_word: continue

            if not any(i['term_target'] == target_word for i in st.session_state.db["vocabulary"]):
                st.session_state.db["vocabulary"].append({
                    "id": str(uuid.uuid4()),
                    "category": list_name.strip(),
                    "term_target": target_word,
                    "term_primary": primary_word,
                    "srs_data": {
                        "score": 0, "score_apprentissage": 0,
                        "next_review_date": datetime.now().isoformat(),
                        "next_review_date_apprentissage": datetime.now().isoformat()
                    }
                })
                added += 1
        save_db(st.session_state.db)
        st.success(f"✅ {added} mots importés dans la liste '{list_name}' !")
        st.rerun()

    st.divider()
    if st.button("🔄 Forcer une révision (Tout réinitialiser à maintenant)"):
        for c in st.session_state.db["vocabulary"]:
            c["srs_data"]["next_review_date"] = datetime.now().isoformat()
            c["srs_data"]["next_review_date_apprentissage"] = datetime.now().isoformat()
        save_db(st.session_state.db)
        quit_session()
        st.success("Toutes les dates ont été réinitialisées !")

    if st.button("🗑️ Vider TOUTE la base de données", type="secondary"):
        st.session_state.db = {"vocabulary": []}
        save_db(st.session_state.db)
        st.warning("Base de données effacée.")
        st.rerun()

# --- DICTIONNAIRES ---
elif menu == "Dictionnaires 📖":
    st.header("📖 Dictionnaires en ligne")
    st.write("Ouvrez le dictionnaire complet pour vos recherches :")
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("🌐 Ouvrir Lexilogos (Français ↔️ Portugais)", "https://www.lexilogos.com/frances_lingua_dicionario.htm", use_container_width=True)

# --- BIBLIOTHÈQUE ---
elif menu == "Bibliothèque":
    st.header("📚 Liste de mots")
    if st.session_state.db["vocabulary"]:
        df_display = pd.DataFrame([
            {
                "Liste": c.get("category", "Général"), 
                "Portugais": c["term_target"], 
                "Français": c["term_primary"], 
                "Score Quiz": c["srs_data"].get("score", 0)
            } 
            for c in st.session_state.db["vocabulary"]
        ])
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("Votre bibliothèque est vide.")

# --- COMMUN AUX MODES D'ÉTUDE ---
elif menu in ["Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️"]:
    
    # HUB DE CHOIX
    if len(st.session_state.play_queue) == 0 or st.session_state.current_step >= len(st.session_state.play_queue):
        st.title("Prêt à étudier ? 🚀")
        st.markdown("### ⚙️ Filtres de la session")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📚 Listes à inclure :**")
                btn_col1, btn_col2 = st.columns(2)
                btn_col1.button("Tout cocher", on_click=select_all_cats, use_container_width=True)
                btn_col2.button("Tout décocher", on_click=deselect_all_cats, use_container_width=True)
                st.multiselect("Sélection des listes", options=ALL_CATEGORIES, key="multiselect_cats", label_visibility="collapsed")
                
                valid_count = len([c for c in st.session_state.db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats])
                max_val = max(1, valid_count)
                if st.session_state.nb_mots_limit > max_val: st.session_state.nb_mots_limit = max_val
                st.number_input(f"🔢 Limite (pour le mode Libre)", min_value=1, max_value=max_val, key="nb_mots_limit")
            
            with c2:
                if menu == "Expression Orale 🎙️":
                    st.info("🗣️ En mode Oral, vous devez traduire du Français vers le Portugais à haute voix.")
                    st.session_state.direction_choice = "Français ➡️ Portugais"
                else:
                    st.radio("🔄 Sens de traduction :", ["Aléatoire", "Français ➡️ Portugais", "Portugais ➡️ Français"], key="direction_choice")
                
                if menu == "Entraînement (Quiz)":
                    st.radio("📝 Type d'exercice :", ["Mixte", "Quiz Écrit", "QCM"], key="exo_choice")
        
        st.divider()

        if not st.session_state.multiselect_cats:
            st.warning("⚠️ Veuillez sélectionner au moins une liste pour commencer.")
        elif valid_count == 0:
            st.warning("⚠️ Les listes sélectionnées sont vides.")
        else:
            col_srs, col_libre, col_infini = st.columns(3)
            with col_srs: st.button("LANCER (SRS) 📚", on_click=generate_session, args=("srs", menu), use_container_width=True, type="primary")
            with col_libre: st.button("SÉRIE LIBRE 🎯", on_click=generate_session, args=("libre", menu), use_container_width=True)
            with col_infini: st.button("MODE INFINI ♾️", on_click=generate_session, args=("infini", menu), use_container_width=True)

    # SESSION EN COURS
    else:
        card = st.session_state.play_queue[st.session_state.current_step]

        if not st.session_state.exercise_initialized:
            if st.session_state.active_direction == "Français ➡️ Portugais": show_target = False
            elif st.session_state.active_direction == "Portugais ➡️ Français": show_target = True
            else: show_target = random.choice([True, False])

            st.session_state.current_question = card["term_target"] if show_target else card["term_primary"]
            st.session_state.current_answer = card["term_primary"] if show_target else card["term_target"]
            st.session_state.pt_audio = get_audio_bytes(card["term_target"], lang='pt', tld='pt')

            if st.session_state.active_exo == "Mixte": st.session_state.ex_type = random.choice(["ecrit", "qcm"])
            elif st.session_state.active_exo == "Quiz Écrit": st.session_state.ex_type = "ecrit"
            elif st.session_state.active_exo == "QCM": st.session_state.ex_type = "qcm"

            if st.session_state.ex_type == "qcm" and menu == "Entraînement (Quiz)":
                correct = st.session_state.current_answer
                all_opts = [c["term_primary"] if show_target else c["term_target"] 
                            for c in st.session_state.db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats]
                others = list(set([o for o in all_opts if o != correct]))
                st.session_state.options = random.sample(others, min(len(others), 3)) + [correct]
                random.shuffle(st.session_state.options)

            st.session_state.exercise_initialized = True

        current_score_display = card['srs_data'].get('score_apprentissage', 0) if menu == "Apprentissage (Quizlet)" else card['srs_data'].get('score', 0)
        
        if st.session_state.session_mode == "infini":
            st.caption(f"🔥 **Mode Infini** — Mot n° {st.session_state.current_step + 1}  |  Catégorie : {card.get('category', 'Général')} | Score Actuel : {current_score_display}")
        else:
            st.progress(st.session_state.current_step / len(st.session_state.play_queue))
            st.caption(f"Mot {st.session_state.current_step + 1} / {len(st.session_state.play_queue)}  —  Catégorie : {card.get('category', 'Général')} | Score Actuel : {current_score_display}")
        
        question = st.session_state.current_question
        answer = st.session_state.current_answer

        # --- MODE 1 : APPRENTISSAGE (QUIZLET) ---
        if menu == "Apprentissage (Quizlet)":
            st.markdown(f"<h3 style='text-align: center; color: {QUIZLET_BLUE};'>Mode Cartes Flash</h3>", unsafe_allow_html=True)
            display_text = answer if st.session_state.is_flipped else question
            bg_color = "#f0f8ff" if st.session_state.is_flipped else "#ffffff"
            
            st.markdown(f"""
                <div style="background-color: {bg_color}; height: 300px; display: flex; align-items: center; justify-content: center; 
                            border-radius: 15px; border: 2px solid #e0e0e0; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px;">
                    <h1 style="color: #333; text-align: center; font-size: 3em; margin: 0;">{display_text}</h1>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.pt_audio:
                st.markdown("<p style='text-align: center; color: #666; font-size: 0.9em; margin-bottom: 0;'>🔊 Prononciation portugaise :</p>", unsafe_allow_html=True)
                st.audio(st.session_state.pt_audio, format="audio/mp3")

            if not st.session_state.is_flipped:
                if st.button("🔄 Tourner la carte", use_container_width=True):
                    st.session_state.is_flipped = True
                    st.rerun()
            else:
                if st.button("🔄 Voir la question", use_container_width=True):
                    st.session_state.is_flipped = False
                    st.rerun()
                st.divider()
                st.markdown("<p style='text-align: center; font-weight: bold;'>Avez-vous trouvé ?</p>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.button("❌ À revoir", on_click=next_question, args=(card["id"], False, menu), use_container_width=True)
                c2.button("✅ Acquis", on_click=next_question, args=(card["id"], True, menu), use_container_width=True, type="primary")

        # --- MODE 2 : ENTRAÎNEMENT (DUOLINGO) ---
        elif menu == "Entraînement (Quiz)":
            st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 15px; border-left: 10px solid {DUOLINGO_GREEN}; margin-bottom: 20px;">
                    <p style="color: #666; margin: 0; font-weight: bold;">Traduisez ceci :</p>
                    <h2 style="margin: 0; color: #333; font-size: 2.5em;">{question}</h2>
                </div>
            """, unsafe_allow_html=True)

            if card["term_target"] == question and st.session_state.pt_audio and not st.session_state.answer_checked:
                st.audio(st.session_state.pt_audio, format="audio/mp3")

            if not st.session_state.answer_checked:
                if st.session_state.ex_type == "qcm":
                    for opt in st.session_state.options:
                        if st.button(opt, use_container_width=True):
                            st.session_state.is_correct = (opt == answer)
                            if not st.session_state.is_correct: st.session_state.has_failed = True
                            st.session_state.user_input_val = opt
                            st.session_state.answer_checked = True
                            st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🤷 Je ne sais pas", use_container_width=True):
                        set_dont_know()
                        st.rerun()

                elif st.session_state.ex_type == "ecrit":
                    user_text = st.text_input("Votre traduction :", key="written_input_field").strip()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("VÉRIFIER", use_container_width=True, type="primary"):
                            if user_text:
                                is_correct = (normalize_text(user_text) == normalize_text(answer))
                                st.session_state.is_correct = is_correct
                                if not is_correct: st.session_state.has_failed = True
                                st.session_state.user_input_val = user_text
                                st.session_state.answer_checked = True
                                st.rerun()
                            else:
                                st.warning("Veuillez écrire une réponse.")
                    with c2:
                        if st.button("🤷 Je ne sais pas", use_container_width=True):
                            set_dont_know()
                            st.rerun()

            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Correct !\nLa réponse est bien : **{answer}**")
                    if card["term_target"] == answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio, format="audio/mp3")
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, menu), type="primary", use_container_width=True)
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]":
                        st.info(f"### 💡 Voici la réponse :\nLa traduction de **{question}** est : **{answer}**")
                    else:
                        st.error(f"### ❌ Oups !\nVous avez répondu : *{st.session_state.user_input_val}*\n\nLa bonne réponse était : **{answer}**")
                    
                    if card["term_target"] == answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio, format="audio/mp3")
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], False, menu), type="primary", use_container_width=True)

        # --- MODE 3 : EXPRESSION ORALE ---
        elif menu == "Expression Orale 🎙️":
            st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 15px; border-left: 10px solid {ORAL_ORANGE}; margin-bottom: 20px;">
                    <p style="color: #666; margin: 0; font-weight: bold;">Traduisez à voix haute en portugais :</p>
                    <h2 style="margin: 0; color: #333; font-size: 2.5em;">{question}</h2>
                </div>
            """, unsafe_allow_html=True)

            if not st.session_state.answer_checked:
                st.info("💡 Cliquez sur le micro ci-dessous, parlez, puis arrêtez l'enregistrement.")
                
                mic_key = f"mic_input_{st.session_state.current_step}_{st.session_state.retry_counter}"
                audio_value = st.audio_input("Enregistrez votre réponse en portugais", key=mic_key)
                
                if audio_value:
                    with st.spinner("Analyse de votre voix..."):
                        transcription = recognize_speech_from_audio(audio_value)
                        if not transcription or transcription.startswith("["):
                            st.error(f"Je n'ai pas bien entendu ({transcription}). Pouvez-vous répéter ?")
                        else:
                            st.session_state.user_input_val = transcription
                            is_correct = (normalize_text(transcription) == normalize_text(answer))
                            st.session_state.is_correct = is_correct
                            if not is_correct: st.session_state.has_failed = True
                            st.session_state.answer_checked = True
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🤷 Je ne sais pas comment le prononcer", use_container_width=True):
                    set_dont_know()
                    st.rerun()

            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Parfait !\nJ'ai entendu : **{st.session_state.user_input_val}**")
                    st.markdown("🎧 **Réécouter la prononciation :**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio, format="audio/mp3")
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, "Entraînement (Quiz)"), type="primary", use_container_width=True)
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]":
                        st.info(f"### 💡 Voici la réponse :\nIl fallait dire : **{answer}**")
                    else:
                        st.error(f"### ❌ Presque !\nJ'ai entendu : *{st.session_state.user_input_val}*\nIl fallait dire : **{answer}**")
                    
                    st.markdown("🎧 **Écoutez la prononciation et réessayez pour vous améliorer !**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio, format="audio/mp3")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.button("🔄 RÉESSAYER", on_click=retry_oral, use_container_width=True)
                    with c2:
                        st.button("CONTINUER ➡️", on_click=next_question, args=(card["id"], False, "Entraînement (Quiz)"), type="primary", use_container_width=True)
