"""Tests for HUDRenderer text caching in the fallback (non-integrated) HUD path.

``render_hud`` previously re-rendered every label every frame
(``font.render`` x6). It must reuse cached surfaces via ``_render_value``
and only re-render labels whose text actually changed.
"""

import pygame

from airwar.game.rendering.hud_renderer import HUDRenderer


class _FontSpy:
    """Wraps a pygame Font and counts render() calls."""

    def __init__(self, font):
        self._font = font
        self.render_count = 0

    def render(self, *args, **kwargs):
        self.render_count += 1
        return self._font.render(*args, **kwargs)


def _make_renderer() -> tuple[HUDRenderer, _FontSpy, pygame.Surface, dict]:
    renderer = HUDRenderer()
    spy = _FontSpy(renderer.hud_font)
    renderer.hud_font = spy
    surface = pygame.Surface((800, 600))
    args = dict(
        surface=surface,
        score=1234,
        difficulty="normal",
        player_health=80,
        player_max_health=100,
        kills=5,
        next_progress=40,
        boss_kills=1,
    )
    return renderer, spy, surface, args


def test_render_hud_reuses_cached_surfaces():
    renderer, spy, _surface, args = _make_renderer()

    renderer.render_hud(**args)
    first_pass = spy.render_count
    assert first_pass == 6  # score, progress, difficulty, health, kills, boss

    renderer.render_hud(**args)
    assert spy.render_count == first_pass  # nothing changed → no re-render


def test_render_hud_rerenders_only_changed_labels():
    renderer, spy, _surface, args = _make_renderer()
    renderer.render_hud(**args)
    baseline = spy.render_count

    args["score"] = 1300
    renderer.render_hud(**args)
    assert spy.render_count == baseline + 1  # only the score label re-rendered


def test_render_hud_health_change_rerenders_once():
    renderer, spy, _surface, args = _make_renderer()
    renderer.render_hud(**args)
    baseline = spy.render_count

    args["player_health"] = 20  # drops below the danger ratio → danger color
    renderer.render_hud(**args)
    assert spy.render_count == baseline + 1
