import pytest
import pygame


class TestSpriteBindings:
    """Test Rust sprite glow functions."""

    def test_single_bullet_glow_creates_surface(self):
        from airwar.core_bindings import create_single_bullet_glow, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            pytest.skip("Rust not available")

        data = create_single_bullet_glow(8.0, 16.0)
        # Surface should be width+16 by height+12
        expected_size = (8 + 16) * (16 + 12) * 4  # RGBA
        assert len(data) == expected_size

    def test_spread_bullet_glow_creates_surface(self):
        from airwar.core_bindings import create_spread_bullet_glow, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            pytest.skip("Rust not available")

        data = create_spread_bullet_glow(6.0)
        # Surface should be radius*4+8 by radius*4+8
        expected_size = (6 * 4 + 8) * (6 * 4 + 8) * 4
        assert len(data) == expected_size

    def test_laser_bullet_glow_creates_surface(self):
        from airwar.core_bindings import create_laser_bullet_glow, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            pytest.skip("Rust not available")

        data = create_laser_bullet_glow(20.0)
        # Surface should be 20 by height+8
        expected_size = 20 * (20 + 8) * 4
        assert len(data) == expected_size

    def test_explosive_missile_glow_creates_surface(self):
        from airwar.core_bindings import create_explosive_missile_glow, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            pytest.skip("Rust not available")

        data = create_explosive_missile_glow(10.0, 20.0)
        bw = int(10.0 * 0.8)
        surf_w = bw * 3 + 12
        surf_h = int(20.0) + 10
        expected_size = surf_w * surf_h * 4
        assert len(data) == expected_size

    def test_glow_circle_creates_surface(self):
        from airwar.core_bindings import create_glow_circle, RUST_AVAILABLE
        if not RUST_AVAILABLE:
            pytest.skip("Rust not available")

        data = create_glow_circle(10, 255, 0, 0, 5)
        size = (10 + 5) * 2 + 4
        expected_size = size * size * 4
        assert len(data) == expected_size


class TestSpriteRendering:
    """Test that sprite drawing functions work with pygame."""

    @pytest.fixture(autouse=True)
    def setup_pygame(self):
        pygame.init()
        pygame.display.set_mode((400, 400))

    def test_draw_single_bullet(self):
        from airwar.utils.sprites import draw_single_bullet, _single_bullet_glow_cache

        screen = pygame.Surface((200, 200))
        draw_single_bullet(screen, 100, 100, 8, 16)
        # Check that glow was cached
        assert (8, 16) in _single_bullet_glow_cache

    def test_draw_spread_bullet(self):
        from airwar.utils.sprites import draw_spread_bullet, _spread_bullet_glow_cache

        screen = pygame.Surface((200, 200))
        draw_spread_bullet(screen, 100, 100, 12, 12)
        assert 6 in _spread_bullet_glow_cache

    def test_draw_laser_bullet(self):
        from airwar.utils.sprites import draw_laser_bullet, _laser_bullet_glow_cache

        screen = pygame.Surface((200, 200))
        draw_laser_bullet(screen, 100, 100, 4, 20)
        assert 20 in _laser_bullet_glow_cache

    def test_draw_explosive_missile(self):
        from airwar.utils.sprites import draw_explosive_missile, _explosive_missile_cache

        screen = pygame.Surface((200, 200))
        draw_explosive_missile(screen, 100, 100, 10, 20)
        bw = int(10 * 0.8)
        assert (bw, 20) in _explosive_missile_cache
