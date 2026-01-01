"""
Internationalization (i18n) module for UllageMaster.
Provides multi-language support (English, Turkish).
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Optional

# Current language
_current_lang: str = "en"
_translations: Dict[str, dict] = {}


def _get_i18n_dir() -> Path:
    """
    Get the i18n directory path.
    
    Supports both normal execution and PyInstaller frozen apps.
    For frozen apps, uses sys._MEIPASS to find bundled resources.
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as frozen executable - use _MEIPASS
        return Path(sys._MEIPASS) / 'i18n'
    else:
        # Running as normal Python script
        return Path(__file__).parent


def load_language(lang_code: str) -> bool:
    """
    Load a language file.
    
    Args:
        lang_code: Language code ('en' or 'tr')
        
    Returns:
        True if successful, False otherwise
    """
    global _current_lang, _translations
    
    lang_file = _get_i18n_dir() / f"{lang_code}.json"
    
    if not lang_file.exists():
        return False
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            _translations[lang_code] = json.load(f)
        _current_lang = lang_code
        return True
    except Exception as e:
        print(f"Error loading language file: {e}")
        return False


def get_text(key: str, section: Optional[str] = None) -> str:
    """
    Get translated text for a key.
    
    Args:
        key: Translation key (e.g., 'save' or 'menu.save')
        section: Optional section name (e.g., 'menu', 'grid')
        
    Returns:
        Translated text or the key if not found
    """
    global _current_lang, _translations
    
    # Load language if not loaded
    if _current_lang not in _translations:
        if not load_language(_current_lang):
            load_language('en')  # Fallback to English
    
    trans = _translations.get(_current_lang, {})
    
    # Handle dot notation in key
    if '.' in key:
        parts = key.split('.')
        result = trans
        for part in parts:
            if isinstance(result, dict):
                result = result.get(part, key)
            else:
                return key
        return result if isinstance(result, str) else key
    
    # Handle section parameter
    if section:
        section_data = trans.get(section, {})
        return section_data.get(key, key)
    
    # Search in root level
    return trans.get(key, key)


def t(key: str, section: Optional[str] = None) -> str:
    """Shorthand for get_text."""
    return get_text(key, section)


def get_current_language() -> str:
    """Get current language code."""
    return _current_lang


def set_language(lang_code: str) -> bool:
    """
    Set the current language.
    
    Args:
        lang_code: Language code ('en' or 'tr')
        
    Returns:
        True if successful
    """
    return load_language(lang_code)


def get_available_languages() -> Dict[str, str]:
    """
    Get list of available languages.
    
    Returns:
        Dictionary of {code: name}
    """
    return {
        'en': 'English',
        'tr': 'Türkçe'
    }


# Initialize with English
load_language('en')
