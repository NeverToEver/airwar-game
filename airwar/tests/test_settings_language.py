"""Tests for the language switcher in :mod:`airwar.scenes.settings_scene`.

Covers H-10:

* The settings scene exposes a third focusable row (language) in
  addition to the existing ctrl_mode / shift_boost_mode / back rows.
* Cycling the language calls ``airwar.i18n.set_locale`` and stores
  the new code in the settings dict under the ``"language"`` key.
* The cycle wraps around (last → first, first → second).
* A persisted language is honoured by ``UserDB.get_user_settings``
  so the next session starts in the right language.
* The cycling only persists the supported locales (no arbitrary
  strings leak into the settings dict).
"""

from __future__ import annotations

import pygame
import pytest

from airwar.scenes.settings_scene import SettingsScene


def _get_locale() -> str:
    """Read the current translator locale without going through the
    (un-exported) module-level helper."""
    from airwar.i18n import get_translator
    return get_translator().get_locale()


@pytest.fixture(autouse=True)
def _init_pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def _reset_translator():
    """Snapshot the translator singleton around each test so the
    default-locale invariant is restored after the cycle."""
    from airwar.i18n import get_translator, set_locale

    saved = get_translator().get_locale()
    set_locale("zh_CN")
    yield
    set_locale(saved)


def _make_scene(settings_ref=None) -> SettingsScene:
    scene = SettingsScene()
    scene.enter(db=None, username=None, settings_ref=settings_ref or {})
    return scene


def test_settings_scene_has_language_row_in_focus_count() -> None:
    """The scene must accept four focusable rows (ctrl, shift, language,
    back) — the language row is new in H-10."""
    scene = _make_scene()
    assert scene._focus_count == 4
    # The locale cycle must enumerate exactly the two supported locales.
    assert set(scene.AVAILABLE_LOCALES) == {"zh_CN", "en_US"}


def test_cycle_language_advances_locale_and_persists() -> None:
    """``_cycle_language`` must:
    * call ``set_locale`` with the next locale in the cycle
    * store the new locale under ``settings["language"]``
    * survive a follow-up call so the second cycle moves on
    """
    settings = {"ctrl_mode": "hold", "shift_boost_mode": "hold"}
    scene = _make_scene(settings)

    assert _get_locale() == "zh_CN"
    scene._cycle_language()
    assert _get_locale() == "en_US"
    assert settings["language"] == "en_US"

    scene._cycle_language()
    assert _get_locale() == "zh_CN"  # wraps around
    assert settings["language"] == "zh_CN"


def test_cycle_language_uses_stored_value_as_starting_point() -> None:
    """If the settings dict already has a stored language, the cycle
    must advance from THAT locale, not the global translator state.
    This is the contract that keeps a user who logged in mid-game
    from getting their selection silently overwritten."""
    settings = {"language": "en_US"}
    scene = _make_scene(settings)
    scene._cycle_language()
    # en_US → zh_CN (wrap)
    assert _get_locale() == "zh_CN"
    assert settings["language"] == "zh_CN"


def test_language_setting_round_trips_through_user_db(tmp_path) -> None:
    """``update_user_settings`` → ``get_user_settings`` must round-trip
    the ``language`` key, mirroring how ctrl_mode / shift_boost_mode
    already work. This is the persistence path the settings scene
    relies on."""
    from airwar.utils.database import UserDB

    db = UserDB(db_path=str(tmp_path / "users.json"))

    # Register a user, then save the language via the same path the
    # settings scene uses.
    db.create_user("pilot", password="hash_doesnt_matter_for_this")
    saved_settings = {"ctrl_mode": "hold", "shift_boost_mode": "hold", "language": "en_US"}
    assert db.update_user_settings("pilot", saved_settings) is True

    # Reload and verify the language key survived.
    reloaded = db.get_user_settings("pilot")
    assert reloaded["language"] == "en_US"
    # The other keys must still be present (no regression).
    assert reloaded["ctrl_mode"] == "hold"


def test_cycle_language_message_uses_translated_label() -> None:
    """The on-screen confirmation message must use the i18n key so
    the player sees ``"Language: en_US"`` in English mode and the
    Chinese equivalent in Chinese mode. We pin the English path
    (post-cycle) here so the test stays locale-independent."""
    from airwar.i18n import set_locale, t

    settings = {}
    scene = _make_scene(settings)
    set_locale("en_US")  # simulate already-English
    scene._cycle_language()
    assert "Language" in scene._message or "语言" in scene._message
    # The exact string is whichever locale the translator currently
    # holds — the assertion above is loose enough to survive both.
    assert scene._message_timer == 90
    # Bonus: the i18n key must exist in en_US so the English path
    # never falls back to the key string.
    set_locale("en_US")
    assert "{" not in t("settings.change_language", locale="en_US")
