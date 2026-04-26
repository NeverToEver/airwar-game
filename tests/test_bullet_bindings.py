"""Tests for bullet Rust bindings."""

import pytest


class TestBatchUpdateBullets:
    """Tests for batch_update_bullets Rust function."""

    def test_import(self):
        """Test that batch_update_bullets can be imported."""
        from airwar.core_bindings import batch_update_bullets, RUST_AVAILABLE
        assert RUST_AVAILABLE is True
        assert callable(batch_update_bullets)

    def test_basic_movement(self):
        """Test basic bullet position updates."""
        from airwar.core_bindings import batch_update_bullets

        # (id, x, y, vx, vy, bullet_type, is_laser, screen_height)
        bullets = [
            (0, 100.0, 100.0, 0.0, -10.0, 0, False, 800.0),
        ]
        results = batch_update_bullets(bullets)
        assert len(results) == 1
        assert results[0][0] == 0  # id
        assert results[0][1] == 100.0  # x unchanged
        assert results[0][2] == 90.0  # y moved up by 10
        assert results[0][3] is True  # still active

    def test_off_screen_top(self):
        """Test bullet deactivation when going off screen top."""
        from airwar.core_bindings import batch_update_bullets

        bullets = [
            (0, 200.0, -20.0, 0.0, -10.0, 0, False, 800.0),
        ]
        results = batch_update_bullets(bullets)
        assert len(results) == 1
        assert results[0][3] is False  # inactive

    def test_off_screen_bottom(self):
        """Test bullet deactivation when going off screen bottom."""
        from airwar.core_bindings import batch_update_bullets

        bullets = [
            (0, 300.0, 850.0, 0.0, 10.0, 0, False, 800.0),
        ]
        results = batch_update_bullets(bullets)
        assert len(results) == 1
        assert results[0][3] is False  # inactive

    def test_laser_stays_active(self):
        """Test that laser bullets stay active even when off-screen."""
        from airwar.core_bindings import batch_update_bullets

        bullets = [
            (0, 400.0, -100.0, 0.0, -5.0, 2, True, 800.0),  # laser, off top
            (1, 500.0, 900.0, 0.0, 5.0, 2, True, 800.0),   # laser, off bottom
        ]
        results = batch_update_bullets(bullets)
        assert len(results) == 2
        assert results[0][3] is True  # laser stays active
        assert results[1][3] is True  # laser stays active

    def test_multiple_bullets(self):
        """Test batch update with multiple bullets."""
        from airwar.core_bindings import batch_update_bullets

        bullets = [
            (0, 100.0, 100.0, 0.0, -10.0, 0, False, 800.0),
            (1, 200.0, 200.0, 5.0, 0.0, 0, False, 800.0),  # moving right
            (2, 300.0, 300.0, -5.0, 0.0, 0, False, 800.0), # moving left
            (3, 400.0, 400.0, 0.0, 10.0, 0, False, 800.0), # moving down
        ]
        results = batch_update_bullets(bullets)
        assert len(results) == 4
        # All positions should be correctly updated
        assert results[0] == (0, 100.0, 90.0, True)
        assert results[1] == (1, 205.0, 200.0, True)
        assert results[2] == (2, 295.0, 300.0, True)
        assert results[3] == (3, 400.0, 410.0, True)

    def test_empty_input(self):
        """Test with empty input list."""
        from airwar.core_bindings import batch_update_bullets

        bullets = []
        results = batch_update_bullets(bullets)
        assert results == []
