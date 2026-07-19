"""P2 regression tests: 16:9 window tiers, tier persistence, live apply.

Covers the Window aspect-lock / clamp logic, the settings-scene tier
cycling (persistence + live-apply callback), and the viewport
letterbox path used in fullscreen. All tests run headless: Window
resize paths that touch the real display are guarded by the
``get_surface() is None`` early return.
"""

import pygame

from airwar.game.scaled_viewport import ScaledViewport
from airwar.scenes.settings_scene import SettingsScene
from airwar.window.window import RESOLUTION_TIERS, Window


def _bare_window() -> Window:
    # No init(): the display is never created, so _set_os_window_size
    # early-returns and resize() becomes pure bookkeeping.
    return Window()


class TestWindowResize:
    def test_resize_locks_aspect_16_9(self):
        w = _bare_window()
        w.resize(1600, 100)  # requested height is ignored
        assert (w._width, w._height) == (1600, 900)

    def test_resize_clamps_to_min_tier(self):
        w = _bare_window()
        w.resize(800, 800)
        assert (w._width, w._height) == (1280, 720)

    def test_resize_clamps_to_max_tier(self):
        w = _bare_window()
        w.resize(9999, 100)
        assert (w._width, w._height) == (2560, 1440)

    def test_adaptive_size_is_16_9(self):
        w = _bare_window()
        aw, ah = w._get_adaptive_size()
        assert ah == aw * 9 // 16


class TestResolutionTiers:
    def test_tiers_are_all_16_9(self):
        for tier, (w, h) in RESOLUTION_TIERS.items():
            assert h == w * 9 // 16, f"tier {tier} is not 16:9"

    def test_set_resolution_tier_applies_each_tier(self):
        w = _bare_window()
        for tier, size in RESOLUTION_TIERS.items():
            assert w.set_resolution_tier(tier) is True
            assert (w._width, w._height) == size
            assert w._windowed_size == size

    def test_set_resolution_tier_rejects_unknown(self):
        w = _bare_window()
        w.set_resolution_tier("M")
        assert w.set_resolution_tier("XL") is False
        assert (w._width, w._height) == RESOLUTION_TIERS["M"]


def _bare_settings_scene(applied: list) -> SettingsScene:
    scene = object.__new__(SettingsScene)
    scene._db = None
    scene._username = None
    scene._settings_ref = {}
    scene._message = ""
    scene._message_timer = 0
    scene._on_resolution_tier = applied.append
    return scene


class TestSettingsResolutionRow:
    def test_cycle_resolution_persists_and_applies_live(self):
        applied = []
        scene = _bare_settings_scene(applied)

        scene._cycle_resolution()  # default M -> L
        assert scene._settings_ref["resolution_tier"] == "L"
        assert applied == ["L"]

        scene._cycle_resolution()  # L -> S
        assert scene._settings_ref["resolution_tier"] == "S"
        assert applied == ["L", "S"]

        scene._cycle_resolution()  # S -> M
        assert scene._settings_ref["resolution_tier"] == "M"
        assert applied == ["L", "S", "M"]

    def test_cycle_resolution_recovers_from_unknown_tier(self):
        applied = []
        scene = _bare_settings_scene(applied)
        scene._settings_ref["resolution_tier"] = "bogus"

        scene._cycle_resolution()  # treated as M -> L
        assert scene._settings_ref["resolution_tier"] == "L"
        assert applied == ["L"]


class TestViewportLetterbox:
    def test_present_letterboxes_on_taller_display(self):
        vp = ScaledViewport(logical_w=100, logical_h=50)
        vp.logical_surface.fill((0, 255, 0))
        display = pygame.Surface((200, 200))

        vp.present(display)

        # scale = min(200/100, 200/50) = 2 -> 200x100 band centered vertically.
        assert display.get_at((100, 10)) == (0, 0, 0, 255)  # top bar
        assert display.get_at((100, 100)) == (0, 255, 0, 255)  # content
        assert display.get_at((100, 190)) == (0, 0, 0, 255)  # bottom bar

    def test_present_pillarboxes_on_wider_display(self):
        vp = ScaledViewport(logical_w=100, logical_h=50)
        vp.logical_surface.fill((0, 255, 0))
        display = pygame.Surface((300, 100))

        vp.present(display)

        # scale = min(300/100, 100/50) = 2 -> 200x100 band centered horizontally.
        assert display.get_at((10, 50)) == (0, 0, 0, 255)  # left bar
        assert display.get_at((150, 50)) == (0, 255, 0, 255)  # content
        assert display.get_at((290, 50)) == (0, 0, 0, 255)  # right bar

    def test_present_reuses_cached_scratch_surface(self):
        vp = ScaledViewport(logical_w=100, logical_h=50)
        display = pygame.Surface((200, 200))
        vp.present(display)
        cache = vp._present_cache
        vp.present(display)
        assert vp._present_cache is cache  # no per-frame reallocation

    def test_screen_to_logical_after_tier_resize(self):
        # 16:9 window at tier S: the uniform transform maps window
        # coordinates back onto the fixed 1920x1080 logical surface.
        vp = ScaledViewport(logical_w=1920, logical_h=1080)
        vp.update(1280, 720)
        assert vp.screen_to_logical(640, 360) == (960.0, 540.0)
        assert vp.screen_to_logical(1280, 720) == (1920.0, 1080.0)


class TestViewportWindowSync:
    def test_sync_skipped_without_display_surface(self):
        # Headless: no display surface -> the explicitly-set transform
        # must survive a screen_to_logical call untouched.
        vp = ScaledViewport(logical_w=1920, logical_h=1080)
        vp.update(2160, 1080)
        assert vp.screen_to_logical(120, 0) == (0.0, 0.0)

    def test_sync_refreshes_transform_from_window_size(self, monkeypatch):
        vp = ScaledViewport(logical_w=1920, logical_h=1080)
        monkeypatch.setattr(pygame.display, "get_init", lambda: True)
        monkeypatch.setattr(pygame.display, "get_surface", lambda: object())
        monkeypatch.setattr(pygame.display, "get_window_size", lambda: (1280, 720))

        assert vp.screen_to_logical(640, 360) == (960.0, 540.0)
        assert vp._window_size == (1280, 720)

        # Window "resized" -> transform recomputed exactly once more.
        monkeypatch.setattr(pygame.display, "get_window_size", lambda: (2560, 1440))
        assert vp.screen_to_logical(1280, 720) == (960.0, 540.0)
        assert vp._window_size == (2560, 1440)


def test_settings_scene_focus_count_covers_resolution_row():
    scene = SettingsScene()
    assert scene._focus_count == 5  # ctrl, shift, language, resolution, back
