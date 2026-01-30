"""Language detection logic."""
import os
import locale
from typing import Optional


def detect_language(
    cli_lang: Optional[str] = None,
    config_lang: Optional[str] = None
) -> str:
    """
    Detect the appropriate language to use.

    Priority order:
    1. CLI argument (--lang)
    2. Environment variable (FLOW_LANG)
    3. Config file setting
    4. System locale
    5. Default (English)

    Args:
        cli_lang: Language specified via CLI argument
        config_lang: Language from workflow.yaml config

    Returns:
        Language code ('en' or 'ko')
    """
    # 1. CLI argument takes highest priority
    if cli_lang:
        return _normalize_lang(cli_lang)

    # 2. Environment variable
    env_lang = os.environ.get('FLOW_LANG')
    if env_lang:
        return _normalize_lang(env_lang)

    # 3. Config file setting
    if config_lang:
        return _normalize_lang(config_lang)

    # 4. System locale detection
    try:
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            if system_locale.startswith('ko'):
                return 'ko'
            # Add more locale mappings as needed
    except (ValueError, TypeError):
        pass

    # 5. Default to English
    return 'en'


def _normalize_lang(lang: str) -> str:
    """
    Normalize language code to supported values.

    Args:
        lang: Input language code (e.g., 'ko', 'ko_KR', 'korean', 'en', 'en_US')

    Returns:
        Normalized code ('en' or 'ko')
    """
    lang = lang.lower().strip()

    # Korean variants
    if lang in ('ko', 'kor', 'korean', 'ko_kr', 'ko-kr'):
        return 'ko'

    # English variants
    if lang in ('en', 'eng', 'english', 'en_us', 'en-us', 'en_gb', 'en-gb'):
        return 'en'

    # Default to English for unknown
    return 'en'
