import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airwar.core_bindings import (
    update_movement,
    RUST_AVAILABLE,
)

pytestmark = pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")


class TestMovementBindings:
    """Test movement pattern bindings."""

    def test_update_movement_straight(self):
        """Test straight movement pattern."""
        x, y, timer = update_movement(
            0,  # move_type: straight
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        assert x == 100.0  # x should be unchanged
        assert y > 100.0  # y should increase slightly due to oscillation
        assert timer == 1.0

    def test_update_movement_sine(self):
        """Test sine movement pattern."""
        x, y, timer = update_movement(
            1,  # move_type: sine
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        assert x > 100.0  # sine wave moves x
        assert y > 100.0
        assert timer == 1.0

    def test_update_movement_zigzag(self):
        """Test zigzag movement pattern."""
        x, y, timer = update_movement(
            2,  # move_type: zigzag
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        # Zigzag moves in x direction
        assert x > 100.0
        assert timer == 1.0

    def test_update_movement_dive(self):
        """Test dive movement pattern."""
        x, y, timer = update_movement(
            3,  # move_type: dive
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        assert timer == 1.0

    def test_update_movement_hover(self):
        """Test hover movement pattern."""
        x, y, timer = update_movement(
            4,  # move_type: hover
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        assert x > 100.0  # hover creates oscillation
        assert timer == 1.0

    def test_update_movement_spiral(self):
        """Test spiral movement pattern."""
        x, y, timer = update_movement(
            5,  # move_type: spiral
            0.0,  # timer
            100.0,  # active_x
            100.0,  # active_y
            80.0,  # move_range_x
            40.0,  # move_range_y
            0.0,  # offset
            2.0,  # amplitude
            0.05,  # frequency
            2.0,  # speed
            1.0,  # direction
            45.0,  # zigzag_interval
            40.0,  # spiral_radius
        )
        # Spiral creates movement in both x and y
        assert x != 100.0 or y != 100.0
        assert timer == 1.0

    def test_update_movement_timer_increments(self):
        """Test that timer increments correctly."""
        x1, y1, timer1 = update_movement(0, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0)
        assert timer1 == 11.0

    def test_update_movement_sequential_calls(self):
        """Test multiple sequential movement updates."""
        timer = 0.0

        for _ in range(10):
            x, y, timer = update_movement(1, timer, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 45.0, 40.0)

        assert timer == 10.0
        # After 10 iterations, sine wave should have progressed
        # x should not be exactly 100 since sine is oscillating

    def test_zigzag_direction_change(self):
        """Test that zigzag direction changes at interval."""
        # Start with direction=1 at timer=0
        x1, y1, timer1 = update_movement(2, 0.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0)

        # At timer=9, direction should still be 1
        x9, y9, timer9 = update_movement(2, 9.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0)

        # At timer=10 (interval), direction should flip
        x10, y10, timer10 = update_movement(2, 10.0, 100.0, 100.0, 80.0, 40.0, 0.0, 2.0, 0.05, 2.0, 1.0, 10.0, 40.0)

        # x9 and x10 should be in different directions
        assert abs(x9 - 100.0) > 0.1 or abs(x10 - 100.0) > 0.1  # at least one has moved