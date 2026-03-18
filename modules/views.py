import streamlit as st
import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
import modules.utils as utils
import modules.database as database

def render_home():
    st.title("🏠 Bienvenue sur LingoClone")
    st.write("Prêt à perfectionner ton portugais ? Choisis une activité ci-dessous :")
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🧠 Mémorisation")
        st.button("📚 Apprentissage (Quizlet)", on_click=lambda: st.session_state.update(current_menu="Apprentissage (Quizlet)", play_queue=[]), use_container_width=True)
        st.button("📝 Entraînement (Quiz)", on_click=lambda: st.session_state.update(current_menu="Entraînement (Quiz)", play_queue=[]), use_container_width=True)
    with c2:
        st.markdown("### 🗣️ Pratique & Grammaire")
        st.button("🎙️ Expression Orale", on_click=lambda: st.session_state.update(current_menu="Expression Orale 🎙️", play_queue=[]), use_container_width=True)
        st.button("✍️ Conjugaison", on_click=lambda: st.session_state.update(current_menu="Conjugaison ✍️", play_queue=[]), use_container_width=True)

def render_conjugation():
    st.title("✍️ Grammaire & Conjugaison")
    verbs_db = database.load_verbs_db().get("verbs", [])
    if not verbs_db:
        st.error("Impossible de charger verbs_db.json.")
        return

    # On définit les temps disponibles une seule fois pour les deux onglets
    tenses_map = {
        "Présent": "presente", "Passé (Pretérito Perfeito)": "preterito_perfeito", 
        "Imparfait": "preterito_imperfeito", "Futur": "futuro", "Conditionnel": "condicional",
        "Subjonctif Présent": "subjuntivo_presente"
    }

    tabs = st.tabs(["🎯 S'entraîner (Mini-Test)", "📖 Tableaux de Conjugaison"])
    
    # ONGLET 1 : MINI-TEST
    with tabs[0]:
        st.subheader("Mini-Test de Conjugaison")
        
        tense_display = st.selectbox("Choisis le temps :", list(tenses_map.keys()), key="test_tense")
        tense_key = tenses_map[tense_display]
        
        if not st.session_state.get("conj_test_init", False):
            verb_data = random.choice(verbs_db)
            pronoun_idx = random.randint(0, 4)
            st.session_state.conj_current_verb = verb_data
            st.session_state.conj_current_pronoun_idx = pronoun_idx
            st.session_state.conj_current_answer = utils.conjugate_verb(verb_data, tense_key, pronoun_idx)
            st.session_state.conj_test_init = True
            st.session_state.conj_checked = False

        verb_data = st.session_state.conj_current_verb
        p_idx = st.session_state.conj_current_pronoun_idx
        
        st.markdown(f"### Conjugue le verbe **{verb_data['infinitive'].upper()}** ({verb_data['fr']}) au **{tense_display}** :")
        st.write(f"**{utils.PRONOUNS[p_idx]}** ... ?")
        
        if not st.session_state.conj_checked:
            user_conj = st.text_input("Ta réponse :", key="conj_input").strip()
            if st.button("Vérifier", type="primary", use_container_width=True):
                if user_conj:
                    st.session_state.conj_is_correct = (utils.normalize_text(user_conj) == utils.normalize_text(st.session_state.conj_current_answer))
                    st.session_state.conj_user_val = user_conj
                    st.session_state.conj_checked = True
                    st.rerun()
                else:
                    st.warning("Veuillez écrire une réponse.")
        else:
            if st.session_state.conj_is_correct:
                st.success(f"🎉 Correct ! **{utils.PRONOUNS[p_idx]} {st.session_state.conj_current_answer}**")
            else:
                st.error(f"❌ Oups ! Tu as écrit *{st.session_state.conj_user_val}*.\n\nBonne réponse : **{utils.PRONOUNS[p_idx]} {st.session_state.conj_current_answer}**")
            
            if st.button("Continuer", type="primary", use_container_width=True):
                st.session_state.conj_test_init = False
                st.rerun()

    # ONGLET 2 : CONSULTATION DES TABLEAUX
    with tabs[1]:
        st.subheader("Recherche de Conjugaisons")
        
        c1, c2 = st.columns(2)
        with c1:
            # On trie les verbes par ordre alphabétique pour faciliter la recherche
            verb_dict = {v["infinitive"]: v for v in verbs_db}
            selected_inf = st.selectbox("Choisis un verbe :", sorted(list(verb_dict.keys())))
            selected_verb = verb_dict[selected_inf]
            
        with c2:
            consult_tense_display = st.selectbox("Choisis le temps :", list(tenses_map.keys()), key="consult_tense")
            consult_tense_key = tenses_map[consult_tense_display]
            
        # Affichage des infos du verbe
        type_str = "Régulier" if selected_verb["type"] == "regular" else "Irrégulier"
        st.markdown(f"**Verbe :** {selected_verb['infinitive'].capitalize()} ({selected_verb['fr']}) — *{type_str}*")
        
        # Génération du tableau
        conjugation_list = []
        for i, pronoun in enumerate(utils.PRONOUNS):
            try:
                conj_form = utils.conjugate_verb(selected_verb, consult_tense_key, i)
                conjugation_list.append({"Pronom": pronoun, "Conjugaison": conj_form})
            except Exception:
                conjugation_list.append({"Pronom": pronoun, "Conjugaison": "-"})
                
        # On affiche le tableau proprement via Streamlit et Pandas
        st.dataframe(pd.DataFrame(conjugation_list), use_container_width=True, hide_index=True)

