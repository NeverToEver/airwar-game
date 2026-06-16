"""Layered lock arbitration for gameplay state flags."""

import logging
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class LockLayer(IntEnum):
    """Enum defining lock priority layers for state arbitration."""

    HOMECOMING = 100
    MOTHERSHIP = 80
    BOSS_ENRAGE = 60
    PHASE_DASH = 40
    PLAYER_HIT = 30
    GIVE_UP = 20
    GAME_PAUSE = 10


@dataclass
class LockRequest:
    invincible: bool = False
    lock_controls: bool = False
    is_paused: bool = False
    is_silent_invincible: bool = False
    invincibility_duration: int = 0


class LockLayerConflict(RuntimeError):
    """Raised by :meth:`LockManager.acquire_strict` when a layer is
    already locked with a different request. See M-10 for rationale.
    """


class LockManager:
    """Centralized arbitration for player invincibility, control locks, and pause blocking."""

    def __init__(self, game_state, player=None):
        self._game_state = game_state
        self._player = player
        self._locks: dict[LockLayer, LockRequest] = {}
        self._force_timer_update = False

    def set_game_state(self, game_state) -> None:
        self._game_state = game_state
        if self._locks:
            self._recompute()

    def set_player(self, player):
        self._player = player
        if self._locks:
            self._recompute()

    def acquire(self, layer: LockLayer, request: LockRequest):
        """Acquire ``request`` on ``layer``.

        Silently replaces any prior request on the same layer. Use
        :meth:`acquire_strict` if the call site wants to be told about a
        conflict, or :meth:`acquire_or_update` to merge the new request
        with the existing one (max duration, OR of booleans).
        """
        if layer in self._locks:
            prior = self._locks[layer]
            if prior != request:
                logger.debug(
                    "LockManager.acquire overwriting prior request on layer %s: %r -> %r",
                    layer.name, prior, request,
                )
        self._locks[layer] = request
        self._force_timer_update = True
        self._recompute()

    def acquire_or_update(self, layer: LockLayer, request: LockRequest):
        """Acquire ``request`` on ``layer``, merging with the existing
        request if one is present. Booleans are OR-ed together; the
        invincibility timer takes the max of the two; the silent /
        non-silent distinction follows the more-recent call.
        """
        existing = self._locks.get(layer)
        if existing is None:
            self._locks[layer] = request
        else:
            merged = LockRequest(
                invincible=existing.invincible or request.invincible,
                lock_controls=existing.lock_controls or request.lock_controls,
                is_paused=existing.is_paused or request.is_paused,
                is_silent_invincible=(
                    request.is_silent_invincible
                    if request.invincible
                    else existing.is_silent_invincible
                ),
                invincibility_duration=max(
                    existing.invincibility_duration, request.invincibility_duration
                ),
            )
            if merged != existing:
                logger.debug(
                    "LockManager.acquire_or_update merged on layer %s: %r -> %r",
                    layer.name, existing, merged,
                )
            self._locks[layer] = merged
        self._force_timer_update = True
        self._recompute()

    def acquire_strict(self, layer: LockLayer, request: LockRequest):
        """Like :meth:`acquire`, but raise ``LockLayerConflict`` if the
        layer is already locked with a different request. Useful at
        call sites that want a hard failure (rather than a silent
        overwrite) when two systems race for the same layer.
        """
        existing = self._locks.get(layer)
        if existing is not None and existing != request:
            raise LockLayerConflict(
                f"Lock layer {layer.name} already held with a different "
                f"request: {existing!r} vs {request!r}"
            )
        self._locks[layer] = request
        self._force_timer_update = True
        self._recompute()

    def release(self, layer: LockLayer):
        self._locks.pop(layer, None)
        self._force_timer_update = True
        self._recompute()

    def clear(self) -> None:
        self._locks.clear()
        self._force_timer_update = True
        self._recompute()

    def is_locked(self, layer: LockLayer) -> bool:
        return layer in self._locks

    def has_locks(self) -> bool:
        return bool(self._locks)

    def refresh(self) -> None:
        self._recompute()

    def apply_transient_state(
        self,
        *,
        paused: bool | None = None,
        invincible: bool | None = None,
        invincibility_duration: int | None = None,
        silent_invincible: bool | None = None,
    ) -> None:
        if not self._game_state:
            return
        if paused is not None:
            self._game_state.is_paused = paused
        if invincible is not None:
            self._game_state.is_player_invincible = invincible
        if invincibility_duration is not None:
            self._game_state.invincibility_timer = invincibility_duration
        if silent_invincible is not None:
            self._game_state.is_silent_invincible = silent_invincible

    def _recompute(self):
        invincible = False
        lock_controls = False
        paused = False
        silent = False
        timer = 0
        invincibility_applied = False
        for layer in sorted(self._locks.keys(), reverse=True):
            req = self._locks[layer]
            if req.invincible and not invincibility_applied:
                invincible = True
                silent = req.is_silent_invincible
                timer = req.invincibility_duration
                invincibility_applied = True
            if req.lock_controls:
                lock_controls = True
            if req.is_paused:
                paused = True
        if self._game_state:
            was_invincible = getattr(self._game_state, "is_player_invincible", False)
            self._game_state.is_player_invincible = invincible
            # Only update timer from lock duration when:
            # 1. A new lock was just acquired (_force_timer_update)
            # 2. Invincibility is newly activated (wasn't active before)
            # 3. Lock defines permanent invincibility (timer >= 999999)
            # Otherwise preserve the current countdown so _update_invincibility
            # can decrement it each frame.
            if self._force_timer_update or not (invincible and was_invincible) or timer >= 999999:
                self._game_state.invincibility_timer = timer
            self._force_timer_update = False
            self._game_state.is_silent_invincible = silent
            self._game_state.is_paused = paused
        if self._player:
            self._player.is_controls_locked = lock_controls
