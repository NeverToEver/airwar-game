import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airwar.core_bindings import (
    vec2_length,
    vec2_normalize,
    vec2_add,
    vec2_sub,
    vec2_dot,
    vec2_distance,
    vec2_cross,
    vec2_scale,
    vec2_length_squared,
    vec2_distance_squared,
    vec2_angle,
    vec2_from_angle,
    vec2_lerp,
    vec2_clamp_length,
    RUST_AVAILABLE,
)

pytestmark = pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")


class TestVector2Bindings:
    def test_vec2_length(self):
        assert abs(vec2_length(3.0, 4.0) - 5.0) < 0.001

    def test_vec2_normalize(self):
        x, y = vec2_normalize(3.0, 4.0)
        assert abs(x - 0.6) < 0.001
        assert abs(y - 0.8) < 0.001

    def test_vec2_add(self):
        x, y = vec2_add(1.0, 2.0, 3.0, 4.0)
        assert x == 4.0 and y == 6.0

    def test_vec2_sub(self):
        x, y = vec2_sub(5.0, 7.0, 2.0, 3.0)
        assert x == 3.0 and y == 4.0

    def test_vec2_dot(self):
        assert abs(vec2_dot(1.0, 0.0, 0.0, 1.0)) < 0.001
        assert abs(vec2_dot(1.0, 0.0, 1.0, 0.0) - 1.0) < 0.001

    def test_vec2_cross(self):
        assert abs(vec2_cross(1.0, 0.0, 0.0, 1.0) - 1.0) < 0.001

    def test_vec2_scale(self):
        x, y = vec2_scale(2.0, 3.0, 2.0)
        assert x == 4.0 and y == 6.0

    def test_vec2_distance(self):
        assert abs(vec2_distance(0.0, 0.0, 3.0, 4.0) - 5.0) < 0.001

    def test_vec2_length_squared(self):
        assert abs(vec2_length_squared(3.0, 4.0) - 25.0) < 0.001

    def test_vec2_distance_squared(self):
        assert abs(vec2_distance_squared(0.0, 0.0, 3.0, 4.0) - 25.0) < 0.001

    def test_vec2_lerp(self):
        x, y = vec2_lerp(0.0, 0.0, 10.0, 10.0, 0.5)
        assert abs(x - 5.0) < 0.001
        assert abs(y - 5.0) < 0.001

    def test_vec2_clamp_length(self):
        x, y = vec2_clamp_length(10.0, 0.0, 5.0)
        assert abs(x - 5.0) < 0.001
        assert y == 0.0