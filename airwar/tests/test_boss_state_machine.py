"""Boss state machine invariant tests.

These tests pin the behavioral contract of :class:`BossStateMachine` so
that future refactors cannot silently break the enrage sequence or the
damage-lock policy.

The five invariants covered (one per test, see design doc §4.5):

1. enrage is idempotent (re-trigger does nothing)
2. enrage health-lock clamps incoming damage at the lock value
3. enrage visual intensity is non-negative and bounded
4. state machine can return to ACTIVE after the enrage release hold
5. ESCAPED is reachable from ACTIVE only via ``mark_escaped``
"""

from __future__ import annotations

import os
import sys

import pytest

# Headless-friendly display setup
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Ensure repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from airwar.entities import Boss, BossData
from airwar.entities.enemy.boss import (
    ENRAGE_TRIGGER_RATIO,
    BossState,
    IllegalBossTransition,
)


def _make_boss(health: int = 1000) -> Boss:
    """Create a non-entering boss with the given max health."""
    boss = Boss(500, 120, BossData(health=health))
    boss.is_entering = False
    return boss


def test_enrage_trigger_is_idempotent() -> None:
    """Calling trigger_enrage twice must not double-set timers or state."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.trigger_enrage((600.0, 400.0))
    first_timer = sm.enrage_timer
    assert sm.enraged is True
    assert sm.state == BossState.ENRAGE_TRANSITION

    # Second call must be a no-op.
    sm.trigger_enrage((0.0, 0.0))
    assert sm.enrage_timer == first_timer
    assert sm.state == BossState.ENRAGE_TRANSITION
    # Snapshot target must NOT change on the second call.
    assert sm.enrage_snapshot_target == (600.0, 400.0)


def test_enrage_health_lock_clamps_damage_to_lock_value() -> None:
    """Damage that would drop health below the enrage lock must clamp at it.

    This invariant only fires when the boss is NOT yet enraged (the
    pre-enrage clamp). Once enrage is active, the lock clamps damage
    differently (keeps health at or above the lock).
    """
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    # Pre-set the lock value (normally this would happen when the boss
    # triggers enrage at 30% health, but for this test we want to check
    # the pre-enrage clamp behavior).
    sm._enrage_health_lock_value = int(1000 * ENRAGE_TRIGGER_RATIO)
    sm._enrage_health_lock_active = False  # not yet enraged
    # Set health just above the lock so a normal hit would push it over.
    boss.health = sm._enrage_health_lock_value + 5
    new_health, score = sm.compute_take_damage(damage=10)
    # Health must clamp at the lock value; no score awarded.
    assert new_health == sm._enrage_health_lock_value
    assert score == 0


def test_boss_take_damage_lethal_when_never_enraged() -> None:
    """A lethal hit on a boss that never triggered enrage must kill it.

    Regression: before the fix, ``_enrage_health_lock_value`` defaulted to 0
    and the pre-enrage branch swallowed the lethal hit, returning score=0 so
    ``mark_dead()`` never fired and the boss froze at HP=0.
    """
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    # Lock value stays at 0 (never enrage-triggered).
    assert sm._enrage_health_lock_value == 0
    # Lethal damage via the full take_damage path (triggers mark_dead).
    score = boss.take_damage(1000)
    assert score > 0, "Lethal hit must return positive score so mark_dead() fires"
    assert boss.active is False
    assert boss._state.state == BossState.DEAD


def test_enrage_visual_intensity_is_bounded() -> None:
    """Visual intensity must be in [0, 0.88] at all times."""
    boss = _make_boss(health=1000)
    sm = boss._state
    assert sm.enrage_visual_intensity() == 0.0

    sm.trigger_enrage((600.0, 400.0))
    assert 0.0 <= sm.enrage_visual_intensity() <= 0.88

    # Simulate full enrage progression.
    sm._enrage_timer = 0
    sm._enrage_transition_timer = 0
    sm.finish_enrage_transition()  # ENRAGE_TRANSITION -> ENRAGE_ACTIVE
    assert 0.0 <= sm.enrage_visual_intensity() <= 0.88

    # Release hold should produce a non-zero but bounded value.
    sm.begin_enrage_release_hold((0.0, 0.0))
    assert 0.0 <= sm.enrage_visual_intensity() <= 0.74


def test_state_can_return_to_active_after_enrage_release_hold() -> None:
    """After enrage bullets are released, the boss must return to ACTIVE."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    sm._enrage_timer = 0
    sm.begin_enrage_release_hold((0.0, 0.0))
    assert sm.state == BossState.ENRAGE_RELEASE_HOLD

    # After the hold timer drains, the enrage return begins.
    sm._enrage_release_hold_timer = 0
    sm.begin_enrage_return((10.0, 10.0), (20.0, 20.0))
    assert sm.state == BossState.ENRAGE_RETURN
    sm._enrage_return_timer = 0
    sm.finish_enrage_return()
    assert sm.state == BossState.ACTIVE


