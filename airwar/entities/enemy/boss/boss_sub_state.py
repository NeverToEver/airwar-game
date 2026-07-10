"""Boss enrage sub-machine — 4-state enrage cycle + health-lock damage policy.

The sub-machine owns the enrage state beneath :class:`BossStateMachine`:

* 4 timer counters: ``_enrage_timer``, ``_enrage_transition_timer``,
  ``_enrage_release_hold_timer``, ``_enrage_return_timer``
* 5 location anchors: ``_enrage_snapshot_target``, ``_enrage_transition_origin``,
  ``_enrage_release_anchor``, ``_enrage_return_origin``, ``_enrage_return_target``
* 2 attack fields: ``_enrage_attack_timer``, ``_enrage_attack_index``
* 4 flags: ``_enraged``, ``_enrage_bullets_released``,
  ``_enrage_health_lock_active``, ``_enrage_health_lock_value``

The top-level :class:`BossStateMachine` (in :mod:`.boss_state`) delegates
enrage behavior to this class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .boss_state import (
    ENRAGE_ATTACK_INTERVAL,
    ENRAGE_ATTACK_WINDUP,
    ENRAGE_DURATION,
    ENRAGE_RELEASE_HOLD_DURATION,
    ENRAGE_RETURN_DURATION,
    ENRAGE_SLOW_FACTOR,
    ENRAGE_TRANSITION_DURATION,
    ENRAGE_TRIGGER_RATIO,
)

if TYPE_CHECKING:
    from .boss import Boss


class EnrageSubMachine:
    """Owns the enrage sub-state (timers, anchors, attack state, flags).

    The 8 transfer methods, 6 tick methods, 8 predicate methods, and
    ``compute_take_damage`` live here. The top-level ``BossStateMachine``
    is responsible for syncing the top-level ``BossState`` enum after
    each transfer; this class only knows about its own counters and
    anchors.
    """

    def __init__(self, boss: Boss) -> None:
        self._boss = boss
        # Flags
        self._enraged: bool = False
        self._enrage_bullets_released: bool = False
        self._enrage_health_lock_active: bool = False
        self._enrage_health_lock_value: int = 0
        # Timers
        self._enrage_timer: int = 0
        self._enrage_transition_timer: int = 0
        self._enrage_release_hold_timer: int = 0
        self._enrage_return_timer: int = 0
        # Location anchors
        self._enrage_snapshot_target: tuple[float, float] | None = None
        self._enrage_transition_origin: tuple[float, float] | None = None
        self._enrage_release_anchor: tuple[float, float] | None = None
        self._enrage_return_origin: tuple[float, float] | None = None
        self._enrage_return_target: tuple[float, float] | None = None
        # Attack state
        self._enrage_attack_timer: int = 0
        self._enrage_attack_index: int = 0

    # ------------------------------------------------------------------
    # Transitions (idempotent: trigger_enrage is the only guard)
    # ------------------------------------------------------------------

    def trigger_enrage(self, snapshot_target: tuple[float, float]) -> None:
        """Begin the enrage sub-machine (idempotent)."""
        if self._enraged:
            return
        self._enraged = True
        self._enrage_timer = ENRAGE_DURATION
        self._enrage_bullets_released = False
        self._enrage_health_lock_active = True
        self._enrage_health_lock_value = int(self._boss.data.health * ENRAGE_TRIGGER_RATIO)
        # Clamp current health at the lock value so the enrage sequence
        # always starts from the same checkpoint.
        if self._boss.health < self._enrage_health_lock_value:
            self._boss.health = self._enrage_health_lock_value
        self._enrage_snapshot_target = snapshot_target
        self._enrage_transition_timer = ENRAGE_TRANSITION_DURATION
        self._enrage_transition_origin = (self._boss.rect.centerx, self._boss.rect.centery)
        self._enrage_release_hold_timer = 0
        self._enrage_release_anchor = None
        self._enrage_return_timer = 0
        self._enrage_return_origin = None
        self._enrage_return_target = None
        self._enrage_attack_timer = ENRAGE_ATTACK_WINDUP
        self._enrage_attack_index = 0

    def finish_enrage_transition(self) -> None:
        """Move from ENRAGE_TRANSITION to ENRAGE_ACTIVE."""
        self._enrage_transition_timer = 0
        self._enrage_transition_origin = None

    def begin_enrage_release_hold(self, anchor: tuple[float, float]) -> None:
        """Move from ENRAGE_ACTIVE to ENRAGE_RELEASE_HOLD."""
        self._enrage_release_hold_timer = ENRAGE_RELEASE_HOLD_DURATION
        self._enrage_release_anchor = anchor
        self._enrage_bullets_released = True
        self._enrage_health_lock_active = False
        self._enrage_timer = 0

    def begin_enrage_return(
        self,
        origin: tuple[float, float],
        target: tuple[float, float],
    ) -> None:
        """Move from ENRAGE_RELEASE_HOLD to ENRAGE_RETURN."""
        self._enrage_return_timer = ENRAGE_RETURN_DURATION
        self._enrage_return_origin = origin
        self._enrage_return_target = target
        self._enrage_release_anchor = None

    def finish_enrage_return(self) -> None:
        """Return to ACTIVE after a successful enrage cycle."""
        self._enrage_return_timer = 0
        self._enrage_return_origin = None
        self._enrage_return_target = None

    # ------------------------------------------------------------------
    # Per-frame decrementers
    # ------------------------------------------------------------------

    def tick_enrage_attack_timer(self) -> None:
        """Decrement the enrage snapshot attack timer (clamped at 0)."""
        if self._enrage_attack_timer > 0:
            self._enrage_attack_timer -= 1

    def reset_enrage_attack_timer(self) -> None:
        self._enrage_attack_timer = ENRAGE_ATTACK_INTERVAL
        self._enrage_attack_index += 1

    def tick_enrage_transition_timer(self) -> None:
        if self._enrage_transition_timer > 0:
            self._enrage_transition_timer -= 1

    def tick_enrage_timer(self) -> None:
        if self._enrage_timer > 0:
            self._enrage_timer -= 1

    def tick_enrage_release_hold_timer(self) -> None:
        if self._enrage_release_hold_timer > 0:
            self._enrage_release_hold_timer -= 1

    def tick_enrage_return_timer(self) -> None:
        if self._enrage_return_timer > 0:
            self._enrage_return_timer -= 1

    # ------------------------------------------------------------------
    # Predicates used by the rest of the codebase
    # ------------------------------------------------------------------

    def is_enrage_active(self) -> bool:
        return self._enrage_timer > 0

    def is_enrage_transitioning(self) -> bool:
        return self._enrage_transition_timer > 0

    def is_enrage_release_holding(self) -> bool:
        return self._enrage_release_hold_timer > 0

    def is_enrage_returning(self) -> bool:
        return self._enrage_return_timer > 0

    def should_lock_player_movement(self) -> bool:
        return self._enrage_timer > 0 and not self._enrage_bullets_released

    def enrage_slow_factor(self) -> float:
        return ENRAGE_SLOW_FACTOR if self._enrage_timer > 0 else 1.0

    def enrage_progress(self) -> float:
        """0.0 at enrage start, 1.0 at enrage end."""
        return max(0.0, min(1.0, 1.0 - self._enrage_timer / ENRAGE_DURATION))

    def enrage_visual_intensity(self) -> float:
        """Visual overlay intensity for the enrage sequence (0..~0.88)."""
        if self._enrage_timer > 0:
            progress = self.enrage_progress()
            eased = progress * progress * (3 - 2 * progress)
            transition_ramp = 1.0
            if self._enrage_transition_timer > 0:
                elapsed = ENRAGE_TRANSITION_DURATION - self._enrage_transition_timer
                transition = max(
                    0.0,
                    min(1.0, elapsed / max(1, ENRAGE_TRANSITION_DURATION)),
                )
                transition_ramp = transition * transition * (3 - 2 * transition)
            return max(
                0.0,
                min(0.88, (0.18 + 0.70 * eased) * transition_ramp),
            )
        if self._enrage_release_hold_timer > 0:
            hold = self._enrage_release_hold_timer / max(1, ENRAGE_RELEASE_HOLD_DURATION)
            return max(0.0, min(0.74, 0.52 + 0.22 * hold))
        if self._enrage_return_timer > 0:
            fade = self._enrage_return_timer / max(1, ENRAGE_RETURN_DURATION)
            eased = fade * fade * (3 - 2 * fade)
            return max(0.0, min(0.52, 0.52 * eased))
        return 0.0

    # ------------------------------------------------------------------
    # Internal helpers (used by Boss.take_damage)
    # ------------------------------------------------------------------

    def compute_take_damage(self, damage: int) -> tuple[int, int]:
        """Apply damage under the enrage health-lock policy.

        Returns:
            (new_health, score_delta) — caller applies the new health and
            the score (positive on death, 0 otherwise).
        """
        if damage is None or damage < 0:
            return self._boss.health, 0
        if not self._enraged and self._boss.max_health > 0:
            projected = self._boss.health - damage
            if projected <= 0:
                # Lethal hit — boss dies regardless of enrage lock
                return 0, self._boss.data.score
            if projected <= self._enrage_health_lock_value:
                self._boss.health = self._enrage_health_lock_value
                return self._boss.health, 0
        if self._enrage_health_lock_active:
            self._boss.health = max(self._boss.health, self._enrage_health_lock_value)
            return self._boss.health, 0
        new_health = self._boss.health - damage
        if new_health <= 0:
            return 0, self._boss.data.score
        return new_health, 0


__all__ = ["EnrageSubMachine"]
