"""Layered lock arbitration for gameplay state flags."""

from dataclasses import dataclass
from enum import IntEnum


class LockLayer(IntEnum):
    HOMECOMING = 100
    MOTHERSHIP = 80
    BOSS_ENRAGE = 60
    PHASE_DASH = 40
    GIVE_UP = 20


@dataclass
class LockRequest:
    invincible: bool = False
    lock_controls: bool = False
    paused: bool = False
    silent_invincible: bool = False
    invincibility_duration: int = 0


class LockManager:
    def __init__(self, game_state, player=None):
        self._game_state = game_state
        self._player = player
        self._locks: dict[LockLayer, LockRequest] = {}

    def set_game_state(self, game_state) -> None:
        self._game_state = game_state
        if self._locks:
            self._recompute()

    def set_player(self, player):
        self._player = player
        if self._locks:
            self._recompute()

    def acquire(self, layer: LockLayer, request: LockRequest):
        self._locks[layer] = request
        self._recompute()

    def release(self, layer: LockLayer):
        self._locks.pop(layer, None)
        self._recompute()

    def clear(self) -> None:
        self._locks.clear()
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
            self._game_state.paused = paused
        if invincible is not None:
            self._game_state.player_invincible = invincible
        if invincibility_duration is not None:
            self._game_state.invincibility_timer = invincibility_duration
        if silent_invincible is not None:
            self._game_state.silent_invincible = silent_invincible

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
                silent = req.silent_invincible
                timer = req.invincibility_duration
                invincibility_applied = True
            if req.lock_controls:
                lock_controls = True
            if req.paused:
                paused = True
        if self._game_state:
            self._game_state.player_invincible = invincible
            self._game_state.invincibility_timer = timer
            self._game_state.silent_invincible = silent
            self._game_state.paused = paused
        if self._player:
            self._player.controls_locked = lock_controls
