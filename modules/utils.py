import io
import re
import unicodedata
from gtts import gTTS
import speech_recognition as sr

def normalize_text(text):
    if not text: return ""
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())

def get_audio_bytes(text, lang='pt', tld='pt'):
    try:
        tts = gTTS(text=text, lang=lang, tld=tld)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

def recognize_speech_from_audio(audio_file_bytes):
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_bytes) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language='pt-PT')
    except: return "[Incompréhensible]"

# --- MOTEUR DE CONJUGAISON ---
PRONOUNS = ["Eu", "Tu", "Ele/Ela/Você", "Nós", "Eles/Elas/Vocês"]

def conjugate_verb(verb_data, tense_key, pronoun_idx):
    if verb_data["type"] == "irregular":
        return verb_data["conjugations"][tense_key][pronoun_idx]
    
    verb = verb_data["infinitive"]
    root = verb[:-2]
    group = verb_data["group"]
    
    # Terminaisons pour tous les temps réguliers
    endings = {
        "AR": {
            "presente": ["o", "as", "a", "amos", "am"],
            "preterito_perfeito": ["ei", "aste", "ou", "amos", "aram"],
            "preterito_imperfeito": ["ava", "avas", "ava", "ávamos", "avam"],
            "futuro": ["arei", "arás", "ará", "aremos", "arão"],
            "condicional": ["aria", "arias", "aria", "aríamos", "ariam"],
            "subjuntivo_presente": ["e", "es", "e", "emos", "em"],
            "subjuntivo_imperfeito": ["asse", "asses", "asse", "ássemos", "assem"],
            "subjuntivo_futuro": ["ar", "ares", "ar", "armos", "arem"]
        },
        "ER": {
            "presente": ["o", "es", "e", "emos", "em"],
            "preterito_perfeito": ["i", "este", "eu", "emos", "eram"],
            "preterito_imperfeito": ["ia", "ias", "ia", "íamos", "iam"],
            "futuro": ["erei", "erás", "erá", "eremos", "erão"],
            "condicional": ["eria", "erias", "eria", "eríamos", "eriam"],
            "subjuntivo_presente": ["a", "as", "a", "amos", "am"],
            "subjuntivo_imperfeito": ["esse", "esses", "esse", "êssemos", "essem"],
            "subjuntivo_futuro": ["er", "eres", "er", "ermos", "erem"]
        },
        "IR": {
            "presente": ["o", "es", "e", "imos", "em"],
            "preterito_perfeito": ["i", "iste", "iu", "imos", "iram"],
            "preterito_imperfeito": ["ia", "ias", "ia", "íamos", "iam"],
            "futuro": ["irei", "irás", "irá", "iremos", "irão"],
            "condicional": ["iria", "irias", "iria", "iríamos", "iriam"],
            "subjuntivo_presente": ["a", "as", "a", "amos", "am"],
            "subjuntivo_imperfeito": ["isse", "isses", "isse", "íssemos", "issem"],
            "subjuntivo_futuro": ["ir", "ires", "ir", "irmos", "irem"]
        }
    }
    
    return root + endings[group][tense_key][pronoun_idx]