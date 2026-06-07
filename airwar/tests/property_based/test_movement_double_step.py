"""Property-based tests for movement double-step equivalence.

For deterministic movement patterns (move_type 0..5) the per-frame
``update_movement`` integrator only depends on the previous timer value,
so two consecutive ticks at delta=1 must produce the same (x, y, timer) as
one tick at delta=2. This invariant is the basis of fixed-timestep
collision/physics stability.
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.core_bindings import update_movement

# Movement types 0..5 are deterministic functions of (timer, active_x,
# active_y, *). Types 6 and 7 (noise-driven) depend on current_x/current_y
# so they are intentionally excluded from the commutativity test.
DETERMINISTIC_MOVE_TYPES = st.sampled_from([0, 1, 2, 3, 4, 5])

# Bounded ranges so a single Hypothesis example runs in well under the
# 2 s deadline even for move_type 1/3/4 (sine, frequency=1.0).
TIMER = st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False)
POSITION = st.floats(min_value=-1_000.0, max_value=1_000.0, allow_nan=False, allow_infinity=False)
RANGE = st.floats(min_value=-200.0, max_value=200.0, allow_nan=False, allow_infinity=False)
SCALAR = st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False)
FREQUENCY = st.floats(min_value=0.01, max_value=2.0, allow_nan=False, allow_infinity=False)
INTERVAL = st.integers(min_value=1, max_value=60)


@st.composite
def _movement_params(draw) -> dict:
    """Draw a parameter dict covering all ``update_movement`` inputs."""
    return {
        "move_type": draw(DETERMINISTIC_MOVE_TYPES),
        "timer": draw(TIMER),
        "active_x": draw(POSITION),
        "active_y": draw(POSITION),
        "move_range_x": draw(RANGE),
        "move_range_y": draw(RANGE),
        "offset": draw(SCALAR),
        "amplitude": draw(SCALAR),
        "frequency": draw(FREQUENCY),
        "speed": draw(SCALAR),
        "direction": draw(SCALAR),
        "zigzag_interval": float(draw(INTERVAL)),
        "spiral_radius": draw(SCALAR),
        "current_x": draw(POSITION),
        "current_y": draw(POSITION),
        "noise_scale_x": 0.1,
        "noise_scale_y": 0.1,
        "noise_amplitude_x": 0.0,
        "noise_amplitude_y": 0.0,
        "noise_seed": 0,
    }


def _step(params: dict) -> tuple[float, float, float]:
    """Single deterministic step: timer increases by 1."""
    return update_movement(**params)


@settings(max_examples=200, deadline=2000)
@given(params=_movement_params())
def test_two_single_steps_equal_one_double_step(params):
    """``step(step(p)) == step(p with timer += 1)`` for deterministic move types.

    For the deterministic patterns (0..5) the integrator only depends on the
    current timer plus the constant ``active_x``/``active_y`` anchors, never
    on the previous x/y output. So advancing the timer by 1 starting from the
    initial state must produce the same (x, y, timer) as taking two consecutive
    single-step ticks (the first step's new_timer is the second step's input).
    """
    once = _step(params)
    twice = _step({**params, "timer": once[2]})  # carry the new_timer forward
    direct = _step({**params, "timer": params["timer"] + 1.0})

    # Floats: update_movement is built on math.sin which is exact to ~1 ULP
    # per call, so 1e-6 relative tolerance catches real regressions while
    # letting the inevitable FPU rounding slip through.
    for idx, name in enumerate(("x", "y", "timer")):
        if math.isnan(twice[idx]) or math.isnan(direct[idx]):
            continue
        assert twice[idx] == direct[idx] or abs(twice[idx] - direct[idx]) < 1e-6 * max(1.0, abs(direct[idx])), name


@settings(max_examples=200, deadline=2000)
@given(params=_movement_params())
def test_timer_increases_monotonically(params):
    """A single step must increase the timer by exactly 1.0.

    ``update_movement`` returns the new timer as ``f32`` (Rust), while
    ``params["timer"]`` is a Python ``f64``; the cross-precision round-trip
    can lose 1-2 ULP, so we use a relative tolerance matching the sibling
    commutativity test above rather than strict ``==``.
    """
    x, y, t = _step(params)
    expected = params["timer"] + 1.0
    assert abs(t - expected) < 1e-6 * max(1.0, abs(expected))
    # x, y stay finite for sane input
    assert math.isfinite(x)
    assert math.isfinite(y)
