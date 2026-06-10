"""Player state machine invariant tests.

These tests pin the legal-edge table of the player's alive-substate
HSM. Any future change that adds or removes an edge must update the
test accordingly — the whole point of the HSM is to make illegal
transitions impossible.

The five invariants covered (one per test, mirroring design §6.4):

1. NORMAL -> DOCKED is a legal transition (player can dock)
2. DASHING -> SHIELDED is illegal (must pass through NORMAL)
3. Respawn transitions return to RESPAWN_INVINCIBLE then NORMAL
4. Shield expiration auto-transitions back to NORMAL
5. Dead is a terminal state
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from airwar.entities.player_state import (
    IllegalPlayerTransition,
    PlayerAliveState,
    PlayerState,
    PlayerStateMachine,
)

# Player HSM legal-transition table — every gameplay action funnels through
# this. Pure logic, no rendering. Smoke these so HSM regressions fail fast.
pytestmark = pytest.mark.smoke


class _StubPlayer:
    """Minimal duck-typed Player that satisfies PlayerStateMachine.__init__."""


def _make_sm() -> PlayerStateMachine:
    return PlayerStateMachine(_StubPlayer())


def test_normal_to_docked_is_legal() -> None:
    """NORMAL -> DOCKED must be allowed (player docks with mothership)."""
    sm = _make_sm()
    assert sm.alive_substate == PlayerAliveState.NORMAL
    sm.transition_substate(PlayerAliveState.DOCKED)
    assert sm.alive_substate == PlayerAliveState.DOCKED
    assert sm.is_docked() is True


def test_dashing_to_shielded_is_illegal() -> None:
    """DASHING -> SHIELDED is not in the legal-edge table.

    A dash must end (DASHING -> NORMAL) before the player can take
    cover. Trying the direct edge must raise IllegalPlayerTransition.
    """
    sm = _make_sm()
    sm.transition_substate(PlayerAliveState.DASHING)
    with __import__("pytest").raises(IllegalPlayerTransition):
        sm.transition_substate(PlayerAliveState.SHIELDED)
    # Confirm we are still in DASHING (no partial state mutation).
    assert sm.alive_substate == PlayerAliveState.DASHING


def test_respawn_invincibility_lifecycle() -> None:
    """respawn() puts the player in RESPAWN_INVINCIBLE; tick drains it."""
    sm = _make_sm()
    sm.mark_dying()
    sm.mark_dead()
    sm.respawn()
    assert sm.state == PlayerState.ALIVE
    assert sm.alive_substate == PlayerAliveState.RESPAWN_INVINCIBLE
    assert sm.is_respawn_invincible() is True


def test_shield_expiration_returns_to_normal() -> None:
    """A shield with duration=1 must auto-clear on tick_shield()."""
    sm = _make_sm()
    sm.activate_shield(duration=1)
    assert sm.alive_substate == PlayerAliveState.SHIELDED
    sm.tick_shield()
    assert sm.alive_substate == PlayerAliveState.NORMAL
    assert sm.is_shielded() is False


def test_dead_is_terminal() -> None:
    """Once in DEAD, mark_dead() is a no-op and the state stays DEAD."""
    sm = _make_sm()
    sm.mark_dead()
    assert sm.state == PlayerState.DEAD
    sm.mark_dead()  # idempotent
    assert sm.state == PlayerState.DEAD


def test_enter_boost_from_dash_raises() -> None:
    """F03 S6: Boosting while dashing now raises (was silent no-op).

    Dash preempts boost; callers must exit DASHING first.
    """
    sm = _make_sm()
    sm.transition_substate(PlayerAliveState.DASHING)
    with pytest.raises(IllegalPlayerTransition):
        sm.enter_boost()
    # State unchanged after the rejected attempt
    assert sm.alive_substate == PlayerAliveState.DASHING
    assert sm.is_boosting() is False


def test_should_lock_controls_in_dock_and_dash() -> None:
    """Top-level predicate: lock controls while docked or dashing."""
    sm = _make_sm()
    assert sm.should_lock_controls() is False
    sm.enter_dock()
    assert sm.should_lock_controls() is True
    sm.exit_dock()
    assert sm.should_lock_controls() is False
    sm.enter_dash()
    assert sm.should_lock_controls() is True
    sm.exit_dash()
    assert sm.should_lock_controls() is False


def test_force_substate_bypasses_legal_table() -> None:
    """force_substate is the documented escape hatch for save/restore."""
    sm = _make_sm()
    sm.transition_substate(PlayerAliveState.DASHING)
    # DASHING -> SHIELDED is illegal via the table, but force_substate works.
    sm.force_substate(PlayerAliveState.SHIELDED)
    assert sm.alive_substate == PlayerAliveState.SHIELDED
