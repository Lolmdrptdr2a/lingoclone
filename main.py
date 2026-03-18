import streamlit as st
import database
import modules.views as views


# --- CONFIGURATION ---
st.set_page_config(page_title="LingoClone", page_icon="🦉", layout="centered")
ACCESS_PIN = st.secrets.get("MY_PIN", "1234")

# --- AUTHENTIFICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🦉 Bienvenue sur LingoClone")
    pin_input = st.text_input("Code PIN", type="password", max_chars=4)
    if pin_input == str(ACCESS_PIN):
        st.session_state.authenticated = True
        st.rerun()
    elif len(pin_input) == 4:
        st.error("Code PIN incorrect.")
    st.stop()

# --- INITIALISATION GLOBALE ---
if "db" not in st.session_state: 
    st.session_state.db = database.load_vocab_db()
if "current_menu" not in st.session_state: 
    st.session_state.current_menu = "Accueil"
if "play_queue" not in st.session_state: 
    st.session_state.play_queue = []

# --- BARRE LATÉRALE ---
st.sidebar.title("🦉 LingoClone")

menu_options = ["Accueil", "Apprentissage (Quizlet)", "Entraînement (Quiz)", "Expression Orale 🎙️", "Conjugaison ✍️", "Dictionnaires 📖", "Bibliothèque", "Paramètres"]
selected_menu = st.sidebar.radio("Navigation", menu_options, index=menu_options.index(st.session_state.current_menu))

if selected_menu != st.session_state.current_menu:
    st.session_state.current_menu = selected_menu
    st.rerun()

if st.sidebar.button("☁️ Sauvegarder ma progression", type="primary", use_container_width=True):
    with st.spinner("Sauvegarde..."):
        if database.sync_to_github(st.session_state.db):
            st.sidebar.success("✅ Sauvegardé !")
        else:
            st.sidebar.error("❌ Erreur de sauvegarde.")

# --- ROUTAGE DES PAGES ---
menu = st.session_state.current_menu

if menu == "Accueil":
    views.render_home()
elif menu == "Paramètres":
    views.render_settings()
elif menu == "Bibliothèque":
    views.render_library()
elif menu == "Conjugaison ✍️":
    views.render_conjugation()
elif menu == "Dictionnaires 📖":
    st.link_button("🌐 Ouvrir Lexilogos", "https://www.lexilogos.com/frances_lingua_dicionario.htm", use_container_width=True)
else:
    views.render_exercise(menu)