def test_escape_only_reachable_via_mark_escaped() -> None:
    """The ESCAPING state must only be set by mark_escaped()."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    assert sm.state == BossState.ACTIVE

    sm.mark_escaped()
    assert sm.state == BossState.ESCAPING


def test_take_damage_returns_score_when_health_drops_to_zero() -> None:
    """After disabling the enrage lock, a killing blow returns the score."""
    boss = _make_boss(health=1000)
    boss._enrage_health_lock_active = False
    boss._enraged = True
    score = boss.take_damage(boss.health)
    assert score == 5000  # default BossData.score
    assert boss.active is False
    assert boss._state.state == BossState.DEAD


def test_compute_take_damage_ignores_negative_or_none_damage() -> None:
    """Negative or None damage must be a no-op (defensive)."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    before = boss.health
    new_health, score = sm.compute_take_damage(damage=-50)
    assert new_health == before
    assert score == 0
    new_health, score = sm.compute_take_damage(damage=None)
    assert new_health == before
    assert score == 0


# ---------------------------------------------------------------------------
# Legal-edge table tests (P0-4 — mirror Player HSM pattern).
#
# Each transition method on ``BossStateMachine`` consults
# ``_BOSS_TRANSITIONS`` and raises :class:`IllegalBossTransition` for
# any move not in the legal-edge table. The happy-path tests below
# walk one full forward path through the boss lifecycle; the illegal
# tests probe edges the production code must never allow.
# ---------------------------------------------------------------------------


def test_happy_path_legal_transition_entering_to_active() -> None:
    """ENTERING -> ACTIVE is the canonical entry-exit edge."""
    boss = _make_boss(health=1000)
    sm = boss._state
    assert sm.state == BossState.ENTERING
    sm.finish_entry()
    assert sm.state == BossState.ACTIVE


def test_happy_path_legal_transition_active_to_enrage_transition() -> None:
    """ACTIVE -> ENRAGE_TRANSITION is the enrage entry point."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    assert sm.state == BossState.ACTIVE
    sm.trigger_enrage((600.0, 400.0))
    assert sm.state == BossState.ENRAGE_TRANSITION


def test_happy_path_legal_transition_enrage_transition_to_active_via_return() -> None:
    """ENRAGE_TRANSITION -> ENRAGE_ACTIVE -> ... -> ENRAGE_RETURN -> ACTIVE."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    assert sm.state == BossState.ENRAGE_ACTIVE
    sm.begin_enrage_release_hold((0.0, 0.0))
    assert sm.state == BossState.ENRAGE_RELEASE_HOLD
    sm.begin_enrage_return((10.0, 10.0), (20.0, 20.0))
    assert sm.state == BossState.ENRAGE_RETURN
    sm.finish_enrage_return()
    assert sm.state == BossState.ACTIVE


def test_happy_path_legal_transition_active_to_escaping() -> None:
    """ACTIVE -> ESCAPING is reached only via mark_escaped()."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.mark_escaped()
    assert sm.state == BossState.ESCAPING


def test_happy_path_legal_transition_active_to_dead() -> None:
    """ACTIVE -> DEAD is the kill edge (used by Boss.take_damage)."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.mark_dead()
    assert sm.state == BossState.DEAD


