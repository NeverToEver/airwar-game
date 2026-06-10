"""Property-based tests for vec2 / lerp / normalize / collision math.

P2-4: complements the 762 example-based tests with Hypothesis-driven
invariant checks. Targets high-ROI mathematical properties whose
violations would indicate a serious regression in the vec2 / collision
math (used throughout enemy movement, bullet trajectories, particle
physics, and mothership flight).

Properties verified:
1. ``vec2_add`` is commutative (a + b == b + a) and associative
   ((a + b) + c == a + (b + c)).
2. ``vec2_lerp`` preserves its endpoints: lerp(0) == a, lerp(1) == b,
   and the midpoint lerp(0.5) lies on the segment between a and b.
3. ``vec2_normalize`` returns a unit vector whenever the input has
   nonzero magnitude.
4. Collision detection is symmetric: if bullet A hits enemy B then
   enemy B is hit by bullet A.

The Python fallback implementation in ``airwar.core_bindings`` is
exercised when the optional ``airwar_core`` Rust extension is not
installed (CI builds the wheel, so the Rust path is normally active;
locally without ``maturin develop`` the fallback is what runs).
"""

from __future__ import annotations

import math
import os
import sys
from typing import Iterable

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from airwar.core_bindings import (
    batch_collide_bullets_vs_entities,
    vec2_add,
    vec2_length,
    vec2_lerp,
    vec2_normalize,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Bounded coordinates: large enough to exercise additive / subtractive
# arithmetic, small enough to keep float32 ULP within a sane range.
# The Rust extension rounds through f32, so the comparison tolerance
# scales with magnitude. Restricting to a few hundred keeps the
# f32 quantization noise at most a few ULPs of float32.
finite_floats = st.floats(
    min_value=-128.0,
    max_value=128.0,
    allow_nan=False,
    allow_infinity=False,
)
# Normalized direction vectors for normalize tests (avoid (0, 0) which
# is the documented zero-length special case).
nonzero_direction = st.tuples(
    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False).filter(
        lambda v: abs(v) > 1e-6
    ),
    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False).filter(
        lambda v: abs(v) > 1e-6
    ),
)
lerp_t = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
collision_coord = st.integers(min_value=-500, max_value=500)


# AABB layouts (id, x, y, w, h) -- small positive sizes so we get a
# mix of hit and miss in the symmetry test.
bullet_spec = st.tuples(
    st.integers(min_value=0, max_value=10_000),
    collision_coord,
    collision_coord,
    st.integers(min_value=4, max_value=40),
    st.integers(min_value=4, max_value=40),
)
enemy_spec = st.tuples(
    st.integers(min_value=0, max_value=10_000),
    collision_coord,
    collision_coord,
    st.integers(min_value=4, max_value=40),
    st.integers(min_value=4, max_value=40),
)


