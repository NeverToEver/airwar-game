"""Tests for the scaled logical viewport coordinate abstraction."""

import pygame
import pytest

from airwar.game.scaled_viewport import ScaledViewport


class TestScaledViewport:
    def test_default_logical_size(self):
        vp = ScaledViewport()
        assert vp.logical_size == (1920, 1080)

    def test_identity_transform_when_display_matches_logical(self):
        vp = ScaledViewport(logical_w=1920, logical_h=1080)
        vp.update(1920, 1080)
        assert vp.screen_to_logical(100, 200) == pytest.approx((100.0, 200.0))

    def test_letterboxing_centers_logical_surface(self):
        vp = ScaledViewport(logical_w=1920, logical_h=1080)
        # 2:1 display, 16:9 logical -> fit to height, black bars left/right.
        vp.update(2160, 1080)
        expected_scale = 1080 / 1080  # 1.0
        offset_x = (2160 - 1920 * expected_scale) / 2  # 120
        # Center of the left letterbox maps to logical (0, 0).
        assert vp.screen_to_logical(offset_x, 0) == pytest.approx((0.0, 0.0))
        # Center of the viewport maps to logical center.
        assert vp.screen_to_logical(offset_x + 960, 540) == pytest.approx((960.0, 540.0))

    def test_screen_to_logical_clamps_to_logical_bounds(self):
        vp = ScaledViewport(logical_w=800, logical_h=600)
        vp.update(800, 600)
        assert vp.screen_to_logical(-10, -20) == (0.0, 0.0)
        assert vp.screen_to_logical(900, 700) == (800.0, 600.0)

    def test_zero_display_size_results_zero_offset(self):
        vp = ScaledViewport(logical_w=800, logical_h=600)
        vp.update(0, 0)
        assert vp.screen_to_logical(100, 100) == (0.0, 0.0)

    def test_present_blits_to_display_surface(self):
        vp = ScaledViewport(logical_w=100, logical_h=100)
        display = pygame.Surface((100, 100))
        display.fill((255, 0, 0))
        vp.logical_surface.fill((0, 255, 0))
        vp.present(display)
        assert display.get_at((50, 50)) == (0, 255, 0, 255)

    def test_rejects_non_positive_logical_size(self):
        with pytest.raises(ValueError):
            ScaledViewport(logical_w=0, logical_h=1080)
        with pytest.raises(ValueError):
            ScaledViewport(logical_w=1920, logical_h=-1)

    def test_logical_size_setter_rebuilds_surface(self):
        vp = ScaledViewport(logical_w=100, logical_h=100)
        original_surface = vp.logical_surface
        vp.logical_size = (200, 200)
        assert vp.logical_size == (200, 200)
        assert vp.logical_surface is not original_surface
        assert vp.logical_surface.get_size() == (200, 200)

    def test_logical_size_setter_rejects_non_positive_size(self):
        vp = ScaledViewport(logical_w=100, logical_h=100)
        with pytest.raises(ValueError):
            vp.logical_size = (0, 100)
        with pytest.raises(ValueError):
            vp.logical_size = (100, -1)
