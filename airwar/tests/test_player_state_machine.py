"""Player state machine invariant tests.

These tests pin the legal-edge table of the player's alive-substate
HSM. Any future change that adds or removes an edge must update the
test accordingly — the whole point of the HSM is to make illegal
transitions impossible.

The four invariants covered (mirroring design §6.4):

1. NORMAL -> DOCKED is a legal transition (player can dock)
2. Respawn transitions return to RESPAWN_INVINCIBLE then NORMAL
3. Shield expiration auto-transitions back to NORMAL
4. Dead is a terminal state

Note: phase dash lives in the orthogonal ``PlayerPhaseDash`` subsystem,
not in this HSM, so the DASHING substate was removed in M-6.
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
from airwar.tests.conftest import StubPlayerForStateMachine

# Player HSM legal-transition table — every gameplay action funnels through
# this. Pure logic, no rendering. Smoke these so HSM regressions fail fast.
pytestmark = pytest.mark.smoke


def _make_sm() -> PlayerStateMachine:
    return PlayerStateMachine(StubPlayerForStateMachine())


def test_normal_to_docked_is_legal() -> None:
    """NORMAL -> DOCKED must be allowed (player docks with mothership)."""
    sm = _make_sm()
    assert sm.alive_substate == PlayerAliveState.NORMAL
    sm.transition_substate(PlayerAliveState.DOCKED)
    assert sm.alive_substate == PlayerAliveState.DOCKED
    assert sm.is_docked() is True


def test_docked_to_shielded_is_illegal() -> None:
    """DOCKED -> SHIELDED is not in the legal-edge table.

    The player must undock (DOCKED -> NORMAL) before taking cover.
    Trying the direct edge must raise IllegalPlayerTransition.
    Replaces the pre-M-6 `DASHING -> SHIELDED` test (DASHING was
    removed when the orthogonal PlayerPhaseDash subsystem took over).
    """
    sm = _make_sm()
    sm.transition_substate(PlayerAliveState.DOCKED)
    with __import__("pytest").raises(IllegalPlayerTransition):
        sm.transition_substate(PlayerAliveState.SHIELDED)
    # Confirm we are still in DOCKED (no partial state mutation).
    assert sm.alive_substate == PlayerAliveState.DOCKED


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


def test_enter_boost_from_shield_raises() -> None:
    """F03 S6: Boosting while shielded now raises (was silent no-op).

    Shield preempts boost; callers must deactivate the shield first.
    Replaces the pre-M-6 `enter_boost_from_dash` test (DASHING was
    removed when the orthogonal PlayerPhaseDash subsystem took over).
    """
    sm = _make_sm()
    sm.activate_shield(duration=10)
    with pytest.raises(IllegalPlayerTransition):
        sm.enter_boost()
    # State unchanged after the rejected attempt
    assert sm.alive_substate == PlayerAliveState.SHIELDED
    assert sm.is_boosting() is False


def test_should_lock_controls_when_docked() -> None:
    """Top-level predicate: lock controls while docked.

    Dash moved to the orthogonal ``PlayerPhaseDash`` subsystem in M-6, so
    this test no longer covers the dash branch — it pins the only
    remaining locked-controls substate (DOCKED).
    """
    sm = _make_sm()
    assert sm.should_lock_controls() is False
    sm.enter_dock()
    assert sm.should_lock_controls() is True
    sm.exit_dock()
    assert sm.should_lock_controls() is False


def test_force_substate_bypasses_legal_table() -> None:
    """force_substate is the documented escape hatch for save/restore."""
    sm = _make_sm()
    sm.transition_substate(PlayerAliveState.DOCKED)
    # DOCKED -> SHIELDED is illegal via the table, but force_substate works.
    sm.force_substate(PlayerAliveState.SHIELDED)
    assert sm.alive_substate == PlayerAliveState.SHIELDED
