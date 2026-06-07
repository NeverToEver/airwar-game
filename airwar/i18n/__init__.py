"""Lightweight i18n (internationalization) infrastructure.

Proof-of-concept translator that loads JSON locale files and exposes a
``t(key, **kwargs)`` API with fallback to the key itself when a translation
is missing. A process-wide singleton is available via :func:`get_translator`.

Locale files live under :mod:`airwar.locales` and are named
``{locale}.json`` (e.g. ``zh_CN.json``, ``en_US.json``). The default locale
is ``zh_CN`` to preserve the historically hardcoded Chinese UI strings.
"""

from __future__ import annotations

import json
import logging
import os
from threading import RLock
from typing import Any

_logger = logging.getLogger(__name__)

DEFAULT_LOCALE = "zh_CN"
_FALLBACK_LOCALE = "zh_CN"

# Locales directory: <airwar_pkg>/locales
_LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales")


class Translator:
    """Lightweight JSON-backed translator.

    The translator is intentionally minimal: load translations for a locale
    from a JSON file, look up keys via :meth:`t`, and fall back to the key
    itself (with a warning) when a key is missing.
    """

    def __init__(self, default_locale: str = DEFAULT_LOCALE, locales_dir: str | None = None) -> None:
        self._default_locale = default_locale
        self._locales_dir = locales_dir or _LOCALES_DIR
        self._locale = default_locale
        self._catalogs: dict[str, dict[str, str]] = {}
        self._lock = RLock()
        # Eagerly load the default locale so first-frame t() calls are O(1).
        self._load_locale(default_locale)

    def t(self, key: str, **kwargs: Any) -> str:
        """Return the translated string for ``key`` in the current locale.

        Missing keys log a warning and return the key itself so the UI never
        crashes on incomplete translations. ``**kwargs`` are forwarded to
        :py:meth:`str.format` for positional/positional parameter support
        (e.g. ``t("score_label", score=123)`` -> ``"得分: 123"``).
        """
        with self._lock:
            catalog = self._catalogs.get(self._locale) or self._catalogs.get(_FALLBACK_LOCALE) or {}

        value = catalog.get(key)
        if value is None:
            _logger.warning(
                "Missing translation for key=%r in locale=%r; falling back to key",
                key,
                self._locale,
            )
            value = key

        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, IndexError, ValueError) as exc:
                _logger.warning("Failed to format key=%r with kwargs=%r: %s", key, kwargs, exc)
                return value
        return value

    def set_locale(self, locale: str) -> None:
        """Switch the active locale, loading its catalog on demand.

        Unknown locales log a warning; the active locale is left unchanged
        so the UI keeps rendering existing translations.
        """
        with self._lock:
            if locale == self._locale:
                return
            self._load_locale(locale)
            self._locale = locale

    def get_locale(self) -> str:
        """Return the active locale code (e.g. ``"zh_CN"``)."""
        return self._locale

    def has_key(self, key: str) -> bool:
        """Return ``True`` if ``key`` has a translation in the current locale."""
        with self._lock:
            catalog = self._catalogs.get(self._locale) or {}
            return key in catalog

    def _load_locale(self, locale: str) -> None:
        """Load and cache ``{locale}.json`` from the locales directory.

        Missing files or malformed JSON log a warning and the translator
        silently treats the locale as empty (fallback rules still apply).
        """
        if locale in self._catalogs:
            return
        path = os.path.join(self._locales_dir, f"{locale}.json")
        if not os.path.isfile(path):
            _logger.warning("Locale file not found: %s", path)
            self._catalogs[locale] = {}
            return
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning("Failed to load locale file %s: %s", path, exc)
            self._catalogs[locale] = {}
            return
        if not isinstance(data, dict):
            _logger.warning("Locale file %s did not contain a JSON object; ignoring", path)
            self._catalogs[locale] = {}
            return
        # Coerce values to strings to keep t() return type predictable.
        self._catalogs[locale] = {str(k): str(v) for k, v in data.items()}


_singleton: Translator | None = None
_singleton_lock = RLock()


def get_translator() -> Translator:
    """Return the process-wide :class:`Translator` singleton.

    The singleton is created on first call; subsequent calls return the same
    instance so shared state (current locale) is preserved across modules.
    """
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = Translator()
        return _singleton


def t(key: str, **kwargs: Any) -> str:
    """Convenience wrapper around the singleton's :meth:`Translator.t`."""
    return get_translator().t(key, **kwargs)


def reset_translator_for_tests(translator: Translator | None = None) -> Translator:
    """Replace the singleton. Intended for tests; not for production use."""
    global _singleton
    with _singleton_lock:
        _singleton = translator if translator is not None else Translator()
        return _singleton
