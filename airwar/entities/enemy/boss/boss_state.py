"""Boss state HSM — top-level lifecycle + facade over the enrage sub-machine.

* :class:`BossState` and the 8 top-level states (defined here)
* :class:`BossStateMachine` (defined here) — thin facade. Owns the
  top-level :class:`BossState` enum, delegates enrage timer/location/
  attack state and damage policy to :class:`EnrageSubMachine` in
  :mod:`.boss_sub_state`.
* :class:`EnrageSubMachine` (:mod:`.boss_sub_state`) — owns the 4
  enrage timer counters, the 5 location anchors, the attack state, the
  enrage flags, and the health-lock damage policy.

The enrage tuning constants remain available from ``Boss`` for the gameplay
code that uses them.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from airwar.config.constants_access import get_game_constants

if TYPE_CHECKING:
    from .boss import Boss


# ---------------------------------------------------------------------------
# Constants (re-exported so ``Boss.ENRAGE_DURATION`` keeps working)
# ---------------------------------------------------------------------------

_BOSS_ENRAGE = get_game_constants().BOSS_ENRAGE

ENRAGE_TRIGGER_RATIO: float = _BOSS_ENRAGE.TRIGGER_RATIO
ENRAGE_DURATION: int = _BOSS_ENRAGE.DURATION
ENRAGE_TRANSITION_DURATION: int = _BOSS_ENRAGE.TRANSITION_DURATION
ENRAGE_SLOW_FACTOR: float = _BOSS_ENRAGE.SLOW_FACTOR
ENRAGE_BULLET_SPEED: float = _BOSS_ENRAGE.BULLET_SPEED
ENRAGE_LASER_SPEED: float = _BOSS_ENRAGE.LASER_SPEED
ENRAGE_RELEASE_BULLET_SPEED: float = _BOSS_ENRAGE.RELEASE_BULLET_SPEED
ENRAGE_RELEASE_LASER_SPEED: float = _BOSS_ENRAGE.RELEASE_LASER_SPEED
ENRAGE_ATTACK_INTERVAL: int = _BOSS_ENRAGE.ATTACK_INTERVAL
ENRAGE_ATTACK_WINDUP: int = _BOSS_ENRAGE.ATTACK_WINDUP
ENRAGE_RELEASE_INTERVAL: int = _BOSS_ENRAGE.RELEASE_INTERVAL
ENRAGE_SNAPSHOT_LASER_COUNT: int = _BOSS_ENRAGE.SNAPSHOT_LASER_COUNT
ENRAGE_SNAPSHOT_RING_COUNT: int = _BOSS_ENRAGE.SNAPSHOT_RING_COUNT
ENRAGE_PATH_RADIUS_SCALE: float = _BOSS_ENRAGE.PATH_RADIUS_SCALE
ENRAGE_SQUARE_PATH_RATIO: float = _BOSS_ENRAGE.SQUARE_PATH_RATIO
ENRAGE_TRAIL_LENGTH: int = _BOSS_ENRAGE.TRAIL_LENGTH
ENRAGE_TRAIL_RENDER_MAX: int = _BOSS_ENRAGE.TRAIL_RENDER_MAX
ENRAGE_TRAIL_FINAL_SCALE: float = _BOSS_ENRAGE.TRAIL_FINAL_SCALE
ENRAGE_TRAIL_SCALE: float = _BOSS_ENRAGE.TRAIL_SCALE
ENRAGE_TRAIL_BLUR_PASSES: int = _BOSS_ENRAGE.TRAIL_BLUR_PASSES
ENRAGE_EXIT_BACK_OFFSET: int = _BOSS_ENRAGE.EXIT_BACK_OFFSET
ENRAGE_MUZZLE_FLASH_DURATION: int = _BOSS_ENRAGE.MUZZLE_FLASH_DURATION
ENRAGE_MUZZLE_FLASH_PULSES: int = _BOSS_ENRAGE.MUZZLE_FLASH_PULSES
ENRAGE_MUZZLE_FORWARD_SCALE: float = _BOSS_ENRAGE.MUZZLE_FORWARD_SCALE
ENRAGE_MUZZLE_SIDE_SCALE: float = _BOSS_ENRAGE.MUZZLE_SIDE_SCALE
ENRAGE_RELEASE_HOLD_DURATION: int = _BOSS_ENRAGE.RELEASE_HOLD_DURATION
ENRAGE_RETURN_DURATION: int = _BOSS_ENRAGE.RETURN_DURATION
ENRAGE_CORE_COLOR: tuple[int, int, int] = _BOSS_ENRAGE.CORE_COLOR
ENRAGE_DANGER_COLOR: tuple[int, int, int] = _BOSS_ENRAGE.DANGER_COLOR
ENRAGE_TRAIL_TINT: tuple[int, int, int] = _BOSS_ENRAGE.TRAIL_TINT


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
# Legal transition table (Nystrom-style finite state machine).
#
# Mirrors the Player HSM pattern (see ``player_state._ALIVE_TRANSITIONS``).
# Each transfer method on :class:`BossStateMachine` consults this table at
# entry; an absent edge raises :class:`IllegalBossTransition`.
#
# Design notes:
# - ``DEAD`` is terminal: no outgoing edges.
# - ``ESCAPING -> DEAD`` is legal (an escaping boss can still be killed
#   by stray bullets before flying off-screen).
# - ``ENRAGE_RETURN -> ACTIVE`` is the only loop: a successful enrage
#   cycle returns the boss to ACTIVE.
# - ``trigger_enrage`` is the enrage entry point and is reachable from
#   any non-DEAD state.
# ---------------------------------------------------------------------------

_BOSS_TRANSITIONS: dict[BossState, frozenset[BossState]] = {
    BossState.ENTERING: frozenset(
        {
            BossState.ACTIVE,
            BossState.DEAD,
        }
    ),
    BossState.ACTIVE: frozenset(
        {
            BossState.ENRAGE_TRANSITION,
            BossState.ESCAPING,
            BossState.DEAD,
        }
    ),
    BossState.ENRAGE_TRANSITION: frozenset(
        {
            BossState.ENRAGE_ACTIVE,
            BossState.ESCAPING,
            BossState.DEAD,
        }
    ),
    BossState.ENRAGE_ACTIVE: frozenset(
        {
            BossState.ENRAGE_RELEASE_HOLD,
            BossState.ESCAPING,
            BossState.DEAD,
        }
    ),
    BossState.ENRAGE_RELEASE_HOLD: frozenset(
        {
            BossState.ENRAGE_RETURN,
            BossState.ESCAPING,
            BossState.DEAD,
        }
    ),
    BossState.ENRAGE_RETURN: frozenset(
        {
            BossState.ACTIVE,
            BossState.ESCAPING,
            BossState.DEAD,
        }
    ),
    # ``trigger_enrage`` is legal from any non-DEAD state (idempotent
    # re-trigger) so all non-DEAD states have an edge to ENRAGE_TRANSITION.
    BossState.ESCAPING: frozenset(
        {
            BossState.ENRAGE_TRANSITION,
            BossState.DEAD,
        }
    ),
    BossState.DEAD: frozenset(),
}


# Wire the ENRAGE_TRANSITION edge for every non-DEAD state (idempotent
# ``trigger_enrage`` matches the existing semantics).
for _src in BossState:
    if _src is BossState.DEAD:
        continue
    _existing = _BOSS_TRANSITIONS[_src]
    _BOSS_TRANSITIONS[_src] = _existing | {BossState.ENRAGE_TRANSITION}


class IllegalBossTransition(ValueError):
    """Raised when a boss state transition is not in the legal-edge table.

    Mirrors :class:`airwar.entities.player_state.IllegalPlayerTransition`.
    Defensive guard rails: future refactors that bypass the documented
    state diagram (e.g. jumping ACTIVE -> DEAD via an unvetted path) get
    caught immediately instead of silently corrupting the enrage sequence.
    """


# ---------------------------------------------------------------------------
# State machine (facade over EnrageSubMachine)
# ---------------------------------------------------------------------------


class BossStateMachine:
    """Drives boss lifecycle transitions and exposes enrage predicates.

    After the Phase 5-β split, this class is a thin facade over
    :class:`EnrageSubMachine`. The top-level :class:`BossState` enum
    is owned here; the enrage timer/location/attack state lives in the
    sub-machine. Public methods and properties delegate to the sub-machine
    so the Boss coordinator has one focused source for enrage state.
    """

    def __init__(self, boss: Boss) -> None:
        self._boss = boss
        self._state: BossState = BossState.ENTERING
        # Lazy import: boss_sub_state imports constants from this module
        # at top-level, so deferring the import here breaks the cycle
        # while keeping the class body free of forward references.
        from .boss_sub_state import EnrageSubMachine

        self._sub = EnrageSubMachine(boss)

    # ------------------------------------------------------------------
    # Top-level state accessor
    # ------------------------------------------------------------------

    @property
    def state(self) -> BossState:
        return self._state

    # ------------------------------------------------------------------
    # Public accessors (delegate to sub-machine)
    # ------------------------------------------------------------------

    @property
    def enraged(self) -> bool:
        return self._sub._enraged

    @property
    def enrage_timer(self) -> int:
        return self._sub._enrage_timer

    @property
    def enrage_transition_timer(self) -> int:
        return self._sub._enrage_transition_timer

    @property
    def enrage_release_hold_timer(self) -> int:
        return self._sub._enrage_release_hold_timer

    @property
    def enrage_return_timer(self) -> int:
        return self._sub._enrage_return_timer

    @property
    def enrage_snapshot_target(self) -> tuple[float, float] | None:
        return self._sub._enrage_snapshot_target

    @property
    def enrage_transition_origin(self) -> tuple[float, float] | None:
        return self._sub._enrage_transition_origin

    @property
    def enrage_release_anchor(self) -> tuple[float, float] | None:
        return self._sub._enrage_release_anchor

    @property
    def enrage_return_origin(self) -> tuple[float, float] | None:
        return self._sub._enrage_return_origin

    @property
    def enrage_return_target(self) -> tuple[float, float] | None:
        return self._sub._enrage_return_target

    @property
    def enrage_attack_timer(self) -> int:
        return self._sub._enrage_attack_timer

    @property
    def enrage_attack_index(self) -> int:
        return self._sub._enrage_attack_index

    # ------------------------------------------------------------------
    # Top-level transitions (own the state enum)
    # ------------------------------------------------------------------

    def _check_transition(self, to_state: BossState) -> None:
        """Raise :class:`IllegalBossTransition` if the edge is not legal.

        Mirrors the legal-edge guard pattern from
        :class:`airwar.entities.player_state.PlayerStateMachine`. The
        self-loop case (``to_state == self._state``) is treated as a
        legal idempotent no-op: callers like ``finish_entry`` and
        ``mark_dead`` historically rely on the silent no-op to remain
        safe to call repeatedly.
        """
        if to_state == self._state:
            return
        legal = _BOSS_TRANSITIONS.get(self._state, frozenset())
        if to_state not in legal:
            raise IllegalBossTransition(
                f"Illegal boss state transition: {self._state.name} -> {to_state.name}"
            )

    def finish_entry(self) -> None:
        """Transition out of ENTERING once the boss reaches its target Y."""
        self._check_transition(BossState.ACTIVE)
        self._state = BossState.ACTIVE

    def mark_escaped(self) -> None:
        """Boss survived long enough; mark as escaped and inactive."""
        self._check_transition(BossState.ESCAPING)
        self._state = BossState.ESCAPING

    def mark_dead(self) -> None:
        """Boss was killed (called from :meth:`Boss.take_damage`)."""
        self._check_transition(BossState.DEAD)
        self._state = BossState.DEAD

    # ------------------------------------------------------------------
    # Enrage transitions (delegate + sync top-level state)
    # ------------------------------------------------------------------

    def trigger_enrage(self, snapshot_target: tuple[float, float]) -> None:
        """Begin the enrage sub-machine (idempotent)."""
        self._check_transition(BossState.ENRAGE_TRANSITION)
        self._sub.trigger_enrage(snapshot_target)
        if self._sub._enraged:
            self._state = BossState.ENRAGE_TRANSITION

    def finish_enrage_transition(self) -> None:
        """Move from ENRAGE_TRANSITION to ENRAGE_ACTIVE."""
        self._check_transition(BossState.ENRAGE_ACTIVE)
        self._sub.finish_enrage_transition()
        self._state = BossState.ENRAGE_ACTIVE

    def begin_enrage_release_hold(self, anchor: tuple[float, float]) -> None:
        """Move from ENRAGE_ACTIVE to ENRAGE_RELEASE_HOLD."""
        self._check_transition(BossState.ENRAGE_RELEASE_HOLD)
        self._sub.begin_enrage_release_hold(anchor)
        self._state = BossState.ENRAGE_RELEASE_HOLD

    def begin_enrage_return(
        self,
        origin: tuple[float, float],
        target: tuple[float, float],
    ) -> None:
        """Move from ENRAGE_RELEASE_HOLD to ENRAGE_RETURN."""
        self._check_transition(BossState.ENRAGE_RETURN)
        self._sub.begin_enrage_return(origin, target)
        self._state = BossState.ENRAGE_RETURN

    def finish_enrage_return(self) -> None:
        """Return to ACTIVE after a successful enrage cycle."""
        self._check_transition(BossState.ACTIVE)
        self._sub.finish_enrage_return()
        self._state = BossState.ACTIVE

    # ------------------------------------------------------------------
    # Per-frame decrementers (delegate to sub-machine)
    # ------------------------------------------------------------------

    def tick_enrage_attack_timer(self) -> None:
        """Decrement the enrage snapshot attack timer (clamped at 0)."""
        self._sub.tick_enrage_attack_timer()

    def reset_enrage_attack_timer(self) -> None:
        self._sub.reset_enrage_attack_timer()

    def tick_enrage_transition_timer(self) -> None:
        self._sub.tick_enrage_transition_timer()

    def tick_enrage_timer(self) -> None:
        self._sub.tick_enrage_timer()

    def tick_enrage_release_hold_timer(self) -> None:
        self._sub.tick_enrage_release_hold_timer()

    def tick_enrage_return_timer(self) -> None:
        self._sub.tick_enrage_return_timer()

    # ------------------------------------------------------------------
    # Predicates used by the rest of the codebase
    # ------------------------------------------------------------------

    def is_enrage_active(self) -> bool:
        return self._sub.is_enrage_active()

    def is_enrage_transitioning(self) -> bool:
        return self._sub.is_enrage_transitioning()

    def is_enrage_release_holding(self) -> bool:
        return self._sub.is_enrage_release_holding()

    def is_enrage_returning(self) -> bool:
        return self._sub.is_enrage_returning()

    def should_lock_player_movement(self) -> bool:
        return self._sub.should_lock_player_movement()

    def enrage_slow_factor(self) -> float:
        return self._sub.enrage_slow_factor()

    def enrage_progress(self) -> float:
        """0.0 at enrage start, 1.0 at enrage end."""
        return self._sub.enrage_progress()

    def enrage_visual_intensity(self) -> float:
        """Visual overlay intensity for the enrage sequence (0..~0.88)."""
        return self._sub.enrage_visual_intensity()

    # ------------------------------------------------------------------
    # Internal helpers (used by Boss.take_damage)
    # ------------------------------------------------------------------

    def compute_take_damage(self, damage: int) -> tuple[int, int]:
        """Apply damage under the enrage health-lock policy.

        Returns:
            (new_health, score_delta) — caller applies the new health and
            the score (positive on death, 0 otherwise).
        """
        return self._sub.compute_take_damage(damage)


# ---------------------------------------------------------------------------
# Fallback module-level access for enrage tuning constants.
# ---------------------------------------------------------------------------


def __getattr__(name: str):
    """F04 M9: fallback module-level access for ENRAGE_* constants.

    Defined constants above are already aliases from
    GAME_CONSTANTS.BOSS_ENRAGE. This fallback keeps future ENRAGE_*
    additions source-compatible if callers import them before this
    module grows an explicit alias.
    """
    if name.startswith("ENRAGE_") and name[7:].isupper():
        return getattr(get_game_constants().BOSS_ENRAGE, name[7:])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "IllegalBossTransition",
]
