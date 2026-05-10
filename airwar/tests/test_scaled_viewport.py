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

    assert display.get_at((500, 400))[:3] == pytest.approx((255, 0, 0), abs=3)
    assert display.get_at((500, 10))[:3] == (0, 0, 0)


def test_scaled_viewport_presents_native_size_without_resampling(monkeypatch):
    viewport = ScaledViewport(1920, 1080)
    viewport.update(1920, 1080)
    viewport.logical_surface.fill((32, 128, 220))

    def fail_transform(*args):
        raise AssertionError("native viewport should be blitted without transform resampling")

    monkeypatch.setattr(pygame.transform, "scale", fail_transform)
    monkeypatch.setattr(pygame.transform, "smoothscale", fail_transform)

    display = pygame.Surface((1920, 1080))
    viewport.present(display)

    assert display.get_at((960, 540))[:3] == (32, 128, 220)


def test_scaled_viewport_scales_when_display_size_differs(monkeypatch):
    viewport = ScaledViewport(1920, 1080)
    viewport.update(1000, 800)

    calls = []

    def fake_scale(source, size):
        calls.append((source.get_size(), size))
        scaled = pygame.Surface(size)
        scaled.fill((90, 40, 160))
        return scaled

    monkeypatch.setattr(pygame.transform, "scale", fake_scale)

    display = pygame.Surface((1000, 800))
    viewport.present(display)

    expected_size = (1000, int(1080 * (1000 / 1920)))
    assert calls == [((1920, 1080), expected_size)]
    assert display.get_at((500, 400))[:3] == (90, 40, 160)


def test_screen_to_logical_clamps_out_of_bounds() -> None:
    viewport = ScaledViewport(1920, 1080)
    viewport.update(1000, 800)

    neg = viewport.screen_to_logical(-100, -100)
    assert neg[0] >= 0.0 and neg[1] >= 0.0

    large = viewport.screen_to_logical(9999, 9999)
    assert large[0] == pytest.approx(1920.0) and large[1] == pytest.approx(1080.0)
