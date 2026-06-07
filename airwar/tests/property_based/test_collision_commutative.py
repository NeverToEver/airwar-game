"""Property-based tests for AABB collision commutativity.

Verifies that pairwise collision detection is symmetric: colliding A against B
must produce the same result as colliding B against A, regardless of position
or size. Uses the public ``batch_collide_bullets_vs_entities`` helper from
``airwar.core_bindings`` so the test exercises the same code path as gameplay
collision detection.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.core_bindings import batch_collide_bullets_vs_entities

# Bounding box components stay well inside float32 range and avoid degenerate
# zero-area rects that could mask ordering bugs in batched collision code.
COORD = st.floats(
    min_value=-10_000.0,
    max_value=10_000.0,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)
SIZE = st.floats(min_value=0.01, max_value=500.0, allow_nan=False, allow_infinity=False, width=64)


@st.composite
def _rects(draw) -> tuple[float, float, float, float]:
    """Draw a (x, y, width, height) rectangle tuple."""
    x = draw(COORD)
    y = draw(COORD)
    w = draw(SIZE)
    h = draw(SIZE)
    return (x, y, w, h)


def _collides(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    """Return True if two rects (x, y, w, h) intersect under batched AABB collision."""
    bullets = [(1, *left)]
    entities = [(2, *right)]
    return bool(batch_collide_bullets_vs_entities(bullets, entities, cell_size=64))


@settings(max_examples=200, deadline=2000)
@given(left=_rects(), right=_rects())
def test_collide_is_commutative(left, right):
    """``collide(A, B) == collide(B, A)`` for arbitrary rects."""
    assert _collides(left, right) == _collides(right, left)


@settings(max_examples=200, deadline=2000)
@given(rect=_rects())
def test_collide_with_self_is_true(rect):
    """An AABB always collides with itself."""
    assert _collides(rect, rect) is True


@settings(max_examples=200, deadline=2000)
@given(left=_rects(), right=_rects())
def test_disjoint_rounds_are_antisymmetric(left, right):
    """When the two orderings disagree, neither side can be a strict subset result."""
    ab = _collides(left, right)
    ba = _collides(right, left)
    # Equality is the actual property; the assertion below is just a sanity
    # check that we are not silently dropping a hit due to ordering.
    assert ab == ba
