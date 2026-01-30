"""Internationalization support for workflow-tool."""
from typing import Dict, Optional
import yaml
import os


class I18n:
    """Singleton class for internationalization."""

    _instance: Optional['I18n'] = None
    _messages: Dict[str, Dict] = {}
    _current_lang: str = "en"

    def __new__(cls) -> 'I18n':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'I18n':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
        cls._messages = {}
        cls._current_lang = "en"

    def get_language(self) -> str:
        """Get current language."""
        return self._current_lang

    def set_language(self, lang: str) -> None:
        """Set the current language and load messages."""
        self._current_lang = lang
        self._load_messages(lang)

    def _load_messages(self, lang: str) -> None:
        """Load message catalog for a language."""
        if lang in self._messages:
            return

        msg_path = os.path.join(
            os.path.dirname(__file__),
            f"messages/{lang}.yaml"
        )

        if os.path.exists(msg_path):
            with open(msg_path, 'r', encoding='utf-8') as f:
                self._messages[lang] = yaml.safe_load(f) or {}
        else:
            # Fallback to English if language file not found
            if lang != "en":
                self._load_messages("en")
                self._messages[lang] = self._messages.get("en", {})
            else:
                self._messages[lang] = {}

    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.

        Args:
            key: Dot-separated key path (e.g., 'help.status.description')
            **kwargs: Format arguments for the message

        Returns:
            Translated string, or the key itself if not found
        """
        # Ensure messages are loaded
        if self._current_lang not in self._messages:
            self._load_messages(self._current_lang)

        # Navigate the nested dict
        keys = key.split('.')
        value = self._messages.get(self._current_lang, {})

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, {})
            else:
                return key  # Key not found, return original

        if isinstance(value, str):
            try:
                return value.format(**kwargs) if kwargs else value
            except KeyError:
                return value
        return key  # Not a string, return original key


def t(key: str, **kwargs) -> str:
    """
    Convenience function for translation.

    Args:
        key: Dot-separated key path
        **kwargs: Format arguments

    Returns:
        Translated string
    """
    return I18n.get_instance().t(key, **kwargs)


def set_language(lang: str) -> None:
    """Set the current language."""
    I18n.get_instance().set_language(lang)


def get_language() -> str:
    """Get the current language."""
    return I18n.get_instance().get_language()
