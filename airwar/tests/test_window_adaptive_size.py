import pygame

from airwar.window.window import Window


class _DisplayInfo:
    def __init__(self, width: int, height: int):
        self.current_w = width
        self.current_h = height


def test_adaptive_window_keeps_native_default_size_when_display_can_fit(monkeypatch):
    monkeypatch.setattr(pygame.display, "Info", lambda: _DisplayInfo(1920, 1080))

    window = Window(1920, 1080)

    assert window._get_adaptive_size() == (1920, 1080)


def test_adaptive_window_scales_down_when_display_is_smaller(monkeypatch):
    monkeypatch.setattr(pygame.display, "Info", lambda: _DisplayInfo(1024, 768))

    window = Window(1920, 1080)

    width, height = window._get_adaptive_size()
    assert width < 1920
    assert height < 1080
    assert width <= 1024 - 40
    assert height <= 768 - 80


def test_adaptive_window_scales_proportionally(monkeypatch):
    monkeypatch.setattr(pygame.display, "Info", lambda: _DisplayInfo(1400, 900))

    window = Window(1920, 1080)

    width, height = window._get_adaptive_size()
    ratio = width / height
    expected_ratio = 1920 / 1080
    assert abs(ratio - expected_ratio) < 0.1
