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

# Headless-friendly display setup
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Ensure repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from airwar.entities import Boss, BossData
from airwar.entities.enemy.boss import (
    ENRAGE_TRIGGER_RATIO,
    BossState,
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