def render_settings():
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
        database.save_vocab_db(st.session_state.db)
        st.success(f"✅ {added} mots importés !")
        st.rerun()

    if st.button("🗑️ Vider TOUTE la base de données", type="secondary"): 
        st.session_state.db = {"vocabulary": []}
        database.save_vocab_db(st.session_state.db)
        st.rerun()

def render_library():
    st.header("📚 Bibliothèque")
    if st.session_state.db["vocabulary"]:
        st.dataframe(pd.DataFrame([{"Liste": c.get("category", "Général"), "Portugais": c["term_target"], "Français": c["term_primary"], "Score Quiz": c["srs_data"].get("score", 0)} for c in st.session_state.db["vocabulary"]]), use_container_width=True)
    else:
        st.info("Votre bibliothèque est vide.")


# --- FONCTIONS DE GESTION DES EXERCICES ---
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

def generate_session(mode_type, menu_name):
    st.session_state.session_mode = mode_type
    st.session_state.active_direction = st.session_state.direction_choice
    st.session_state.active_exo = st.session_state.exo_choice
    
    all_cards = st.session_state.db["vocabulary"]
    valid_cards = [c for c in all_cards if c.get("category", "Général") in st.session_state.multiselect_cats]
    
    if mode_type == "srs":
        now = datetime.now()
        key = "next_review_date_apprentissage" if menu_name == "Apprentissage (Quizlet)" else "next_review_date"
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
            
    database.save_vocab_db(db)
    
    if st.session_state.session_mode == "infini":
        valid = [c for c in db["vocabulary"] if c.get("category", "Général") in st.session_state.multiselect_cats]
        if valid: st.session_state.play_queue.append(random.choice(valid))
        
    st.session_state.current_step += 1
    reset_exercise_state()