def test_happy_path_legal_transition_enrage_transition_to_enrage_active() -> None:
    """ENRAGE_TRANSITION -> ENRAGE_ACTIVE is finish_enrage_transition()."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    assert sm.state == BossState.ENRAGE_ACTIVE


def test_happy_path_legal_transition_enrage_active_to_release_hold() -> None:
    """ENRAGE_ACTIVE -> ENRAGE_RELEASE_HOLD is begin_enrage_release_hold()."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    sm.begin_enrage_release_hold((0.0, 0.0))
    assert sm.state == BossState.ENRAGE_RELEASE_HOLD


def test_happy_path_legal_transition_enrage_release_hold_to_enrage_return() -> None:
    """ENRAGE_RELEASE_HOLD -> ENRAGE_RETURN is begin_enrage_return()."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    sm.begin_enrage_release_hold((0.0, 0.0))
    sm.begin_enrage_return((10.0, 10.0), (20.0, 20.0))
    assert sm.state == BossState.ENRAGE_RETURN


def test_illegal_transition_finish_entry_from_active_is_idempotent() -> None:
    """finish_entry() on the target state (ACTIVE) is a no-op (idempotent).

    Mirrors the Player HSM's pattern: a self-loop in the legal-edge
    table is treated as a safe idempotent call. The transfer must
    not raise and must not change the state.
    """
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()  # ENTERING -> ACTIVE
    assert sm.state == BossState.ACTIVE
    # Second call is a self-loop: no-op, no raise.
    sm.finish_entry()
    assert sm.state == BossState.ACTIVE


def test_illegal_transition_mark_escaped_from_entering_raises() -> None:
    """mark_escaped() is not legal from ENTERING (must finish entry first)."""
    boss = _make_boss(health=1000)
    sm = boss._state
    assert sm.state == BossState.ENTERING
    with pytest.raises(IllegalBossTransition):
        sm.mark_escaped()
    # State must NOT have changed.
    assert sm.state == BossState.ENTERING


def test_illegal_transition_begin_enrage_release_hold_from_transition_raises() -> None:
    """ENRAGE_TRANSITION -> ENRAGE_RELEASE_HOLD is not a legal edge.

    Production code must call finish_enrage_transition() first to land
    in ENRAGE_ACTIVE; skipping the transition state is a bug.
    """
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))  # -> ENRAGE_TRANSITION
    assert sm.state == BossState.ENRAGE_TRANSITION
    with pytest.raises(IllegalBossTransition):
        sm.begin_enrage_release_hold((0.0, 0.0))
    assert sm.state == BossState.ENRAGE_TRANSITION


def test_illegal_transition_dead_state_is_terminal() -> None:
    """DEAD is terminal: no transfer method may move the state onward."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.mark_dead()
    assert sm.state == BossState.DEAD
    # Every transfer method must reject the move.
    with pytest.raises(IllegalBossTransition):
        sm.finish_entry()
    with pytest.raises(IllegalBossTransition):
        sm.mark_escaped()
    with pytest.raises(IllegalBossTransition):
        sm.trigger_enrage((0.0, 0.0))
    with pytest.raises(IllegalBossTransition):
        sm.finish_enrage_transition()
    with pytest.raises(IllegalBossTransition):
        sm.begin_enrage_release_hold((0.0, 0.0))
    with pytest.raises(IllegalBossTransition):
        sm.begin_enrage_return((0.0, 0.0), (1.0, 1.0))
    with pytest.raises(IllegalBossTransition):
        sm.finish_enrage_return()
    # State must still be DEAD after every rejected attempt.
    assert sm.state == BossState.DEAD


def test_illegal_transition_enrage_active_to_active_skips_return() -> None:
    """ENRAGE_ACTIVE -> ACTIVE is not a legal edge (must go via RETURN)."""
    boss = _make_boss(health=1000)
    sm = boss._state
    sm.finish_entry()
    sm.trigger_enrage((600.0, 400.0))
    sm.finish_enrage_transition()
    assert sm.state == BossState.ENRAGE_ACTIVE
    with pytest.raises(IllegalBossTransition):
        sm.finish_enrage_return()  # No-op; wrong source state
    assert sm.state == BossState.ENRAGE_ACTIVE
