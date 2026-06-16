"""WarningBanner i18n coverage."""

from __future__ import annotations

import pygame

from airwar.i18n import get_translator, reset_translator_for_tests
from airwar.ui import warning_banner
from airwar.ui.warning_banner import WarningBanner


class _FontSpy:
    def __init__(self) -> None:
        self.rendered: list[tuple[str, tuple[int, int, int]]] = []

    def render(self, text: str, _antialias: bool, color: tuple[int, int, int]) -> pygame.Surface:
        self.rendered.append((text, color))
        return pygame.Surface((max(1, len(text)), 1), pygame.SRCALPHA)


def test_warning_banner_renders_current_locale_text(monkeypatch) -> None:
    translator = reset_translator_for_tests(None)
    translator.set_locale("en_US")
    font = _FontSpy()
    monkeypatch.setattr(warning_banner, "get_cjk_font", lambda _size: font)

    banner = WarningBanner()
    assert banner.activate() is True

    assert [entry[0] for entry in font.rendered] == [
        "Mothership Ammo Depleted",
        "Preparing to Undock",
    ]
    reset_translator_for_tests(None)


def test_warning_banner_default_locale_stays_chinese(monkeypatch) -> None:
    reset_translator_for_tests(None)
    assert get_translator().get_locale() == "zh_CN"
    font = _FontSpy()
    monkeypatch.setattr(warning_banner, "get_cjk_font", lambda _size: font)

    banner = WarningBanner()
    assert banner.activate() is True

    assert [entry[0] for entry in font.rendered] == ["母舰弹药耗尽", "准备脱离"]
    reset_translator_for_tests(None)
