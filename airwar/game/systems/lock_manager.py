"""Layered lock arbitration for gameplay state flags."""

import dataclasses
import logging
import time
import uuid
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class LockLayer(IntEnum):
    """Enum defining lock priority layers for state arbitration.

    Higher values win. Within the same layer the most recent request replaces
    the previous one. Across layers, the highest priority request that sets a
    given flag controls that flag: ``lock_controls`` and ``is_paused`` are
    arbitrated by priority (not OR-ed), while invincibility is taken from the
    single highest priority invincible request.
    """

    HOMECOMING = 100
    MOTHERSHIP = 80
    BOSS_ENRAGE = 60
    PHASE_DASH = 40
    PLAYER_HIT = 30
    GIVE_UP = 20
    GAME_PAUSE = 10
    TRANSIENT = 5


@dataclass
class LockRequest:
    invincible: bool = False
    lock_controls: bool = False
    is_paused: bool = False
    is_silent_invincible: bool = False
    invincibility_duration: int = 0
    expires_at: float = 0.0


@dataclass(frozen=True)
class LockToken:
    """Capability token returned by acquire methods.

    The preferred way to release a lock is to pass the token back to
    :meth:`LockManager.release`. Releasing by bare layer still works for
    backwards compatibility but logs a warning.
    """

    layer: LockLayer
    cookie: str = dataclasses.field(default_factory=lambda: uuid.uuid4().hex)


class LockLayerConflict(RuntimeError):
    """Raised by :meth:`LockManager.acquire_strict` when a layer is
    already locked with a different request. See M-10 for rationale.
    """


