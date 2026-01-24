"""
cli/i18n/__init__.py - Internationalization (i18n) Module

Provides translation support for the CLI.
Korean (ko) is the default language, with English (en) as an option.

Architecture:
    - Messages are organized by namespace (common, ec2, rds, etc.)
    - Translation function t() supports format string interpolation
    - Language is passed via ExecutionContext.lang for thread-safety

Usage:
    from cli.i18n import t, set_lang, get_lang

    # Basic translation
    print(t("common.auth_failed"))  # "Authentication failed" or "인증에 실패했습니다"

    # With interpolation
    print(t("common.found_items", count=5))  # "Found 5 items"

    # Get localized text based on language
    set_lang("en")
    print(t("ec2.unused_eip"))  # "Unused EIP Detection"
"""

from __future__ import annotations

import contextlib
from contextvars import ContextVar
from typing import Any

# Default language context (fallback when ctx.lang not available)
_current_lang: ContextVar[str] = ContextVar("lang", default="ko")

# Supported languages
SUPPORTED_LANGS = ("ko", "en")
DEFAULT_LANG = "ko"


def get_lang() -> str:
    """Get current language from context variable."""
    return _current_lang.get()


def set_lang(lang: str) -> None:
    """Set current language in context variable.

    Args:
        lang: Language code ("ko" or "en")
    """
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    _current_lang.set(lang)


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """Translate a message key to the current language.

    Args:
        key: Message key in namespace.key format (e.g., "common.auth_failed")
        lang: Optional language override. If not provided, uses context variable.
        **kwargs: Format string arguments for interpolation

    Returns:
        Translated string, or key if translation not found

    Examples:
        >>> t("common.select_profile")
        "AWS 프로필을 선택하세요"  # when lang="ko"

        >>> t("common.found_items", count=5)
        "5개 항목 발견"  # when lang="ko"

        >>> t("common.found_items", lang="en", count=5)
        "Found 5 items"
    """
    from cli.i18n.messages import MESSAGES

    if lang is None:
        lang = get_lang()

    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    # Look up the message
    msg_dict = MESSAGES.get(key)
    if msg_dict is None:
        # Key not found, return key as-is
        return key

    # Get the translation for the specified language
    text = msg_dict.get(lang)
    if text is None:
        # Fallback to Korean if English not available
        text = msg_dict.get(DEFAULT_LANG, key)

    # Apply format string interpolation if kwargs provided
    if kwargs:
        with contextlib.suppress(KeyError, ValueError):
            text = text.format(**kwargs)

    return text


def get_text(ko: str, en: str, lang: str | None = None) -> str:
    """Get text based on language without using message registry.

    Useful for inline translations where registering a key is overkill.

    Args:
        ko: Korean text
        en: English text
        lang: Optional language override

    Returns:
        Text in the specified language

    Example:
        >>> get_text("저장됨", "Saved", lang="en")
        "Saved"
    """
    if lang is None:
        lang = get_lang()
    return en if lang == "en" else ko


__all__ = [
    "t",
    "get_text",
    "get_lang",
    "set_lang",
    "SUPPORTED_LANGS",
    "DEFAULT_LANG",
]
