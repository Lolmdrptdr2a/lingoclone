import streamlit as st
import json
import os
#from github import Github, Auth
from datetime import datetime

VOCAB_DB_PATH = "vocab_db.json"
VERBS_DB_PATH = "verbs_db.json"

def get_github_repo():
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        return g.get_repo(st.secrets["REPO_NAME"])
    return None

def load_vocab_db():
    repo = get_github_repo()
    if repo:
        try:
            file_content = repo.get_contents(VOCAB_DB_PATH)
            data = json.loads(file_content.decoded_content.decode("utf-8"))
            return _init_vocab_fields(data)
        except Exception:
            pass 
            
    if os.path.exists(VOCAB_DB_PATH):
        try:
            with open(VOCAB_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _init_vocab_fields(data)
        except:
            pass
    return {"vocabulary": []}

def _init_vocab_fields(data):
    if "vocabulary" in data:
        for c in data["vocabulary"]:
            if "category" not in c: c["category"] = "Général"
            if "score" not in c["srs_data"]: c["srs_data"]["score"] = c["srs_data"].get("box_level", 0)
            if "score_apprentissage" not in c["srs_data"]: c["srs_data"]["score_apprentissage"] = 0
            if "next_review_date_apprentissage" not in c["srs_data"]: 
                c["srs_data"]["next_review_date_apprentissage"] = c["srs_data"].get("next_review_date", datetime.now().isoformat())
    return data

def save_vocab_db(db):
    try:
        with open(VOCAB_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
    except:
        pass

def load_verbs_db():
    repo = get_github_repo()
    if repo:
        try:
            file_content = repo.get_contents(VERBS_DB_PATH)
            return json.loads(file_content.decoded_content.decode("utf-8"))
        except Exception:
            pass 
            
    if os.path.exists(VERBS_DB_PATH):
        try:
            with open(VERBS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"verbs": []}

def sync_to_github(db):
    repo = get_github_repo()
    if repo:
        try:
            contents = repo.get_contents(VOCAB_DB_PATH)
            repo.update_file(contents.path, "Mise à jour progression LingoClone", json.dumps(db, indent=4, ensure_ascii=False), contents.sha)
            return True
        except:
            repo.create_file(VOCAB_DB_PATH, "Création base de données", json.dumps(db, indent=4, ensure_ascii=False))
            return True
    return False
