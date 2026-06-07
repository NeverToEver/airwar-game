"""Boss state HSM — top-level lifecycle and enrage sub-machine.

Centralises the previously scattered ``_phase`` int + ``_is_enraged`` bool
into a single state machine with explicit transition rules. The
:class:`BossStateMachine` is owned by :class:`airwar.entities.enemy.Boss`
and consulted on every frame; it is also the single source of truth for
enrage-related public predicates (``is_enraged``, ``is_enrage_active``,
``should_lock_player_movement``, ``enrage_slow_factor``,
``enrage_visual_intensity``).

Backward compatibility:
    The enrage tuning constants used to live as class attributes on
    ``Boss`` (e.g. ``Boss.ENRAGE_DURATION``). They are re-exported from
    this module and aliased on the ``Boss`` class so existing callers
    that import them as class constants keep working.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .boss import Boss


# ---------------------------------------------------------------------------
# Constants (re-exported so ``Boss.ENRAGE_DURATION`` keeps working)
# ---------------------------------------------------------------------------

ENRAGE_TRIGGER_RATIO: float = 0.30
ENRAGE_DURATION: int = 360
ENRAGE_TRANSITION_DURATION: int = 54
ENRAGE_SLOW_FACTOR: float = 0.24
ENRAGE_BULLET_SPEED: float = 3.2
ENRAGE_LASER_SPEED: float = 3.7
ENRAGE_RELEASE_BULLET_SPEED: float = 1.55
ENRAGE_RELEASE_LASER_SPEED: float = 1.35
ENRAGE_ATTACK_INTERVAL: int = 42
ENRAGE_ATTACK_WINDUP: int = 24
ENRAGE_RELEASE_INTERVAL: int = 6
ENRAGE_SNAPSHOT_LASER_COUNT: int = 4
ENRAGE_SNAPSHOT_RING_COUNT: int = 8
ENRAGE_PATH_RADIUS_SCALE: float = 1.50
ENRAGE_SQUARE_PATH_RATIO: float = 0.48
ENRAGE_TRAIL_LENGTH: int = 42
ENRAGE_TRAIL_RENDER_MAX: int = 16
ENRAGE_TRAIL_FINAL_SCALE: float = 3.0
ENRAGE_TRAIL_SCALE: float = 0.5
ENRAGE_TRAIL_BLUR_PASSES: int = 2
ENRAGE_EXIT_BACK_OFFSET: int = 118
ENRAGE_MUZZLE_FLASH_DURATION: int = 12
ENRAGE_MUZZLE_FLASH_PULSES: int = 2
ENRAGE_MUZZLE_FORWARD_SCALE: float = 0.58
ENRAGE_MUZZLE_SIDE_SCALE: float = 0.34
ENRAGE_RELEASE_HOLD_DURATION: int = 42
ENRAGE_RETURN_DURATION: int = 48
ENRAGE_CORE_COLOR: tuple[int, int, int] = (126, 220, 255)
ENRAGE_DANGER_COLOR: tuple[int, int, int] = (230, 72, 68)
ENRAGE_TRAIL_TINT: tuple[int, int, int] = (96, 154, 220)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BossState(Enum):
    """Top-level boss lifecycle states.

    The state machine is intentionally linear: a boss can only progress
    forward, with the only loop being the ENRAGE_RELEASE_HOLD sub-state
    before returning to ACTIVE (after a successful kill) or transitioning
    to ESCAPING (when the survival timer expires).
    """

    ENTERING = "entering"
    ACTIVE = "active"
    ENRAGE_TRANSITION = "enrage_transition"
    ENRAGE_ACTIVE = "enrage_active"
    ENRAGE_RELEASE_HOLD = "enrage_release_hold"
    ENRAGE_RETURN = "enrage_return"
    ESCAPING = "escaping"
    DEAD = "dead"


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class BossStateMachine:
    """Drives boss lifecycle transitions and exposes enrage predicates.

    The machine owns every timer/flag previously held directly on the
    ``Boss`` instance. Callers read state through the boolean helpers
    (``is_enrage_active``, ``should_lock_player_movement``,
    ``enrage_visual_intensity``) so the ``Boss`` class itself no longer
    needs to know about the underlying counters.
    """

    def __init__(self, boss: Boss) -> None:
        self._boss = boss
        self._state: BossState = BossState.ENTERING
        # enrage sub-machine
        self._enraged: bool = False
        self._enrage_timer: int = 0
        self._enrage_transition_timer: int = 0
        self._enrage_release_hold_timer: int = 0
        self._enrage_return_timer: int = 0
        self._enrage_bullets_released: bool = False
        self._enrage_health_lock_active: bool = False
        self._enrage_health_lock_value: int = 0
        self._enrage_snapshot_target: tuple[float, float] | None = None
        self._enrage_transition_origin: tuple[float, float] | None = None
        self._enrage_release_anchor: tuple[float, float] | None = None
        self._enrage_return_origin: tuple[float, float] | None = None
        self._enrage_return_target: tuple[float, float] | None = None
        self._enrage_attack_timer: int = 0
        self._enrage_attack_index: int = 0

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def state(self) -> BossState:
        return self._state

    @property
    def enraged(self) -> bool:
        return self._enraged

    @property
    def enrage_timer(self) -> int:
        return self._enrage_timer

    @property
    def enrage_transition_timer(self) -> int:
        return self._enrage_transition_timer

    @property
    def enrage_release_hold_timer(self) -> int:
        return self._enrage_release_hold_timer

    @property
    def enrage_return_timer(self) -> int:
        return self._enrage_return_timer

    @property
    def enrage_snapshot_target(self) -> tuple[float, float] | None:
        return self._enrage_snapshot_target

    @property
    def enrage_transition_origin(self) -> tuple[float, float] | None:
        return self._enrage_transition_origin

    @property
    def enrage_release_anchor(self) -> tuple[float, float] | None:
        return self._enrage_release_anchor

    @property
    def enrage_return_origin(self) -> tuple[float, float] | None:
        return self._enrage_return_origin

    @property
    def enrage_return_target(self) -> tuple[float, float] | None:
        return self._enrage_return_target

    @property
    def enrage_attack_timer(self) -> int:
        return self._enrage_attack_timer

    @property
    def enrage_attack_index(self) -> int:
        return self._enrage_attack_index

    @property
    def enrage_health_lock_active(self) -> bool:
        return self._enrage_health_lock_active

    @property
    def enrage_health_lock_value(self) -> int:
        return self._enrage_health_lock_value

    @property
    def enrage_bullets_released(self) -> bool:
        return self._enrage_bullets_released

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    def finish_entry(self) -> None:
        """Transition out of ENTERING once the boss reaches its target Y."""
        self._state = BossState.ACTIVE

    def trigger_enrage(self, snapshot_target: tuple[float, float]) -> None:
        """Begin the enrage sub-machine (idempotent)."""
        if self._enraged:
            return
        self._enraged = True
        self._state = BossState.ENRAGE_TRANSITION
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
        self._state = BossState.ENRAGE_ACTIVE

    def begin_enrage_release_hold(self, anchor: tuple[float, float]) -> None:
        """Move from ENRAGE_ACTIVE to ENRAGE_RELEASE_HOLD."""
        self._state = BossState.ENRAGE_RELEASE_HOLD
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
        self._state = BossState.ENRAGE_RETURN
        self._enrage_return_timer = ENRAGE_RETURN_DURATION
        self._enrage_return_origin = origin
        self._enrage_return_target = target
        self._enrage_release_anchor = None

    def finish_enrage_return(self) -> None:
        """Return to ACTIVE after a successful enrage cycle."""
        self._enrage_return_timer = 0
        self._enrage_return_origin = None
        self._enrage_return_target = None
        self._state = BossState.ACTIVE

    def mark_escaped(self) -> None:
        """Boss survived long enough; mark as escaped and inactive."""
        self._state = BossState.ESCAPING

    def mark_dead(self) -> None:
        """Boss was killed (called from :meth:`Boss.take_damage`)."""
        self._state = BossState.DEAD

    def tick_enrage_attack_timer(self) -> None:
        """Decrement the enrage snapshot attack timer (clamped at 0)."""
        if self._enrage_attack_timer > 0:
            self._enrage_attack_timer -= 1

    def reset_enrage_attack_timer(self) -> None:
        self._enrage_attack_timer = ENRAGE_ATTACK_INTERVAL
        self._enrage_attack_index += 1

    # ------------------------------------------------------------------
    # Per-frame decrementers (kept here so the Boss class doesn't poke
    # at the state counters directly).
    # ------------------------------------------------------------------

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


# Re-export alias so test code can ``from .boss_state import BossStateMachine``.
__all__ = [
    "ENRAGE_ATTACK_INTERVAL",
    "ENRAGE_ATTACK_WINDUP",
    "ENRAGE_BULLET_SPEED",
    "ENRAGE_CORE_COLOR",
    "ENRAGE_DANGER_COLOR",
    "ENRAGE_DURATION",
    "ENRAGE_EXIT_BACK_OFFSET",
    "ENRAGE_LASER_SPEED",
    "ENRAGE_MUZZLE_FLASH_DURATION",
    "ENRAGE_MUZZLE_FLASH_PULSES",
    "ENRAGE_MUZZLE_FORWARD_SCALE",
    "ENRAGE_MUZZLE_SIDE_SCALE",
    "ENRAGE_PATH_RADIUS_SCALE",
    "ENRAGE_RELEASE_BULLET_SPEED",
    "ENRAGE_RELEASE_HOLD_DURATION",
    "ENRAGE_RELEASE_INTERVAL",
    "ENRAGE_RELEASE_LASER_SPEED",
    "ENRAGE_RETURN_DURATION",
    "ENRAGE_SLOW_FACTOR",
    "ENRAGE_SNAPSHOT_LASER_COUNT",
    "ENRAGE_SNAPSHOT_RING_COUNT",
    "ENRAGE_SQUARE_PATH_RATIO",
    "ENRAGE_TRAIL_BLUR_PASSES",
    "ENRAGE_TRAIL_FINAL_SCALE",
    "ENRAGE_TRAIL_LENGTH",
    "ENRAGE_TRAIL_RENDER_MAX",
    "ENRAGE_TRAIL_SCALE",
    "ENRAGE_TRAIL_TINT",
    "ENRAGE_TRANSITION_DURATION",
    "ENRAGE_TRIGGER_RATIO",
    "BossState",
    "BossStateMachine",
]
