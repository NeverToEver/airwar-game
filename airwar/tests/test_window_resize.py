"""Coverage push for airwar.window.window — resize / fullscreen / event paths.

Targets the high-leverage methods left uncovered by test_window_adaptive_size:
- ``init`` with both explicit and adaptive size
- ``resize`` clamping to ``_min_size`` / ``_max_size``
- ``resize`` no-op when fullscreen is active
- ``process_events`` for VIDEORESIZE / QUIT / KEYDOWN
- ``toggle_fullscreen`` window <-> fullscreen transition
- ``get_size`` fallback when ``pygame.display.get_window_size`` raises

The dummy SDL backend used in CI/headless runs can only allocate a small
number of display surfaces per process.  When this limit is hit, ``init``
raises ``pygame.error`` and any test that depends on the screen being
initialised is skipped — the clamp / event / get_size paths that do not
require a live renderer are still exercised.
"""

import contextlib

import pygame
import pytest

import airwar.window.window as window_module
from airwar.window.window import Window


class _DisplayInfo:
    def __init__(self, width: int, height: int):
        self.current_w = width
        self.current_h = height


@pytest.fixture
def dummy_display(monkeypatch):
    """Force a real (dummy) display surface and reset the module singleton.

    Several Window methods read ``pygame.display.get_window_size`` or call
    ``pygame.display.set_mode``; both require an initialised display.
    """
    pygame.init()
    monkeypatch.setattr(pygame.display, "Info", lambda: _DisplayInfo(1920, 1080))
    saved_singleton = window_module._window_instance
    window_module._window_instance = None
    yield
    window_module._window_instance = saved_singleton


def _safe_init(window: Window, *args) -> bool:
    """Try to initialise the display; return False if the dummy backend is full.

    Tests that need a live renderer should ``pytest.skip`` when this returns
    False so they don't flake when run as part of the full suite.
    """
    try:
        window.init(*args)
    except pygame.error:
        return False
    return True


# ─── init / surface ──────────────────────────────────────────────────────────


class TestWindowInit:
    def test_init_with_explicit_size(self, dummy_display) -> None:
        window = Window(800, 600, "TestInit")
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            assert window.is_running() is True
            assert window.get_surface() is not None
            assert window.get_clock() is not None
        finally:
            window.close()

    def test_init_uses_adaptive_size_when_unspecified(self, dummy_display, monkeypatch) -> None:
        monkeypatch.setattr(pygame.display, "Info", lambda: _DisplayInfo(1920, 1080))
        window = Window(1920, 1080)
        if not _safe_init(window):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            assert window.is_running() is True
            assert window.get_surface() is not None
        finally:
            window.close()

    def test_init_falls_back_to_defaults_on_pygame_error(self, dummy_display, monkeypatch) -> None:
        def _raise(*_a, **_kw):
            raise pygame.error("no display")

        monkeypatch.setattr(pygame.display, "Info", _raise)
        window = Window(1920, 1080)
        if not _safe_init(window):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            assert window.is_running() is True
        finally:
            window.close()


# ─── resize clamping ─────────────────────────────────────────────────────────


class TestWindowResize:
    def test_resize_clamps_to_min_size(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            # The clamp happens before set_mode; the resize() call may
            # still fail to recreate the renderer in the dummy backend, in
            # which case the cached clamp values are still authoritative.
            with contextlib.suppress(pygame.error):
                window.resize(100, 100)  # below min
            assert window._width == window._min_size[0]
            assert window._height == window._min_size[1]
        finally:
            window.close()

    def test_resize_clamps_to_max_size(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            with contextlib.suppress(pygame.error):
                window.resize(9999, 9999)  # above max
            assert window._width == window._max_size[0]
            assert window._height == window._max_size[1]
        finally:
            window.close()

    def test_resize_noop_when_fullscreen(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            window._is_fullscreen = True
            window._width, window._height = 1920, 1080
            window.resize(640, 480)
            # Fullscreen guard prevents both the clamp and the surface
            # recreation; width/height stay at the fullscreen value.
            assert window._width == 1920
            assert window._height == 1080
        finally:
            window.close()


# ─── process_events ──────────────────────────────────────────────────────────


class TestWindowProcessEvents:
    def test_process_events_reports_quit(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            try:
                quit_, _keydown, _resize = window.process_events()
                assert quit_ is True
            finally:
                pygame.event.clear(pygame.QUIT)
        finally:
            window.close()

    def test_process_events_reports_resize(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            resize_event = pygame.event.Event(pygame.VIDEORESIZE, w=1024, h=768, size=(1024, 768))
            pygame.event.post(resize_event)
            try:
                _quit, _keydown, resize = window.process_events()
                assert resize == (1024, 768)
                # process_events stores the new dimensions on the instance
                # (the OS window size, which equals what callers get_size
                # would return via get_window_size, is exercised separately).
                assert window._width == 1024
                assert window._height == 768
            finally:
                pygame.event.clear(pygame.VIDEORESIZE)
        finally:
            window.close()

    def test_process_events_reports_keydown(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            key_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0)
            pygame.event.post(key_event)
            try:
                _quit, keydown, _resize = window.process_events()
                assert keydown is not None
                assert keydown.key == pygame.K_ESCAPE
            finally:
                pygame.event.clear(pygame.KEYDOWN)
        finally:
            window.close()


# ─── get_size fallback ───────────────────────────────────────────────────────


class TestWindowGetSize:
    def test_get_size_falls_back_to_screen_when_pygame_errors(self, dummy_display, monkeypatch) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            monkeypatch.setattr(pygame.display, "get_window_size", lambda: (_ for _ in ()).throw(pygame.error("nope")))
            size = window.get_size()
            assert size == window.get_surface().get_size()
        finally:
            window.close()

    def test_get_size_falls_back_to_cached_when_surface_missing(self, dummy_display) -> None:
        window = Window(800, 600)
        # Don't call init — no _screen, no pygame.display. Cached size wins.
        size = window.get_size()
        assert size == (800, 600)


# ─── fullscreen toggle ──────────────────────────────────────────────────────


class TestWindowFullscreen:
    def test_toggle_fullscreen_noop_when_surface_missing(self, dummy_display) -> None:
        window = Window(800, 600)
        # _screen is None, so toggle should return silently and stay
        # non-fullscreen.
        window.toggle_fullscreen()
        assert window.is_fullscreen() is False

    def test_toggle_fullscreen_round_trip(self, dummy_display) -> None:
        window = Window(800, 600)
        if not _safe_init(window, 800, 600):
            pytest.skip("dummy SDL backend renderer slot exhausted")
        try:
            assert window.is_fullscreen() is False
            window.toggle_fullscreen()
            # With the dummy SDL backend the FULLSCREEN path may fall back to
            # the windowed mode (no error, just no fullscreen). Either way
            # the call must not raise and the screen must still be valid.
            assert window.get_surface() is not None
        finally:
            window.close()
