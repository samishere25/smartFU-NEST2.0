"""
Multilingual Translation Service
Uses Mistral AI for accurate pharmaceutical/medical question translation.
Supports 20+ languages with caching for performance.
"""

import logging
import json
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Supported Languages ──────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": {"name": "English",     "native": "English",      "flag": "🇬🇧"},
    "hi": {"name": "Hindi",       "native": "हिन्दी",        "flag": "🇮🇳"},
    "es": {"name": "Spanish",     "native": "Español",      "flag": "🇪🇸"},
    "fr": {"name": "French",      "native": "Français",     "flag": "🇫🇷"},
    "de": {"name": "German",      "native": "Deutsch",      "flag": "🇩🇪"},
    "pt": {"name": "Portuguese",  "native": "Português",    "flag": "🇵🇹"},
    "ja": {"name": "Japanese",    "native": "日本語",        "flag": "🇯🇵"},
    "zh": {"name": "Chinese",     "native": "中文",          "flag": "🇨🇳"},
    "ko": {"name": "Korean",      "native": "한국어",        "flag": "🇰🇷"},
    "ar": {"name": "Arabic",      "native": "العربية",      "flag": "🇸🇦"},
    "ru": {"name": "Russian",     "native": "Русский",      "flag": "🇷🇺"},
    "it": {"name": "Italian",     "native": "Italiano",     "flag": "🇮🇹"},
    "nl": {"name": "Dutch",       "native": "Nederlands",   "flag": "🇳🇱"},
    "tr": {"name": "Turkish",     "native": "Türkçe",       "flag": "🇹🇷"},
    "pl": {"name": "Polish",      "native": "Polski",       "flag": "🇵🇱"},
    "sv": {"name": "Swedish",     "native": "Svenska",      "flag": "🇸🇪"},
    "th": {"name": "Thai",        "native": "ไทย",          "flag": "🇹🇭"},
    "vi": {"name": "Vietnamese",  "native": "Tiếng Việt",   "flag": "🇻🇳"},
    "id": {"name": "Indonesian",  "native": "Bahasa Indonesia", "flag": "🇮🇩"},
    "bn": {"name": "Bengali",     "native": "বাংলা",        "flag": "🇧🇩"},
    "ta": {"name": "Tamil",       "native": "தமிழ்",        "flag": "🇮🇳"},
    "te": {"name": "Telugu",      "native": "తెలుగు",       "flag": "🇮🇳"},
    "mr": {"name": "Marathi",     "native": "मराठी",        "flag": "🇮🇳"},
    "gu": {"name": "Gujarati",    "native": "ગુજરાતી",      "flag": "🇮🇳"},
    "ur": {"name": "Urdu",        "native": "اردو",         "flag": "🇵🇰"},
}

# ── In-memory translation cache ──────────────────────────────────
_translation_cache: Dict[str, str] = {}


def _cache_key(text: str, target_lang: str) -> str:
    """Generate a cache key for a translation."""
    return f"{target_lang}::{text[:200]}"


def get_supported_languages() -> List[Dict]:
    """Return list of supported languages for the frontend dropdown."""
    return [
        {
            "code": code,
            "name": info["name"],
            "native": info["native"],
            "flag": info["flag"],
        }
        for code, info in SUPPORTED_LANGUAGES.items()
    ]