# ---------------------------------------------------------------------------
# Property 1: vec2_add is commutative and associative.
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@given(
    st.tuples(finite_floats, finite_floats),
    st.tuples(finite_floats, finite_floats),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_add_commutative(a: tuple[float, float], b: tuple[float, float]) -> None:
    """a + b == b + a for any two finite vectors."""
    forward = vec2_add(a[0], a[1], b[0], b[1])
    reverse = vec2_add(b[0], b[1], a[0], a[1])
    assert math.isclose(forward[0], reverse[0], abs_tol=1e-6, rel_tol=1e-6)
    assert math.isclose(forward[1], reverse[1], abs_tol=1e-6, rel_tol=1e-6)


@pytest.mark.smoke
@given(
    st.tuples(finite_floats, finite_floats),
    st.tuples(finite_floats, finite_floats),
    st.tuples(finite_floats, finite_floats),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_add_associative(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> None:
    """(a + b) + c == a + (b + c) for any three finite vectors.

    Float addition is not strictly associative, so we tolerate a small
    ULP-scale relative error. The point of the test is to catch
    catastrophic regressions (e.g. a refactor that swaps operands or
    silently drops a term), not to enforce bit-exact equality.
    """
    left = vec2_add(a[0] + b[0], a[1] + b[1], c[0], c[1])
    right = vec2_add(a[0], a[1], b[0] + c[0], b[1] + c[1])
    assert math.isclose(left[0], right[0], abs_tol=1e-4, rel_tol=1e-5)
    assert math.isclose(left[1], right[1], abs_tol=1e-4, rel_tol=1e-5)


# ---------------------------------------------------------------------------
# Property 2: vec2_lerp preserves its endpoints and the midpoint lies
# exactly on the segment.
# ---------------------------------------------------------------------------


# The Rust extension rounds through f32 internally. At endpoint t=0
# the formula collapses to ``a + (b - a) * 0 == a``, which under f32
# can differ from the f64 input by a few f32 ULPs. We scale tolerance
# to the magnitude of the larger endpoint, which catches real
# regressions (sign flips, operand swaps) while tolerating f32 noise.
# At scale 128 the f32 ULP is ~1.5e-5, so 1e-4 covers a few ULPs of
# headroom for cancellation in the (b - a) intermediate.
LERP_TOL = 1e-4


@pytest.mark.smoke
@given(
    st.tuples(finite_floats, finite_floats),
    st.tuples(finite_floats, finite_floats),
    lerp_t,
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_lerp_endpoints(
    a: tuple[float, float], b: tuple[float, float], t: float
) -> None:
    """lerp(0) == a and lerp(1) == b for any finite endpoints.

    ``t`` is included in the strategy so the generator exercises a
    range of t-values too, but the assertion only depends on a and b.
    """
    at_zero = vec2_lerp(a[0], a[1], b[0], b[1], 0.0)
    at_one = vec2_lerp(a[0], a[1], b[0], b[1], 1.0)
    assert math.isclose(at_zero[0], a[0], abs_tol=LERP_TOL)
    assert math.isclose(at_zero[1], a[1], abs_tol=LERP_TOL)
    assert math.isclose(at_one[0], b[0], abs_tol=LERP_TOL)
    assert math.isclose(at_one[1], b[1], abs_tol=LERP_TOL)


@pytest.mark.smoke
@given(
    st.tuples(finite_floats, finite_floats),
    st.tuples(finite_floats, finite_floats),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_lerp_midpoint_on_segment(
    a: tuple[float, float], b: tuple[float, float]
) -> None:
    """lerp(0.5) is the midpoint of a and b, which is the closest point
    on the segment from a to b to either endpoint. We assert the
    midpoint property (which is exact for any endpoints) and that the
    returned point lies on the segment (dist(a, mid) + dist(mid, b) ==
    dist(a, b)).
    """
    mid = vec2_lerp(a[0], a[1], b[0], b[1], 0.5)
    expected_mid = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]))
    assert math.isclose(mid[0], expected_mid[0], abs_tol=1e-5, rel_tol=1e-6)
    assert math.isclose(mid[1], expected_mid[1], abs_tol=1e-5, rel_tol=1e-6)

    full = vec2_length(b[0] - a[0], b[1] - a[1])
    half_left = vec2_length(mid[0] - a[0], mid[1] - a[1])
    half_right = vec2_length(b[0] - mid[0], b[1] - mid[1])
    assert math.isclose(half_left + half_right, full, abs_tol=1e-4, rel_tol=1e-5)


# ---------------------------------------------------------------------------
# Property 3: vec2_normalize returns a unit vector.
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@given(nonzero_direction)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_normalize_magnitude_is_one(v: tuple[float, float]) -> None:
    """For any nonzero input (x, y), normalize(x, y) returns a unit vector."""
    nx, ny = vec2_normalize(v[0], v[1])
    assert math.isclose(
        vec2_length(nx, ny), 1.0, abs_tol=1e-5, rel_tol=1e-5
    ), f"normalize({v}) = ({nx}, {ny}); length should be 1.0"


@pytest.mark.smoke
@given(nonzero_direction)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_vec2_normalize_preserves_direction(v: tuple[float, float]) -> None:
    """normalize(v) must be parallel to v (positive scalar multiple).

    We check the cross product of (x, y) and (nx, ny) is zero -- a
    90-degree component would indicate a sign or swap bug.
    """
    nx, ny = vec2_normalize(v[0], v[1])
    cross = v[0] * ny - v[1] * nx
    # Use a relative tolerance scaled by the input magnitude so that
    # tiny floats and huge floats are both treated fairly.
    scale = max(1.0, vec2_length(v[0], v[1]))
    assert abs(cross) <= 1e-5 * scale, f"normalize rotated the input: cross={cross}, v={v}, n=({nx}, {ny})"


# ---------------------------------------------------------------------------
# Property 4: collision detection is symmetric.
# ---------------------------------------------------------------------------


def _collides(
    bullets: Iterable[tuple[int, float, float, float, float]],
    enemies: Iterable[tuple[int, float, float, float, float]],
) -> set[tuple[int, int]]:
    """Run a batch collision pass and return the (bullet_id, enemy_id) hit set."""
    return set(batch_collide_bullets_vs_entities(list(bullets), list(enemies), cell_size=64))


@pytest.mark.smoke
@given(
    # Ids must be unique within each side: production code uses
    # ``eid = -i - 1`` for enemies and the bullet list index for
    # bullets, both of which are unique. The Rust spatial hash uses
    # ``HashMap<i32, AABB>`` internally, so a duplicate id would
    # silently overwrite the first entry and break AABB symmetry for
    # that input. The Python fallback handles duplicates correctly,
    # but the Rust fast-path is the production code path.
    st.lists(bullet_spec, min_size=1, max_size=6, unique_by=lambda b: b[0]),
    st.lists(enemy_spec, min_size=1, max_size=6, unique_by=lambda e: e[0]),
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_collision_is_symmetric(
    bullets: list[tuple[int, float, float, float, float]],
    enemies: list[tuple[int, float, float, float, float]],
) -> None:
    """If bullet A hits enemy B, then ``(B, A)``-shaped query should
    also report a hit. The AABB intersection is intrinsically symmetric
    (A.intersects(B) iff B.intersects(A)), so the test pins the
    invariant against any future refactor that breaks the symmetry,
    e.g. by accidentally including bullet-specific masks.
    """
    forward = _collides(bullets, enemies)
    # Swap roles: every enemy becomes a "bullet" and vice versa, with
    # swapped AABBs. If the AABB intersection is symmetric the hit
    # set should map 1-to-1 under the swap.
    swapped_hits = _collides(
        [(eid, ex, ey, ew, eh) for eid, ex, ey, ew, eh in enemies],
        [(bid, bx, by, bw, bh) for bid, bx, by, bw, bh in bullets],
    )
    expected_swapped = {(eid, bid) for bid, eid in forward}
    assert swapped_hits == expected_swapped, (
        f"collision is not symmetric:\n"
        f"  forward  = {sorted(forward)}\n"
        f"  swapped  = {sorted(swapped_hits)}\n"
        f"  expected = {sorted(expected_swapped)}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
