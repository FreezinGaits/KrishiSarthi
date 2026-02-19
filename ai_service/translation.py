# ai_service/translation.py
"""
Multilingual translation module for KrishiSarthi.
Supports Hindi, Hinglish, and English — auto-detects input language
and translates to/from English for the RAG pipeline.

Uses deep-translator (free Google Translate wrapper, no API key needed).
"""

import re
from deep_translator import GoogleTranslator


# ── Devanagari Unicode range ─────────────────────────────────
_DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')

# Common Hindi stop-words (used to detect Hinglish)
_HINDI_STOPWORDS = {
    "mera", "meri", "mere", "hai", "hain", "kya", "kaise", "kab",
    "kahan", "kyun", "kyu", "aur", "ka", "ki", "ke", "ko", "se",
    "mein", "par", "nahi", "nahin", "ho", "raha", "rahi", "rahe",
    "tha", "thi", "the", "hona", "karna", "wala", "wali", "wale",
    "bhi", "ye", "yeh", "wo", "woh", "iska", "iski", "iske",
    "uska", "uski", "uske", "sabse", "bahut", "accha", "achhi",
    "kuch", "sab", "ek", "do", "teen", "char", "panch",
    "lagana", "lagao", "dalna", "daalo", "bataiye", "batao",
    "kaisa", "kaisi", "kitna", "kitni", "kitne", "abhi",
    "pehle", "baad", "phir", "lekin", "agar", "toh", "to",
    "fasal", "khet", "paudha", "patta", "patte", "tamatar",
    "aloo", "pyaaz", "gehu", "dhan", "makka", "sarson",
    "rog", "bimari", "keeda", "keet", "dawai", "upay",
    "ilaj", "spray", "khad", "paani", "pani", "mitti",
}


def detect_language(text: str) -> str:
    """
    Detect language of user input.

    Returns:
        'hi'       — Hindi (primarily Devanagari script)
        'hinglish' — Hinglish (Hindi words written in Latin script)
        'en'       — English
    """
    if not text or not text.strip():
        return "en"

    text_stripped = text.strip()

    # Count Devanagari vs total characters (ignoring spaces/punctuation)
    alpha_chars = [c for c in text_stripped if c.isalpha()]
    if not alpha_chars:
        return "en"

    devanagari_count = len(_DEVANAGARI_RE.findall(text_stripped))
    devanagari_ratio = devanagari_count / len(alpha_chars)

    # If >30% Devanagari chars, it's Hindi
    if devanagari_ratio > 0.3:
        return "hi"

    # Check for Hinglish: Latin-script text with Hindi stop-words
    words = set(re.findall(r'[a-zA-Z]+', text_stripped.lower()))
    hindi_word_count = len(words & _HINDI_STOPWORDS)

    # If >=2 Hindi stop-words found in Latin script, treat as Hinglish
    if hindi_word_count >= 2:
        return "hinglish"

    return "en"


def translate_to_english(text: str, source_lang: str) -> str:
    """
    Translate user input to English for RAG retrieval.

    Args:
        text: User's original message
        source_lang: Detected language ('hi', 'hinglish', or 'en')

    Returns:
        English translation of the text (unchanged if already English)
    """
    if source_lang == "en":
        return text

    try:
        if source_lang == "hi":
            translated = GoogleTranslator(source='hi', target='en').translate(text)
        elif source_lang == "hinglish":
            # Hinglish is Latin-script Hindi — Google Translate handles auto-detect
            translated = GoogleTranslator(source='auto', target='en').translate(text)
        else:
            translated = GoogleTranslator(source='auto', target='en').translate(text)

        return translated or text
    except Exception as e:
        print(f"Translation to English failed: {e}")
        return text  # fallback: use original text


def translate_from_english(text: str, target_lang: str) -> str:
    """
    Translate LLM response from English back to the user's language.

    Args:
        text: English response from LLM
        target_lang: Target language ('hi', 'hinglish', or 'en')

    Returns:
        Translated text in the target language
    """
    if target_lang == "en":
        return text

    try:
        if target_lang == "hi":
            # Translate to Hindi (Devanagari script)
            translated = GoogleTranslator(source='en', target='hi').translate(text)
        elif target_lang == "hinglish":
            # For Hinglish: translate to Hindi, then we'll rely on the LLM prompt
            # to generate a mix. As a fallback, translate to Hindi.
            # Google Translate doesn't have a "Hinglish" target, so we return Hindi.
            translated = GoogleTranslator(source='en', target='hi').translate(text)
        else:
            translated = text

        return translated or text
    except Exception as e:
        print(f"Translation from English failed: {e}")
        return text  # fallback: return English text
