"""Tests for movement strategies — _smooth_noise, factory, strategy updates."""

from unittest.mock import MagicMock

import pytest

from airwar.entities.movement_strategies import (
    AggressiveMovement,
    DiveMovement,
    HoverMovement,
    NoiseMovement,
    SineMovement,
    SpiralMovement,
    StraightMovement,
    ZigzagMovement,
    _smooth_noise,
    get_movement_strategy,
)

# 8 enemy movement patterns drive every wave — pure logic, smoke them so
# any strategy regression trips the PR fast-path.
pytestmark = pytest.mark.smoke

# --- _smooth_noise ---


class TestSmoothNoise:
    def test_returns_float(self):
        assert isinstance(_smooth_noise(1.0, 42), float)

    def test_range_clamped(self):
        for x in [0.0, 0.5, 1.0, 5.0, 100.0, -50.0]:
            for seed in [0, 42, 999]:
                val = _smooth_noise(x, seed)
                assert -1.0 <= val <= 1.0

    def test_continuous(self):
        # nearby x values should produce similar outputs
        for seed in [0, 42]:
            v1 = _smooth_noise(5.0, seed)
            v2 = _smooth_noise(5.01, seed)
            assert abs(v1 - v2) < 0.1

    def test_seed_changes_output(self):
        v1 = _smooth_noise(10.0, 0)
        v2 = _smooth_noise(10.0, 999)
        assert v1 != v2


# --- get_movement_strategy factory ---


class TestGetMovementStrategy:
    def test_known_types(self):
        cases = {
            "straight": StraightMovement,
            "sine": SineMovement,
            "zigzag": ZigzagMovement,
            "dive": DiveMovement,
            "hover": HoverMovement,
            "spiral": SpiralMovement,
            "noise": NoiseMovement,
            "aggressive": AggressiveMovement,
        }
        for name, cls in cases.items():
            assert isinstance(get_movement_strategy(name), cls)

    def test_unknown_returns_straight(self):
        assert isinstance(get_movement_strategy("unknown"), StraightMovement)


# --- strategy updates ---


def _make_enemy(**overrides):
    """Create a mock enemy with default movement attributes."""
    defaults = {
        "rect": MagicMock(x=100, y=200),
        "active_position_x": 100.0,
        "active_position_y": 200.0,
        "lifetime": 0,
        "move_timer": 0,
        "move_frequency": 0.05,
        "move_offset": 0.0,
        "zigzag_timer": 0,
        "zigzag_interval": 30,
        "zigzag_speed": 3,
        "direction": 1,
        "dive_timer": 0,
        "hover_timer": 0.0,
        "spiral_timer": 0,
        "spiral_frequency": 0.1,
        "noise_timer": 0.0,
        "noise_speed": 0.02,
        "noise_scale_x": 1.0,
        "noise_scale_y": 1.0,
        "noise_seed": 42,
        "noise_amplitude_x": 1.0,
        "noise_amplitude_y": 1.0,
        "agg_timer": 0.0,
        "agg_speed": 0.02,
        "agg_scale_x": 1.0,
        "agg_scale_y": 1.0,
        "agg_seed": 42,
        "agg_amplitude_x": 1.0,
        "agg_amplitude_y": 1.0,
        "sync_rects": MagicMock(),
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


class TestStraightMovement:
    def test_sets_position(self):
        enemy = _make_enemy()
        StraightMovement().update(enemy)
        assert enemy.rect.x == enemy.active_position_x
        enemy.sync_rects.assert_called_once()


class TestSineMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        SineMovement().update(enemy)
        assert enemy.move_timer == 1

    def test_calls_sync(self):
        enemy = _make_enemy()
        SineMovement().update(enemy)
        enemy.sync_rects.assert_called_once()


class TestZigzagMovement:
    def test_direction_flips_at_interval(self):
        enemy = _make_enemy(zigzag_timer=29, zigzag_interval=30, direction=1)
        ZigzagMovement().update(enemy)
        assert enemy.direction == -1

    def test_timer_resets(self):
        enemy = _make_enemy(zigzag_timer=29, zigzag_interval=30)
        ZigzagMovement().update(enemy)
        assert enemy.zigzag_timer == 0


class TestDiveMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        DiveMovement().update(enemy)
        assert enemy.dive_timer == 1


class TestHoverMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        HoverMovement().update(enemy)
        assert enemy.hover_timer == pytest.approx(0.08)


class TestSpiralMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        SpiralMovement().update(enemy)
        assert enemy.spiral_timer == 1


class TestNoiseMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        NoiseMovement().update(enemy)
        assert enemy.noise_timer == pytest.approx(0.02)

    def test_clamps_large_deltas(self):
        enemy = _make_enemy()
        enemy.rect.x = 0
        enemy.rect.y = 0
        enemy.active_position_x = 1000.0
        enemy.active_position_y = 1000.0
        NoiseMovement().update(enemy)
        # movement should be clamped to max_delta=6
        assert abs(enemy.rect.x - 0) <= 6
        assert abs(enemy.rect.y - 0) <= 6


class TestAggressiveMovement:
    def test_increments_timer(self):
        enemy = _make_enemy()
        AggressiveMovement().update(enemy)
        assert enemy.agg_timer == pytest.approx(0.02)

    def test_clamps_large_deltas(self):
        enemy = _make_enemy()
        enemy.rect.x = 0
        enemy.rect.y = 0
        enemy.active_position_x = 1000.0
        enemy.active_position_y = 1000.0
        AggressiveMovement().update(enemy)
        # max_delta=8
        assert abs(enemy.rect.x - 0) <= 8
        assert abs(enemy.rect.y - 0) <= 8