# --- VUE EXERCICE PRINCIPALE ---
def render_exercise(menu):
    # Initialisation de la sélection des catégories si vide
    all_categories = sorted(list(set([c.get("category", "Général") for c in st.session_state.db["vocabulary"]])))
    if "multiselect_cats" not in st.session_state: st.session_state.multiselect_cats = all_categories
    if "nb_mots_limit" not in st.session_state: st.session_state.nb_mots_limit = 20
    if "direction_choice" not in st.session_state: st.session_state.direction_choice = "Aléatoire"
    if "exo_choice" not in st.session_state: st.session_state.exo_choice = "Mixte"

    if len(st.session_state.play_queue) == 0 or st.session_state.current_step >= len(st.session_state.play_queue):
        st.title(f"Prêt pour : {menu.split(' ')[0]} ? 🚀")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**📚 Listes à inclure :**")
                btn_col1, btn_col2 = st.columns(2)
                btn_col1.button("Tout cocher", on_click=lambda: st.session_state.update(multiselect_cats=all_categories), use_container_width=True)
                btn_col2.button("Tout décocher", on_click=lambda: st.session_state.update(multiselect_cats=[]), use_container_width=True)
                st.multiselect("Sélection", options=all_categories, key="multiselect_cats", label_visibility="collapsed")
                
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
            with col_srs: st.button("LANCER (SRS) 📚", on_click=generate_session, args=("srs", menu), use_container_width=True, type="primary")
            with col_libre: st.button("SÉRIE LIBRE 🎯", on_click=generate_session, args=("libre", menu), use_container_width=True)
            with col_infini: st.button("MODE INFINI ♾️", on_click=generate_session, args=("infini", menu), use_container_width=True)

    else:
        card = st.session_state.play_queue[st.session_state.current_step]

        if not st.session_state.exercise_initialized:
            show_pt = st.session_state.active_direction == "Portugais ➡️ Français" if st.session_state.active_direction != "Aléatoire" else random.choice([True, False])
            st.session_state.current_question = card["term_target"] if show_pt else card["term_primary"]
            st.session_state.current_answer = card["term_primary"] if show_pt else card["term_target"]
            st.session_state.pt_audio = utils.get_audio_bytes(card["term_target"], lang='pt', tld='pt')

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
                if st.button("🔄 Tourner", use_container_width=True): st.session_state.is_flipped = True; st.rerun()
            else:
                if st.button("🔄 Voir la question", use_container_width=True): st.session_state.is_flipped = False; st.rerun()
                st.divider()
                st.markdown("<p style='text-align: center; font-weight: bold;'>Avez-vous trouvé ?</p>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.button("❌ À revoir", on_click=next_question, args=(card["id"], False, menu), use_container_width=True)
                c2.button("✅ Acquis", on_click=next_question, args=(card["id"], True, menu), use_container_width=True, type="primary")

        elif menu == "Entraînement (Quiz)":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-radius:15px; border-left:10px solid #58CC02; margin-bottom:20px;"><p style="color:#666; margin:0; font-weight:bold;">Traduisez ceci :</p><h2 class="question-title" style="margin:0; color:#333;">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if card["term_target"] == st.session_state.current_question and st.session_state.pt_audio and not st.session_state.answer_checked: st.audio(st.session_state.pt_audio, format="audio/mp3")

            if not st.session_state.answer_checked:
                if st.session_state.ex_type == "qcm":
                    for o in st.session_state.options:
                        if st.button(o, use_container_width=True):
                            st.session_state.is_correct = (o == st.session_state.current_answer)
                            if not st.session_state.is_correct: st.session_state.has_failed = True
                            st.session_state.user_input_val = o; st.session_state.answer_checked = True; st.rerun()
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🤷 Je ne sais pas", use_container_width=True): set_dont_know(); st.rerun()
                else:
                    user_t = st.text_input("Votre traduction").strip()
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("VÉRIFIER", use_container_width=True, type="primary"):
                            if user_t:
                                is_cor = (utils.normalize_text(user_t) == utils.normalize_text(st.session_state.current_answer))
                                st.session_state.is_correct = is_cor
                                if not is_cor: st.session_state.has_failed = True
                                st.session_state.user_input_val = user_t; st.session_state.answer_checked = True; st.rerun()
                            else: st.warning("Veuillez écrire une réponse.")
                    with c2:
                        if st.button("🤷 Je ne sais pas", use_container_width=True): set_dont_know(); st.rerun()
            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Correct !\nLa réponse est bien : **{st.session_state.current_answer}**")
                    if card["term_target"] == st.session_state.current_answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, menu), type="primary", use_container_width=True)
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]": 
                        st.info(f"### 💡 Réponse :\nLa traduction de **{st.session_state.current_question}** est : **{st.session_state.current_answer}**")
                        st.button("CONTINUER", on_click=next_question, args=(card["id"], False, menu), type="primary", use_container_width=True)
                    else: 
                        st.error(f"### ❌ Oups !\nVous avez répondu : *{st.session_state.user_input_val}*\nBonne réponse : **{st.session_state.current_answer}**")
                        if card["term_target"] == st.session_state.current_answer and st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                        
                        c1, c2 = st.columns(2)
                        c1.button("✅ Ma réponse était juste", on_click=next_question, args=(card["id"], not st.session_state.has_failed, menu), use_container_width=True)
                        c2.button("CONTINUER", on_click=next_question, args=(card["id"], False, menu), type="primary", use_container_width=True)

        elif menu == "Expression Orale 🎙️":
            st.markdown(f'<div class="question-card" style="background-color:#f8f9fa; border-radius:15px; border-left:10px solid #FF9600; margin-bottom:20px;"><p style="color:#666; margin:0; font-weight:bold;">Traduisez à voix haute :</p><h2 class="question-title" style="margin:0; color:#333;">{st.session_state.current_question}</h2></div>', unsafe_allow_html=True)
            if not st.session_state.answer_checked:
                audio_v = st.audio_input("Parlez ici", key=f"mic_{st.session_state.current_step}_{st.session_state.retry_counter}")
                if audio_v:
                    with st.spinner("Analyse..."):
                        txt = utils.recognize_speech_from_audio(audio_v)
                        if not txt or txt.startswith("["): st.error(f"Mal entendu ({txt}). Répétez ?")
                        else:
                            st.session_state.user_input_val = txt
                            is_cor = (utils.normalize_text(txt) == utils.normalize_text(st.session_state.current_answer))
                            st.session_state.is_correct = is_cor
                            if not is_cor: st.session_state.has_failed = True
                            st.session_state.answer_checked = True; st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🤷 Je ne sais pas", use_container_width=True): set_dont_know(); st.rerun()
            else:
                if st.session_state.is_correct:
                    st.success(f"### 🎉 Parfait !\nJ'ai entendu : **{st.session_state.user_input_val}**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    st.button("CONTINUER", on_click=next_question, args=(card["id"], not st.session_state.has_failed, "Entraînement (Quiz)"), type="primary", use_container_width=True)
                else:
                    if st.session_state.user_input_val == "[Je ne sais pas]": st.info(f"### 💡 Réponse :\n**{st.session_state.current_answer}**")
                    else: st.error(f"### ❌ Presque !\nJ'ai entendu : *{st.session_state.user_input_val}*\nIl fallait dire : **{st.session_state.current_answer}**")
                    if st.session_state.pt_audio: st.audio(st.session_state.pt_audio)
                    c1, c2 = st.columns(2)
                    c1.button("🔄 RÉESSAYER", on_click=retry_oral, use_container_width=True)
                    c2.button("CONTINUER ➡️", on_click=next_question, args=(card["id"], False, "Entraînement (Quiz)"), type="primary", use_container_width=True)