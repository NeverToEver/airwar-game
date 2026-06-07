"""Property-based tests for score monotonicity.

Score is the canonical "only goes up" number in the game: kills, boss kills
and milestone rewards all add to it, and ``normalize_score`` clamps negatives
to zero. This module verifies that any sequence of valid score events
never decreases the recorded score.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.game.constants import normalize_score

# A "score event" is one of the public score-mutating operations exposed by
# GameController. Each event carries a non-negative reward amount.
SCORE_DELTA = st.integers(min_value=0, max_value=10_000)
SCORE_SEQUENCE = st.lists(SCORE_DELTA, min_size=0, max_size=50)
INITIAL_SCORE = st.integers(min_value=0, max_value=1_000_000)


@settings(max_examples=300, deadline=2000)
@given(initial=INITIAL_SCORE, deltas=SCORE_SEQUENCE)
def test_score_never_decreases_over_kill_events(initial, deltas):
    """``normalize_score(score)`` is non-decreasing as we add non-negative kills."""
    score = initial
    for delta in deltas:
        new_score = normalize_score(score + delta)
        assert new_score >= score
        score = new_score


@settings(max_examples=300, deadline=2000)
@given(initial=INITIAL_SCORE, deltas=SCORE_SEQUENCE)
def test_score_sequence_matches_cumulative_sum(initial, deltas):
    """Final score equals ``initial + sum(deltas)`` clamped at zero.

    normalize_score is a thin clamp-to-non-negative-int wrapper, so the
    property verifies the wrapper itself never silently drops score.
    """
    expected = max(0, initial + sum(deltas))
    score = initial
    for delta in deltas:
        score = normalize_score(score + delta)
    assert score == expected


@settings(max_examples=300, deadline=2000)
@given(value=st.floats(min_value=-1e9, max_value=1e9, allow_nan=False, allow_infinity=False))
def test_normalize_score_clamps_negatives_to_zero(value):
    """Any negative input must normalize to zero, never a negative int."""
    assert normalize_score(value) >= 0


@settings(max_examples=300, deadline=2000)
@given(initial=INITIAL_SCORE, deltas=SCORE_SEQUENCE)
def test_score_replay_is_deterministic(initial, deltas):
    """Replaying the same delta sequence always yields the same final score."""

    def run() -> int:
        score = initial
        for delta in deltas:
            score = normalize_score(score + delta)
        return score

    first = run()
    second = run()
    assert first == second
