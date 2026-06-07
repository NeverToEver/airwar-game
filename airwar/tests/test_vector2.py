"""Tests for Vector2 with Rust-backed arithmetic."""

import math

import pytest

from airwar.core_bindings import RUST_AVAILABLE
from airwar.entities.base import Vector2


def test_construct_default():
    v = Vector2()
    assert v.x == 0
    assert v.y == 0


def test_construct_explicit():
    v = Vector2(3, 4)
    assert v.x == 3
    assert v.y == 4


def test_add_two_vectors():
    r = Vector2(1, 2) + Vector2(3, 4)
    assert r == Vector2(4, 6)


def test_radd_supports_zero():
    # 0 + v should work (relies on __radd__)
    r = 0 + Vector2(1, 2)
    # This is not exactly __radd__ (0 isn't a Vector2), but a + b where a is int triggers __radd__
    # The expected behaviour here depends on whether __radd__ returns a Vector2 — it should.
    assert isinstance(r, Vector2)


def test_subtract_vectors():
    r = Vector2(5, 7) - Vector2(2, 3)
    assert r == Vector2(3, 4)


def test_multiply_by_scalar():
    r = Vector2(3, 4) * 2.5
    assert r.x == pytest.approx(7.5)
    assert r.y == pytest.approx(10.0)


def test_rmul_by_scalar():
    r = 2.5 * Vector2(3, 4)
    assert r.x == pytest.approx(7.5)
    assert r.y == pytest.approx(10.0)


def test_length_345():
    assert Vector2(3, 4).length() == pytest.approx(5.0)


def test_length_zero():
    assert Vector2(0, 0).length() == 0.0


def test_normalize_unit_vector():
    v = Vector2(3, 4).normalize()
    assert v.x == pytest.approx(0.6, abs=1e-5)
    assert v.y == pytest.approx(0.8, abs=1e-5)


def test_normalize_zero_vector():
    v = Vector2(0, 0).normalize()
    assert v.x == 0.0
    assert v.y == 0.0


def test_abs_of_negative():
    v = abs(Vector2(-3, -4))
    assert v == Vector2(3, 4)


def test_dot_product():
    assert Vector2(1, 2).dot(Vector2(3, 4)) == pytest.approx(11.0)


def test_dot_orthogonal():
    assert Vector2(1, 0).dot(Vector2(0, 1)) == pytest.approx(0.0)


def test_distance_between():
    assert Vector2(0, 0).distance(Vector2(3, 4)) == pytest.approx(5.0)


def test_angle_zero_x_axis():
    assert Vector2(1, 0).angle() == pytest.approx(0.0)


def test_angle_y_axis():
    assert Vector2(0, 1).angle() == pytest.approx(math.pi / 2, abs=1e-5)


def test_from_angle_round_trip():
    v = Vector2.from_angle(1.0, 2.0)
    assert v.length() == pytest.approx(2.0)
    assert v.angle() == pytest.approx(1.0, abs=1e-5)


def test_lerp_midpoint():
    r = Vector2(0, 0).lerp(Vector2(2, 4), 0.5)
    assert r == Vector2(1, 2)


def test_lerp_endpoints():
    assert Vector2(0, 0).lerp(Vector2(10, 20), 0.0) == Vector2(0, 0)
    assert Vector2(0, 0).lerp(Vector2(10, 20), 1.0) == Vector2(10, 20)


def test_clamp_length_under_limit_unchanged():
    v = Vector2(1, 1)
    assert v.clamp_length(10.0) == Vector2(1, 1)


def test_clamp_length_over_limit_scaled():
    v = Vector2(3, 4)  # length 5
    r = v.clamp_length(2.5)  # limit 2.5 -> scale 0.5
    assert r.x == pytest.approx(1.5)
    assert r.y == pytest.approx(2.0)


def test_clamp_length_zero_vector():
    assert Vector2(0, 0).clamp_length(5.0) == Vector2(0, 0)


def test_to_tuple():
    assert Vector2(3, 4).to_tuple() == (3, 4)


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust not available — Rust path not tested")
def test_rust_and_python_paths_agree():
    """If Rust is available, results must be numerically identical to the
    Python fallback. The Python fallback path is exercised by setting
    RUST_AVAILABLE=False at runtime, but since it's a module-level flag
    we just verify the Rust path produces the expected values.
    """
    a = Vector2(7, 11)
    b = Vector2(3, 4)
    assert (a + b) == Vector2(10, 15)
    assert (a - b) == Vector2(4, 7)
    assert (a * 2) == Vector2(14, 22)
    assert a.dot(b) == pytest.approx(7 * 3 + 11 * 4)
    assert a.distance(b) == pytest.approx(math.hypot(4, 7))
