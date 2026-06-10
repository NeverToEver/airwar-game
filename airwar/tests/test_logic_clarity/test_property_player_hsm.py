"""Property-based tests for Player HSM (PlayerStateMachine).

Verifies the invariants of the alive-substate legal-edge table using
Hypothesis. Each property captures a contract that any future refactor
must not break:

1. After any sequence of legal transitions, the substate is one of
   :class:`PlayerAliveState` values.
2. Illegal moves (not in ``_ALIVE_TRANSITIONS``) raise
   :class:`IllegalPlayerTransition`.
3. ``force_substate`` bypasses the table without raising.
4. Shield duration decreases monotonically while SHIELDED is active.

The five substates (NORMAL/BOOSTING/DASHING/SHIELDED/DOCKED/RESPAWN_INVINCIBLE)
are the universe of legal values — the table only ever moves between
them, never outside.
"""

from __future__ import annotations

import os
import sys
from itertools import pairwise

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.entities.player_state import (
    IllegalPlayerTransition,
    PlayerAliveState,
    PlayerStateMachine,
)
from airwar.tests.conftest import StubPlayerForStateMachine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sm() -> PlayerStateMachine:
    return PlayerStateMachine(StubPlayerForStateMachine())


# Strategy: any sequence of substates (legal or illegal). Hypothesis will
# shrink failed cases to the minimal counterexample.
substate_strategy = st.sampled_from(list(PlayerAliveState))
sequence_strategy = st.lists(substate_strategy, max_size=8)


# Legal-edge table copy — must stay in lock-step with production code.
def _legal_targets(current: PlayerAliveState) -> set[PlayerAliveState]:
    return {
        PlayerAliveState.NORMAL: {
            PlayerAliveState.BOOSTING,
            PlayerAliveState.SHIELDED,
            PlayerAliveState.DOCKED,
            PlayerAliveState.RESPAWN_INVINCIBLE,
            PlayerAliveState.NORMAL,
        },
        PlayerAliveState.BOOSTING: {
            PlayerAliveState.NORMAL,
            PlayerAliveState.SHIELDED,
            PlayerAliveState.DOCKED,
            PlayerAliveState.RESPAWN_INVINCIBLE,
        },
        PlayerAliveState.SHIELDED: {
            PlayerAliveState.NORMAL,
            PlayerAliveState.BOOSTING,
            PlayerAliveState.DOCKED,
            PlayerAliveState.RESPAWN_INVINCIBLE,
        },
        PlayerAliveState.DOCKED: {
            PlayerAliveState.NORMAL,
            PlayerAliveState.BOOSTING,
            PlayerAliveState.RESPAWN_INVINCIBLE,
        },
        PlayerAliveState.RESPAWN_INVINCIBLE: {
            PlayerAliveState.NORMAL,
            PlayerAliveState.BOOSTING,
            PlayerAliveState.DOCKED,
        },
    }[current]


# ---------------------------------------------------------------------------
# Property 1: After any sequence of legal transitions, substate is always
# one of the six PlayerAliveState values.
# ---------------------------------------------------------------------------


@given(sequence_strategy)
@settings(max_examples=20)
def test_legal_transitions_keep_substate_in_universe(sequence):
    """Any sequence of legal moves must end with a valid substate."""
    sm = _make_sm()
    for target in sequence:
        current = sm.alive_substate
        if target in _legal_targets(current):
            sm.transition_substate(target)
        # Illegal moves are filtered out here — covered separately below.
    assert sm.alive_substate in set(PlayerAliveState)


# ---------------------------------------------------------------------------
# Property 2: IllegalPlayerTransition is raised for any move NOT in the
# legal-edge table.
# ---------------------------------------------------------------------------


@given(substate_strategy, substate_strategy)
@settings(max_examples=20)
def test_illegal_transitions_raise(from_state, to_state):
    """Direct edge that isn't in the table must raise.

    Self-loops (from_state == to_state) are no-ops per the production
    short-circuit at line 199 of player_state.py, so they're excluded
    from this property.
    """
    sm = _make_sm()
    sm.force_substate(from_state)
    if from_state == to_state:
        # Self-loop is a documented no-op; not the property under test.
        return
    if to_state in _legal_targets(from_state):
        # Legal edge — not the property under test.
        return
    try:
        sm.transition_substate(to_state)
    except IllegalPlayerTransition:
        # State must be unchanged after the rejected attempt.
        assert sm.alive_substate == from_state
        return
    raise AssertionError(f"Expected IllegalPlayerTransition for {from_state.name} -> {to_state.name}")


# ---------------------------------------------------------------------------
# Property 3: force_substate bypasses the legal-edge table.
# ---------------------------------------------------------------------------


@given(substate_strategy, substate_strategy)
@settings(max_examples=20)
def test_force_substate_never_raises(from_state, to_state):
    """force_substate is the documented escape hatch for save/restore."""
    sm = _make_sm()
    sm.force_substate(from_state)
    sm.force_substate(to_state)  # must not raise, even for "illegal" edges
    assert sm.alive_substate == to_state


# ---------------------------------------------------------------------------
# Property 4: Shield duration decreases monotonically while SHIELDED.
# ---------------------------------------------------------------------------


@given(st.integers(min_value=1, max_value=200))
@settings(max_examples=20)
def test_shield_timer_monotonic_decrease(initial_duration):
    """tick_shield() must monotonically decrement the timer; never go below 0."""
    sm = _make_sm()
    sm.activate_shield(duration=initial_duration)
    assert sm.shield_duration == initial_duration
    observed = [sm.shield_duration]
    for _ in range(initial_duration + 5):  # over-tick on purpose
        sm.tick_shield()
        observed.append(sm.shield_duration)
    # Monotonic non-increasing
    for prev, cur in pairwise(observed):
        assert cur <= prev, f"Shield timer increased: {prev} -> {cur}"
    # Clamped at 0
    assert observed[-1] == 0
    # Once the timer hits 0 inside SHIELDED, the state must auto-revert.
    assert sm.alive_substate == PlayerAliveState.NORMAL
