"""Tests for ``airwar.utils.fonts`` — locale-aware font selection.

The login panel placeholder needs a font that matches the active locale
(English placeholder under an English UI, CJK placeholder under a CJK
UI). Pre-M-6 the placeholder always used the CJK font, so non-CJK
locales saw a slightly-too-bold / wrong-metrics rendering of the
placeholder text. These tests pin the post-M-6 contract.
"""

from __future__ import annotations

import pygame
import pytest

from airwar.utils.fonts import get_font_for_locale, is_cjk_locale


@pytest.fixture(autouse=True)
def _init_pygame_font():
    """``pygame.font.Font`` raises ``pygame.error: font not initialized``
    until ``pygame.init()`` runs. The login panel's font selection
    happens during scene render, so any code path that calls
    ``get_font_for_locale`` must have pygame initialised first.

    Note: we deliberately do NOT call ``pygame.quit()`` on teardown.
    The session-level pygame state is shared across all tests in
    the run; calling ``pygame.quit()`` here would invalidate the
    display surface and font cache for every subsequent test,
    surfacing as a SIGSEGV in the next ``font.render`` call (typically
    several hundred tests later when the test order finally reaches a
    render test). The init call is idempotent, so re-entering the
    fixture across tests is safe.
    """
    pygame.init()


@pytest.mark.parametrize(
    "locale,expected",
    [
        ("zh_CN", True),
        ("zh_TW", True),
        ("zh_HK", True),
        ("zh", True),
        ("ZH_CN", True),  # case-insensitive
        ("ja_JP", True),
        ("ko_KR", True),
        ("en_US", False),
        ("en_GB", False),
        ("fr_FR", False),
        ("de_DE", False),
        ("es_ES", False),
        ("ru_RU", False),
        ("pt_BR", False),
    ],
)
def test_is_cjk_locale_matches_only_cjk_language_tags(locale: str, expected: bool) -> None:
    assert is_cjk_locale(locale) is expected


def test_is_cjk_locale_treats_empty_string_as_latin() -> None:
    assert is_cjk_locale("") is False


def test_is_cjk_locale_handles_bcp47_dash_separator() -> None:
    """BCP-47 codes use ``-`` (e.g. ``zh-Hans-CN``); POSIX uses ``_``."""
    assert is_cjk_locale("zh-Hans-CN") is True
    assert is_cjk_locale("en-US") is False


def test_get_font_for_locale_returns_pygame_font() -> None:
    """Both branches must return a real pygame Font object."""
    import pygame

    cjk = get_font_for_locale("zh_CN", 24)
    latin = get_font_for_locale("en_US", 24)
    assert isinstance(cjk, pygame.font.Font)
    assert isinstance(latin, pygame.font.Font)


def test_get_font_for_locale_caches_results() -> None:
    """The helper must cache by (locale, size) — login panel calls it every frame."""
    a = get_font_for_locale("en_US", 24)
    b = get_font_for_locale("en_US", 24)
    assert a is b  # cache hit returns the same Font object


def test_get_font_for_locale_different_sizes_differ() -> None:
    """Cache key is (locale, size) — different sizes must produce different Font objects."""
    small = get_font_for_locale("en_US", 16)
    large = get_font_for_locale("en_US", 32)
    assert small is not large
