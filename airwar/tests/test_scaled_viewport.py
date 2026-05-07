import pygame
import pytest

from airwar.game.scaled_viewport import ScaledViewport


def test_scaled_viewport_maps_letterboxed_screen_points_to_logical_space():
    viewport = ScaledViewport(1920, 1080)
    viewport.update(1000, 800)

    assert viewport.screen_to_logical(500, 400) == (960.0, 540.0)
    assert viewport.screen_to_logical(0, 400) == pytest.approx((0.0, 540.0))
    assert viewport.screen_to_logical(1000, 400)[0] == pytest.approx(1920.0)


def test_scaled_viewport_presents_centered_logical_surface_with_black_bars():
    viewport = ScaledViewport(1920, 1080)
    viewport.update(1000, 800)
    viewport.logical_surface.fill((255, 0, 0))

    display = pygame.Surface((1000, 800))
    viewport.present(display)

    assert display.get_at((500, 400))[:3] == (255, 0, 0)
    assert display.get_at((500, 10))[:3] == (0, 0, 0)
