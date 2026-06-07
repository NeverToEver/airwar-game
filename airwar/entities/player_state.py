"""Player hierarchical state machine (HSM).

Defines the explicit state diagram for the :class:`airwar.entities.player.Player`
and the :class:`PlayerStateMachine` that owns it. The state machine was
introduced in Phase 3 of the refactor to consolidate the previously
scattered boolean flags (``is_shielded``, ``is_boost_active``,
``is_controls_locked``, ``is_phase_dashing``) into a single source of
truth.

State diagram::

    +-------------------+
    |     PlayerState   |  Top-level lifecycle
    +-------------------+
            |
            v
    +-------------------+   +-----------+   +---------+
    |      ALIVE        |-->|   DYING   |-->|  DEAD   |
    +-------------------+   +-----------+   +---------+
            |
            v  PlayerAliveState (orthogonal to PlayerState modifiers)
    +-------------------+   +-----------+   +----------+
    |      NORMAL       |   | BOOSTING  |   | DASHING  |  ...
    +-------------------+   +-----------+   +----------+
       ^     ^     ^
       |     |     +--- SHIELDED
       |     +--------- DOCKED
       +--------------- RESPAWN_INVINCIBLE

Orthogonal modifiers (NOT in the state machine):
    * ``is_phase_dash_enabled`` (talent unlock)
    * ``_has_spread`` / ``_has_laser`` / ``_has_explosive`` (weapon mods)
    * ``mothership_cooldown_mult`` (talent scaling)

These are independent flags that apply across every alive sub-state.
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlayerState(IntEnum):
    """Top-level player lifecycle states."""

    ALIVE = 0
    DYING = 1
    DEAD = 2


class PlayerAliveState(IntEnum):
    """Substates of :attr:`PlayerState.ALIVE`.

    Mutually exclusive — at most one is active at a time. Transitions
    follow the legal-edge table in :class:`PlayerStateMachine`.
    """

    NORMAL = 0
    BOOSTING = 1
    DASHING = 2
    SHIELDED = 3
    DOCKED = 4
    RESPAWN_INVINCIBLE = 5


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


# Legal transitions between alive substates. Any move not listed here
# is rejected by :meth:`PlayerStateMachine.transition_substate`.
_ALIVE_TRANSITIONS: dict[PlayerAliveState, set[PlayerAliveState]] = {
    PlayerAliveState.NORMAL: {
        PlayerAliveState.BOOSTING,
        PlayerAliveState.DASHING,
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
    PlayerAliveState.DASHING: {
        PlayerAliveState.NORMAL,
        PlayerAliveState.DOCKED,
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
}


class IllegalPlayerTransition(ValueError):
    """Raised when a substate transition is not in the legal-edge table."""


class PlayerStateMachine:
    """Owns player lifecycle + alive-substate transitions.

    The Player class delegates to this machine for ``is_alive``,
    ``is_dying``, ``is_dead``, and per-substate predicates. Backward
    compatibility: existing boolean attributes on the Player
    (``is_shielded``, ``is_controls_locked``, etc.) are still readable;
    the HSM exposes parallel predicates.
    """

    def __init__(self, player: Player) -> None:
        self._player = player
        self._state: PlayerState = PlayerState.ALIVE
        self._alive_substate: PlayerAliveState = PlayerAliveState.NORMAL
        # Substate timing
        self._shield_duration: int = 0
        self._respawn_invincibility_duration: int = 0
        # Marked for external use (docking / respawn).
        self._dock_active: bool = False
        self._respawn_invincible: bool = False

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def state(self) -> PlayerState:
        return self._state

    @property
    def alive_substate(self) -> PlayerAliveState:
        return self._alive_substate

    @property
    def shield_duration(self) -> int:
        return self._shield_duration

    @property
    def dock_active(self) -> bool:
        return self._dock_active

    @property
    def respawn_invincible(self) -> bool:
        return self._respawn_invincible

    # ------------------------------------------------------------------
    # Top-level lifecycle
    # ------------------------------------------------------------------

    def mark_dying(self) -> None:
        if self._state == PlayerState.DEAD:
            raise IllegalPlayerTransition(
                "Cannot mark DYING after DEAD: state is already terminal"
            )
        self._state = PlayerState.DYING

    def mark_dead(self) -> None:
        self._state = PlayerState.DEAD

    def respawn(self) -> None:
        """Return to ALIVE / NORMAL after death (called by GameController)."""
        self._state = PlayerState.ALIVE
        self.transition_substate(PlayerAliveState.RESPAWN_INVINCIBLE)

    # ------------------------------------------------------------------
    # Substate transitions
    # ------------------------------------------------------------------

    def transition_substate(self, new_sub: PlayerAliveState) -> None:
        """Transition to ``new_sub`` if the edge is legal.

        Raises:
            IllegalPlayerTransition: if there is no legal edge from the
                current substate to ``new_sub``.
        """
        if new_sub == self._alive_substate:
            return
        legal = _ALIVE_TRANSITIONS.get(self._alive_substate, set())
        if new_sub not in legal:
            raise IllegalPlayerTransition(
                f"Illegal player substate transition: {self._alive_substate.name} -> {new_sub.name}"
            )
        self._alive_substate = new_sub

    def force_substate(self, new_sub: PlayerAliveState) -> None:
        """Bypass the legal-edge check (used for save/restore)."""
        self._alive_substate = new_sub

    # ------------------------------------------------------------------
    # Substate-side helpers
    # ------------------------------------------------------------------

    def activate_shield(self, duration: int) -> None:
        self.transition_substate(PlayerAliveState.SHIELDED)
        self._shield_duration = max(1, duration)

    def deactivate_shield(self) -> None:
        if self._alive_substate == PlayerAliveState.SHIELDED:
            self.transition_substate(PlayerAliveState.NORMAL)
        self._shield_duration = 0

    def tick_shield(self) -> None:
        if self._shield_duration > 0:
            self._shield_duration -= 1
            if self._shield_duration == 0 and self._alive_substate == PlayerAliveState.SHIELDED:
                self.transition_substate(PlayerAliveState.NORMAL)

    def enter_dock(self) -> None:
        self._dock_active = True
        self.transition_substate(PlayerAliveState.DOCKED)

    def exit_dock(self) -> None:
        self._dock_active = False
        if self._alive_substate == PlayerAliveState.DOCKED:
            self.transition_substate(PlayerAliveState.NORMAL)

    def enter_boost(self) -> None:
        # Boosting is only legal when not already in another locked state.
        # F03 S6: silent returns removed; transition_substate raises on
        # illegal moves. The legal-edge table is the single source of truth.
        if self._alive_substate == PlayerAliveState.DOCKED:
            raise IllegalPlayerTransition(
                "Cannot enter BOOSTING from DOCKED: docked and boosting are mutually exclusive"
            )
        if self._alive_substate == PlayerAliveState.SHIELDED:
            raise IllegalPlayerTransition(
                "Cannot enter BOOSTING from SHIELDED: shield is incompatible with boost"
            )
        if self._alive_substate == PlayerAliveState.DASHING:
            raise IllegalPlayerTransition(
                "Cannot enter BOOSTING from DASHING: dash preempts boost"
            )
        self.transition_substate(PlayerAliveState.BOOSTING)

    def exit_boost(self) -> None:
        if self._alive_substate == PlayerAliveState.BOOSTING:
            self.transition_substate(PlayerAliveState.NORMAL)

    def enter_dash(self) -> None:
        # F03 S7: silent return removed. Dash preempts NORMAL only;
        # any other substate raises IllegalPlayerTransition.
        if self._alive_substate != PlayerAliveState.NORMAL:
            raise IllegalPlayerTransition(
                f"Cannot enter DASHING from {self._alive_substate.name}: "
                f"dash only preempts NORMAL"
            )
        self.transition_substate(PlayerAliveState.DASHING)

    def exit_dash(self) -> None:
        if self._alive_substate == PlayerAliveState.DASHING:
            self.transition_substate(PlayerAliveState.NORMAL)

    def enter_respawn_invincibility(self, duration: int) -> None:
        self._respawn_invincible = True
        self._respawn_invincibility_duration = max(1, duration)
        self.transition_substate(PlayerAliveState.RESPAWN_INVINCIBLE)

    def tick_respawn_invincibility(self) -> None:
        if self._respawn_invincibility_duration > 0:
            self._respawn_invincibility_duration -= 1
            if (
                self._respawn_invincibility_duration == 0
                and self._alive_substate == PlayerAliveState.RESPAWN_INVINCIBLE
            ):
                self._respawn_invincible = False
                self.transition_substate(PlayerAliveState.NORMAL)

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        return self._state == PlayerState.ALIVE

    def is_dying(self) -> bool:
        return self._state == PlayerState.DYING

    def is_dead(self) -> bool:
        return self._state == PlayerState.DEAD

    def is_shielded(self) -> bool:
        return self._alive_substate == PlayerAliveState.SHIELDED

    def is_docked(self) -> bool:
        return self._alive_substate == PlayerAliveState.DOCKED

    def is_boosting(self) -> bool:
        return self._alive_substate == PlayerAliveState.BOOSTING

    def is_dashing(self) -> bool:
        return self._alive_substate == PlayerAliveState.DASHING

    def is_respawn_invincible(self) -> bool:
        return self._alive_substate == PlayerAliveState.RESPAWN_INVINCIBLE

    def should_lock_controls(self) -> bool:
        """Top-level predicate: should input be ignored this frame?"""
        return self._alive_substate in (
            PlayerAliveState.DOCKED,
            PlayerAliveState.DASHING,
        )


__all__ = [
    "IllegalPlayerTransition",
    "PlayerAliveState",
    "PlayerState",
    "PlayerStateMachine",
]
