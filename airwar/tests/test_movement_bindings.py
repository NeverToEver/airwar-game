import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airwar.core_bindings import (
    update_movement,
    RUST_AVAILABLE,
)

pytestmark = pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")

# Default trailing args for the extended update_movement signature
_DEF = (100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 0)
# current_x, current_y, noise_scale_x, noise_scale_y, noise_amplitude_x, noise_amplitude_y, noise_seed


class TestMovementBindings:
    """Test movement pattern bindings."""

    def test_update_movement_straight(self):
        """Test straight movement pattern."""
        x, y, timer = update_movement(
            0, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert x == 100.0
        assert y > 100.0
        assert timer == 1.0

    def test_update_movement_sine(self):
        """Test sine movement pattern."""
        x, y, timer = update_movement(
            1, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert x > 100.0
        assert y > 100.0
        assert timer == 1.0

    def test_update_movement_zigzag(self):
        """Test zigzag movement pattern."""
        x, y, timer = update_movement(
            2, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert x > 100.0
        assert timer == 1.0

    def test_update_movement_dive(self):
        """Test dive movement pattern."""
        x, y, timer = update_movement(
            3, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert timer == 1.0

    def test_update_movement_hover(self):
        """Test hover movement pattern."""
        x, y, timer = update_movement(
            4, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert x > 100.0
        assert timer == 1.0

    def test_update_movement_spiral(self):
        """Test spiral movement pattern."""
        x, y, timer = update_movement(
            5, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert x != 100.0 or y != 100.0
        assert timer == 1.0

    def test_update_movement_timer_increments(self):
        """Test that timer increments correctly."""
        x1, y1, timer1 = update_movement(
            0, 10.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
        )
        assert timer1 == 11.0

    def test_update_movement_sequential_calls(self):
        """Test multiple sequential movement updates."""
        timer = 0.0
        for _ in range(10):
            x, y, timer = update_movement(
                1, timer, 100.0, 100.0, 80.0, 40.0,
                0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0, *_DEF,
            )
        assert timer == 10.0

    def test_zigzag_direction_change(self):
        """Test that zigzag direction changes at interval."""
        x1, y1, timer1 = update_movement(
            2, 0.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0, *_DEF,
        )
        x9, y9, timer9 = update_movement(
            2, 9.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0, *_DEF,
        )
        x10, y10, timer10 = update_movement(
            2, 10.0, 100.0, 100.0, 80.0, 40.0,
            0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0, *_DEF,
        )
        assert abs(x9 - 100.0) > 0.1 or abs(x10 - 100.0) > 0.1

    def test_movement_noise(self):
        """Test noise movement pattern (new in Phase 2)."""
        x, y, timer = update_movement(
            6, 0.0, 100.0, 100.0, 80.0, 50.0,
            0.0, 2.0, 0.0, 0.03, 0.0, 0.0, 0.0,  # speed=0.03 (noise_speed)
            100.0, 100.0, 0.04, 0.02, 0.7, 0.4, 9999,
        )
        assert abs(timer - 0.03) < 0.001  # noise timer increments by speed
        assert abs(x - 100.0) <= 6.1
        assert abs(y - 100.0) <= 6.1

    def test_movement_aggressive(self):
        """Test aggressive movement pattern (new in Phase 2)."""
        x, y, timer = update_movement(
            7, 0.0, 100.0, 100.0, 96.0, 60.0,
            0.0, 2.0, 0.0, 0.035, 0.0, 0.0, 0.0,  # speed=0.035 (agg_speed)
            100.0, 100.0, 0.025, 0.015, 0.6, 0.5, 9999,
        )
        assert abs(timer - 0.035) < 0.001  # aggressive timer increments by speed
        assert abs(x - 100.0) <= 8.1
        assert abs(y - 100.0) <= 8.1
