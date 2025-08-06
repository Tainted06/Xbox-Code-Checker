import json
import os
from typing import Dict, Any

class LocalizationManager:
    """Manages localization for the application"""

    def __init__(self, locales_dir: str = "src/locales", default_lang: str = "en"):
        self.locales_dir = locales_dir
        self.default_lang = default_lang
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.current_lang = default_lang
        self.load_translations()

    def load_translations(self) -> None:
        """Load all translation files from the locales directory"""
        if not os.path.exists(self.locales_dir):
            return

        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename.split(".")[0]
                filepath = os.path.join(self.locales_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)

    def set_language(self, lang_code: str) -> None:
        """Set the current language"""
        if lang_code in self.translations:
            self.current_lang = lang_code
        else:
            self.current_lang = self.default_lang

    def get(self, key: str, **kwargs) -> str:
        """
        Get a translated string for a given key.
        The key should be in the format 'section.key'.
        """
        try:
            keys = key.split(".")
            translation = self.translations.get(self.current_lang, {})
            for k in keys:
                translation = translation[k]

            if kwargs:
                return translation.format(**kwargs)
            return translation
        except KeyError:
            # Fallback to default language
            try:
                translation = self.translations.get(self.default_lang, {})
                for k in keys:
                    translation = translation[k]

                if kwargs:
                    return translation.format(**kwargs)
                return translation
            except KeyError:
                return key

    def get_available_languages(self) -> list[str]:
        """Get a list of available languages"""
        return list(self.translations.keys())

# Create a global instance of the localization manager
localization_manager = LocalizationManager()

def _(key: str, **kwargs) -> str:
    """Shorthand function for getting translations"""
    return localization_manager.get(key, **kwargs)
