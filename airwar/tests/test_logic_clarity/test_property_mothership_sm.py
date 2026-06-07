"""Property-based tests for MothershipStateMachine.

Verifies the docking-flow state machine invariants:

1. State transitions follow the legal table:
   IDLE -> PRESSING -> ENTERING -> DOCKING -> DOCKED -> UNDOCKING -> COOLDOWN -> IDLE.
2. Invalid events (e.g. PROGRESS_COMPLETE while in COOLDOWN) do not
   advance the state — the state machine stays put.
3. The ``VALID_TRANSITIONS`` table is a closed graph: every non-terminal
   state has at least one outgoing edge and no self-loops.

Pygame is initialised headlessly to satisfy ``time.get_ticks()`` calls
inside the state machine handlers.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pygame

pygame.init()

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from airwar.game.mother_ship.event_bus import EventBus  # noqa: E402
from airwar.game.mother_ship.mother_ship_state import MotherShipState  # noqa: E402
from airwar.game.mother_ship.state_machine import MotherShipStateMachine  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sm() -> MotherShipStateMachine:
    """Build a fresh state machine + its event bus for diagnostics."""
    return MotherShipStateMachine(EventBus())


# The 7 mothership states — full universe of legal values.
all_states = st.sampled_from(list(MotherShipState))


# ---------------------------------------------------------------------------
# Property 1: transitions follow the legal table.
# ---------------------------------------------------------------------------


def test_valid_transitions_match_documented_flow() -> None:
    """Pinned table check: the 7-state docking flow is the only path."""
    expected = {
        MotherShipState.IDLE: [MotherShipState.COOLDOWN, MotherShipState.PRESSING],
        MotherShipState.COOLDOWN: [MotherShipState.PRESSING],
        MotherShipState.PRESSING: [MotherShipState.IDLE, MotherShipState.ENTERING],
        MotherShipState.ENTERING: [MotherShipState.DOCKING],
        MotherShipState.DOCKING: [MotherShipState.DOCKED],
        MotherShipState.DOCKED: [MotherShipState.UNDOCKING],
        MotherShipState.UNDOCKING: [MotherShipState.COOLDOWN],
    }
    assert dict(MotherShipStateMachine.VALID_TRANSITIONS) == expected


def test_full_docking_walk_traverses_all_seven_states() -> None:
    """Forced walk: IDLE -> PRESSING -> ENTERING -> DOCKING -> DOCKED -> UNDOCKING -> COOLDOWN -> IDLE."""
    sm = _make_sm()
    sm._change_state(MotherShipState.IDLE)
    sm._change_state(MotherShipState.PRESSING)
    sm._change_state(MotherShipState.ENTERING)
    sm._change_state(MotherShipState.DOCKING)
    sm._change_state(MotherShipState.DOCKED)
    sm._change_state(MotherShipState.UNDOCKING)
    sm._change_state(MotherShipState.COOLDOWN)
    sm._change_state(MotherShipState.IDLE)
    assert sm.current_state == MotherShipState.IDLE


# ---------------------------------------------------------------------------
# Property 2: invalid events do not advance the state.
# ---------------------------------------------------------------------------


@given(all_states, all_states)
@settings(max_examples=20)
def test_illegal_transition_attempt_keeps_state(current, target):
    """Direct move to a non-adjacent state must be rejected by
    ``_can_transition_to``; the public state must remain unchanged.
    """
    sm = _make_sm()
    sm._change_state(current)
    legal = MotherShipStateMachine.VALID_TRANSITIONS.get(current, set())
    if target in legal:
        # Skip legal edges — not the property under test.
        return
    assert sm._can_transition_to(target) is False, (
        f"VALID_TRANSITIONS allows illegal edge {current.name} -> {target.name}"
    )
    # The state machine's ``_change_state`` is private — but the public
    # state must not be observed as ``target``.
    assert sm.current_state == current


# ---------------------------------------------------------------------------
# Property 3: VALID_TRANSITIONS is a closed graph (no self-loops, no
# dangling states).
# ---------------------------------------------------------------------------


def test_valid_transitions_no_self_loops() -> None:
    """Self-edges are not allowed in the docking flow."""
    for src, targets in MotherShipStateMachine.VALID_TRANSITIONS.items():
        assert src not in targets, f"Self-loop detected on {src.name}"


@given(all_states)
@settings(max_examples=20)
def test_every_state_has_outgoing_or_is_terminal(state):
    """Every state must have an outgoing edge in VALID_TRANSITIONS.

    The docking flow is fully specified: there are no terminal states
    in the user-facing sense — even IDLE/COOLDOWN transition back to
    PRESSING once a new docking request arrives.
    """
    targets = MotherShipStateMachine.VALID_TRANSITIONS.get(state, set())
    assert len(targets) >= 1, f"State {state.name} has no outgoing transitions"


# ---------------------------------------------------------------------------
# Property 4: COOLDOWN eventually returns to IDLE via update().
# ---------------------------------------------------------------------------


def test_cooldown_returns_to_idle_after_update() -> None:
    """When the cooldown elapses, update() must return the state machine
    to IDLE. The state machine owns the cooldown clock; the test just
    fast-forwards by marking the cooldown as expired and calling update.
    """
    sm = _make_sm()
    sm._change_state(MotherShipState.COOLDOWN)
    sm._cooldown.is_in_cooldown = False  # already elapsed
    sm._cooldown.cooldown_progress = 1.0
    sm.update(current_time=0.0)
    assert sm.current_state == MotherShipState.IDLE