def translate_text(text: str, target_lang: str, context: str = "pharmacovigilance") -> str:
    """
    Translate a single text string to the target language using Mistral AI.

    Args:
        text: The text to translate
        target_lang: Target language code (e.g., 'hi', 'es', 'fr')
        context: Domain context for accurate translation

    Returns:
        Translated text string
    """
    if not text or not text.strip():
        return text

    # No translation needed for English
    if target_lang == "en":
        return text

    # Check language is supported
    if target_lang not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language '{target_lang}', returning original text")
        return text

    # Check cache
    key = _cache_key(text, target_lang)
    if key in _translation_cache:
        return _translation_cache[key]

    target_name = SUPPORTED_LANGUAGES[target_lang]["name"]

    try:
        from app.agents.gemini_client import get_gemini_client
        client = get_gemini_client()

        system_prompt = (
            f"You are a medical/pharmacovigilance translation expert. "
            f"Translate the following text accurately into {target_name}. "
            f"This is in the context of {context} — adverse event reporting and patient safety follow-up. "
            f"Keep medical/drug terminology precise. "
            f"Return ONLY the translated text, nothing else. No quotes, no explanation."
        )

        result = client.generate(system_prompt=system_prompt, user_prompt=text)
        translated = result.strip().strip('"').strip("'")

        # Cache it
        _translation_cache[key] = translated
        logger.info(f"🌐 Translated to {target_lang}: '{text[:50]}' → '{translated[:50]}'")
        return translated

    except Exception as e:
        logger.error(f"Translation failed for '{text[:40]}' → {target_lang}: {e}")
        return text  # Return original on failure


def translate_question(question_text: str, target_lang: str) -> str:
    """Translate a follow-up question to the target language."""
    return translate_text(
        text=question_text,
        target_lang=target_lang,
        context="pharmacovigilance adverse event follow-up question for a reporter"
    )


def translate_options(options: List[Dict], target_lang: str) -> List[Dict]:
    """Translate select/dropdown option labels."""
    if not options or target_lang == "en":
        return options

    translated = []
    for opt in options:
        if isinstance(opt, dict):
            new_opt = dict(opt)
            label = opt.get("label", opt.get("value", ""))
            new_opt["label"] = translate_text(label, target_lang, "medical form option")
            # Keep original value untranslated (it's the data key)
            translated.append(new_opt)
        elif isinstance(opt, str):
            translated.append(translate_text(opt, target_lang, "medical form option"))
        else:
            translated.append(opt)
    return translated


def get_ui_strings(lang: str) -> Dict[str, str]:
    """
    Return UI strings (placeholders, buttons, labels) in the given language.
    Uses a static map for common strings + Mistral for the rest.
    """
    # Base English strings
    base = {
        "submit_button": "Submit & Continue",
        "submitting": "Submitting...",
        "enter_number": "Enter a number...",
        "type_answer": "Type your answer...",
        "select_date": "Select a date",
        "completion_title": "Follow-up information complete.",
        "completion_message": "Thank you for providing this information. It helps protect patient safety and meet regulatory compliance requirements.",
        "your_responses": "Your Responses",
        "questions_answered": "questions answered",
        "close_window": "You may now close this window.",
        "loading": "Loading follow-up information...",
        "encrypted": "Encrypted & audit-logged",
        "data_completeness": "Data Completeness",
        "verified": "Verified",
        "select_language": "Select your preferred language",
        "language_subtitle": "Thank you for helping us ensure patient safety. We have a few questions about the reported case.",
        "retry": "Retry",
        "error_title": "Error Loading Follow-Up",
    }

    if lang == "en":
        return base

    # Try translating all UI strings in one batch via Mistral
    try:
        from app.agents.gemini_client import get_gemini_client
        client = get_gemini_client()

        target_name = SUPPORTED_LANGUAGES.get(lang, {}).get("name", lang)
        prompt = (
            f"Translate all these UI strings into {target_name} for a pharmacovigilance follow-up form. "
            f"Return a valid JSON object with the same keys. "
            f"Only translate the values, keep the keys in English. "
            f"Return ONLY the JSON, no markdown, no explanation.\n\n"
            f"{json.dumps(base, ensure_ascii=False)}"
        )

        result = client.generate(
            system_prompt="You are a UI localization expert for medical software. Return only valid JSON.",
            user_prompt=prompt
        )

        # Parse JSON
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        translated_strings = json.loads(cleaned)

        # Cache individual strings
        for k, v in translated_strings.items():
            cache_k = _cache_key(base[k], lang)
            _translation_cache[cache_k] = v

        logger.info(f"🌐 Translated {len(translated_strings)} UI strings to {lang}")
        return translated_strings

    except Exception as e:
        logger.error(f"Batch UI translation failed for {lang}: {e}")
        return base