class LockManager:
    """Centralized arbitration for player invincibility, control locks, and pause blocking."""

    PERMANENT_INVINCIBILITY_FRAMES: int = 999_999

    def __init__(self, game_state, player=None):
        self._game_state = game_state
        self._player = player
        self._locks: dict[LockLayer, LockRequest] = {}
        self._tokens: dict[LockLayer, LockToken] = {}
        self._force_timer_update = False

    def set_game_state(self, game_state) -> None:
        self._game_state = game_state
        if self._locks:
            self._recompute()

    def set_player(self, player):
        if self._player is not None and self._player is not player:
            self._player.is_controls_locked = False
        self._player = player
        if self._locks:
            self._recompute()

    def _validate(self, layer: LockLayer, request: LockRequest) -> None:
        if not isinstance(layer, LockLayer):
            raise ValueError(f"Invalid lock layer: {layer!r}")
        if request.invincibility_duration < 0:
            raise ValueError("invincibility_duration must be non-negative")
        for field in ("invincible", "lock_controls", "is_paused", "is_silent_invincible"):
            if not isinstance(getattr(request, field), bool):
                raise ValueError(f"{field} must be a bool, got {type(getattr(request, field)).__name__}")

    @staticmethod
    def _with_expires_at(request: LockRequest) -> LockRequest:
        """Return a copy of ``request`` with ``expires_at`` computed from ``invincibility_duration``."""
        if request.expires_at <= 0 and request.invincibility_duration > 0:
            return dataclasses.replace(
                request, expires_at=time.monotonic() + request.invincibility_duration
            )
        return request

    def acquire(self, layer: LockLayer, request: LockRequest) -> LockToken:
        """Acquire ``request`` on ``layer``.

        Silently replaces any prior request on the same layer. Use
        :meth:`acquire_strict` if the call site wants to be told about a
        conflict, or :meth:`acquire_or_update` to merge the new request
        with the existing one (max duration, OR of booleans).

        Returns a :class:`LockToken` that should be used to release the lock.
        """
        self._validate(layer, request)
        request = self._with_expires_at(request)
        if layer in self._locks:
            prior = self._locks[layer]
            if prior != request:
                logger.debug(
                    "LockManager.acquire overwriting prior request on layer %s: %r -> %r",
                    layer.name, prior, request,
                )
        token = LockToken(layer)
        self._locks[layer] = request
        self._tokens[layer] = token
        self._force_timer_update = True
        self._recompute()
        return token

    def acquire_or_update(self, layer: LockLayer, request: LockRequest) -> LockToken:
        """Acquire ``request`` on ``layer``, merging with the existing
        request if one is present. Booleans are OR-ed together; the
        invincibility timer takes the max of the two; the silent /
        non-silent distinction follows the more-recent call.

        Returns a :class:`LockToken` for the resulting lock.
        """
        self._validate(layer, request)
        request = self._with_expires_at(request)
        existing = self._locks.get(layer)
        if existing is None:
            self._locks[layer] = request
        else:
            existing = self._with_expires_at(existing)
            merged_expires_at = 0.0
            if existing.invincible and request.invincible:
                merged_expires_at = (
                    existing.expires_at
                    if request.expires_at <= existing.expires_at
                    else request.expires_at
                )
            elif request.invincible:
                merged_expires_at = request.expires_at
            elif existing.invincible:
                merged_expires_at = existing.expires_at
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
                expires_at=merged_expires_at,
            )
            if merged != existing:
                logger.debug(
                    "LockManager.acquire_or_update merged on layer %s: %r -> %r",
                    layer.name, existing, merged,
                )
            self._locks[layer] = merged
        token = LockToken(layer)
        self._tokens[layer] = token
        self._force_timer_update = True
        self._recompute()
        return token

    def acquire_strict(self, layer: LockLayer, request: LockRequest) -> LockToken:
        """Like :meth:`acquire`, but raise ``LockLayerConflict`` if the
        layer is already locked with a different request. Useful at
        call sites that want a hard failure (rather than a silent
        overwrite) when two systems race for the same layer.

        Returns a :class:`LockToken` for the resulting lock.
        """
        self._validate(layer, request)
        request = self._with_expires_at(request)
        existing = self._locks.get(layer)
        if existing is not None and existing != request:
            raise LockLayerConflict(
                f"Lock layer {layer.name} already held with a different "
                f"request: {existing!r} vs {request!r}"
            )
        token = LockToken(layer)
        self._locks[layer] = request
        self._tokens[layer] = token
        self._force_timer_update = True
        self._recompute()
        return token

    def release(self, token: LockLayer | LockToken) -> bool:
        """Release a lock.

        Accepts a :class:`LockToken` returned by an ``acquire*`` method,
        or a bare :class:`LockLayer` for backwards compatibility. Passing a
        bare layer logs a warning because it bypasses the token owner check.
        """
        if isinstance(token, LockToken):
            layer = token.layer
            current = self._tokens.get(layer)
            if current is None or current.cookie != token.cookie:
                logger.warning(
                    "Ignoring release of layer %s with stale/mismatched LockToken", layer.name
                )
                return False
            self._locks.pop(layer, None)
            self._tokens.pop(layer, None)
            self._force_timer_update = True
            self._recompute()
            return True

        return self._release_layer(token, warn=True)

    def _release_layer(self, layer: LockLayer, *, warn: bool) -> bool:
        removed = self._locks.pop(layer, None)
        self._tokens.pop(layer, None)
        if removed is not None:
            if warn:
                logger.warning(
                    "Releasing lock by layer %r without token; prefer using token from acquire",
                    layer.name,
                )
            self._force_timer_update = True
        self._recompute()
        return removed is not None

    def clear(self) -> None:
        self._locks.clear()
        self._tokens.clear()
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
        existing = self._locks.get(LockLayer.TRANSIENT)
        merged_kwargs = dataclasses.asdict(existing) if existing else {}
        if paused is not None:
            merged_kwargs["is_paused"] = paused
        if invincible is not None:
            merged_kwargs["invincible"] = invincible
        if invincibility_duration is not None:
            merged_kwargs["invincibility_duration"] = invincibility_duration
            merged_kwargs["invincible"] = True
        if silent_invincible is not None:
            merged_kwargs["is_silent_invincible"] = silent_invincible

        has_active_state = any(
            merged_kwargs.get(k) for k in ("invincible", "lock_controls", "is_paused")
        ) or bool(merged_kwargs.get("invincibility_duration"))

        if has_active_state:
            self.acquire_or_update(LockLayer.TRANSIENT, LockRequest(**merged_kwargs))
        else:
            self._release_layer(LockLayer.TRANSIENT, warn=False)
            if silent_invincible is not None and self._game_state:
                # Preserve the legacy direct-flag behavior when only the silent
                # bit is toggled without an accompanying invincibility request.
                self._game_state.is_silent_invincible = silent_invincible

    def _recompute(self):
        now = time.monotonic()
        expired = [
            layer
            for layer, req in self._locks.items()
            if req.expires_at > 0
            and req.expires_at <= now
            and req.invincibility_duration < self.PERMANENT_INVINCIBILITY_FRAMES
        ]
        for layer in expired:
            logger.debug("Lock %s expired, removing", layer.name)
            self._locks.pop(layer, None)
            self._tokens.pop(layer, None)

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
                if req.expires_at > 0:
                    timer = round(max(0, req.expires_at - time.monotonic()))
                else:
                    timer = req.invincibility_duration
                invincibility_applied = True
            # Priority arbitration: once a higher-priority layer sets a flag,
            # lower-priority layers can no longer override it.
            if req.lock_controls and not lock_controls:
                lock_controls = True
            if req.is_paused and not paused:
                paused = True
            if lock_controls and paused and invincibility_applied:
                break
        if self._game_state:
            was_invincible = getattr(self._game_state, "is_player_invincible", False)
            self._game_state.is_player_invincible = invincible
            # Only update timer from lock duration when:
            # 1. A new lock was just acquired (_force_timer_update)
            # 2. Invincibility is newly activated (wasn't active before)
            # 3. Lock defines permanent invincibility
            # Otherwise preserve the current countdown so _update_invincibility
            # can decrement it each frame.
            if (
                self._force_timer_update
                or not (invincible and was_invincible)
                or timer >= self.PERMANENT_INVINCIBILITY_FRAMES
            ):
                self._game_state.invincibility_timer = timer
            self._force_timer_update = False
            self._game_state.is_silent_invincible = silent
            self._game_state.is_paused = paused
        if self._player:
            self._player.is_controls_locked = lock_controls
