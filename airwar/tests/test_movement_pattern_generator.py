"""Tests for MovementPatternGenerator — pattern generation and enhancement."""

import pytest

from airwar.game.systems.movement_pattern_generator import MovementPatternGenerator

# --- enhance_pattern ---


class TestEnhancePattern:
    def test_difficulty_1_returns_default(self):
        result = MovementPatternGenerator.enhance_pattern("straight", 1.0)
        assert result == {"speed_multiplier": 1.0}

    def test_straight_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("straight", 2.0)
        assert result["speed_multiplier"] == pytest.approx(1.3)  # 1.0 + 1.0 * 0.3

    def test_sine_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("sine", 2.0)
        assert result["amplitude_multiplier"] == pytest.approx(1.2)
        assert result["frequency_multiplier"] == pytest.approx(1.1)

    def test_zigzag_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("zigzag", 3.0)
        assert result["speed_multiplier"] == pytest.approx(1.5)  # 1.0 + 2.0 * 0.25
        assert result["direction_change_multiplier"] == pytest.approx(1.3)

    def test_hover_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("hover", 1.5)
        assert result["hover_speed_multiplier"] == pytest.approx(1.15)
        assert result["amplitude_multiplier"] == pytest.approx(1.1)

    def test_dive_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("dive", 2.0)
        assert result["speed_multiplier"] == pytest.approx(1.35)
        assert result["dive_trigger_multiplier"] == pytest.approx(1.1)

    def test_spiral_enhancement(self):
        result = MovementPatternGenerator.enhance_pattern("spiral", 2.0)
        assert result["spiral_speed_multiplier"] == pytest.approx(1.35)
        assert result["spiral_tightness"] == pytest.approx(1.1)

    def test_unknown_pattern_returns_default(self):
        result = MovementPatternGenerator.enhance_pattern("unknown", 2.0)
        assert result == {"speed_multiplier": 1.0}

    def test_sub_one_difficulty(self):
        result = MovementPatternGenerator.enhance_pattern("straight", 0.5)
        assert result["speed_multiplier"] == pytest.approx(0.85)  # 1.0 + (-0.5) * 0.3


# --- get_pattern ---


class TestGetPattern:
    def test_complexity_1_returns_straight(self):
        for _ in range(20):
            assert MovementPatternGenerator.get_pattern(1) == "straight"

    def test_complexity_clamped_below(self):
        for _ in range(20):
            assert MovementPatternGenerator.get_pattern(0) == "straight"

    def test_complexity_clamped_above(self):
        result = MovementPatternGenerator.get_pattern(999)
        assert result in ["straight", "sine", "zigzag", "hover", "spiral"]
