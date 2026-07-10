"""Player phase-dash component.

Owns: phase-dash state machine (READY/WINDUP/ACTIVE/RECOVERY), the
energy cost, the cooldown timer, the start/target positions, and
the invincibility window.

Extracted from the original Player class to keep dash state local to the
ability that owns it.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING

from airwar.config import get_screen_height, get_screen_width

from .boost import PlayerBoost

if TYPE_CHECKING:  # pragma: no cover - typing only
    from airwar.entities.player import Player


class PhaseDashState(Enum):
    """Phase dash ability lifecycle states."""

    READY = "ready"
    WINDUP = "windup"
    ACTIVE = "active"
    RECOVERY = "recovery"


class PlayerPhaseDash:
    """Phase-dash state machine, energy cost, and invincibility.

    Args:
        owner: The Player instance (reads ``rect`` for position,
            ``boost`` for energy accounting).
    """

    COST_RATIO = 0.25
    WINDUP_FRAMES = 5
    ACTIVE_FRAMES = 14
    RECOVERY_FRAMES = 8
    COOLDOWN_FRAMES = 90
    DISTANCE = 250
    MIN_DISTANCE = 120
    ALPHA_MIN = 75
    ALPHA_MAX = 165

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self._state: PhaseDashState = PhaseDashState.READY
        self._timer: int = 0
        self._cooldown: int = 0
        self._start: tuple[float, float] = (0.0, 0.0)
        self._target: tuple[float, float] = (0.0, 0.0)
        self._direction: tuple[float, float] = (0.0, -1.0)
        # Cache the master's pulse timer so we don't read a private attr
        # across the boundary at call sites.
        self._hitbox_timer: int = 0

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def state(self) -> PhaseDashState:
        return self._state

    @state.setter
    def state(self, value: PhaseDashState) -> None:
        self._state = value

    @property
    def timer(self) -> int:
        return self._timer

    @timer.setter
    def timer(self, value: int) -> None:
        self._timer = value

    @property
    def cooldown(self) -> int:
        return self._cooldown

    @cooldown.setter
    def cooldown(self, value: int) -> None:
        self._cooldown = value

    @property
    def max_cooldown(self) -> int:
        return self.COOLDOWN_FRAMES

    @property
    def direction(self) -> tuple[float, float]:
        return self._direction

    @property
    def hitbox_timer(self) -> int:
        return self._hitbox_timer

    @hitbox_timer.setter
    def hitbox_timer(self, value: int) -> None:
        self._hitbox_timer = value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_dashing(self) -> bool:
        return self._state in {PhaseDashState.WINDUP, PhaseDashState.ACTIVE, PhaseDashState.RECOVERY}

    def is_invincible(self) -> bool:
        return self.is_dashing()

    def is_enabled(self) -> bool:
        return bool(self._owner.is_phase_dash_enabled)

    def can_dash(self) -> bool:
        boost: PlayerBoost = self._owner.boost
        return (
            self.is_enabled()
            and self._state == PhaseDashState.READY
            and self._cooldown <= 0
            and boost.boost_current >= self._cost()
        )

    def start(self, direction) -> None:
        """Begin a phase dash. Energy is deducted immediately."""
        owner = self._owner
        boost: PlayerBoost = owner.boost
        boost.boost_current = max(0, boost.boost_current - self._cost())
        boost.reset_idle()
        dx, dy = direction.x, direction.y
        if dx == 0 and dy == 0:
            dx, dy = self._direction
        length = math.hypot(dx, dy)
        if length <= 0:
            dx, dy = 0.0, -1.0
        else:
            dx, dy = dx / length, dy / length
        self._direction = (dx, dy)
        self._state = PhaseDashState.WINDUP
        self._timer = self.WINDUP_FRAMES
        self._start = (owner.rect.x, owner.rect.y)
        target_x = owner.rect.x + dx * self.DISTANCE
        target_y = owner.rect.y + dy * self.DISTANCE
        max_x = get_screen_width() - owner.rect.width
        max_y = get_screen_height() - owner.rect.height
        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))
        if math.hypot(target_x - owner.rect.x, target_y - owner.rect.y) < self.MIN_DISTANCE:
            target_x = max(0, min(owner.rect.x + dx * self.MIN_DISTANCE, max_x))
            target_y = max(0, min(owner.rect.y + dy * self.MIN_DISTANCE, max_y))
        self._target = (target_x, target_y)

    def tick_cooldown(self) -> None:
        if self._cooldown > 0:
            self._cooldown -= 1

    def update_motion(self) -> None:
        """Advance the dash motion. Called by Player while ``is_dashing()``."""
        owner = self._owner
        if self._state == PhaseDashState.WINDUP:
            self._timer -= 1
            if self._timer <= 0:
                self._state = PhaseDashState.ACTIVE
                self._timer = 0
            return

        if self._state == PhaseDashState.ACTIVE:
            self._timer += 1
            progress = min(1.0, self._timer / self.ACTIVE_FRAMES)
            eased = 1 - (1 - progress) * (1 - progress)
            owner.rect.x = self._start[0] + (self._target[0] - self._start[0]) * eased
            owner.rect.y = self._start[1] + (self._target[1] - self._start[1]) * eased
            if progress >= 1.0:
                self._state = PhaseDashState.RECOVERY
                self._timer = self.RECOVERY_FRAMES
            return

        if self._state == PhaseDashState.RECOVERY:
            self._timer -= 1
            if self._timer <= 0:
                self._state = PhaseDashState.READY
                self._cooldown = self.COOLDOWN_FRAMES

    def alpha(self) -> int:
        """Alpha to apply to the player sprite during a dash."""
        if self._state == PhaseDashState.WINDUP:
            return 210
        if self._state == PhaseDashState.RECOVERY:
            progress = 1 - max(0, self._timer) / self.RECOVERY_FRAMES
            return int(self.ALPHA_MAX + (255 - self.ALPHA_MAX) * progress)
        pulse = abs(math.sin(self._hitbox_timer * 0.8))
        return int(self.ALPHA_MIN + (self.ALPHA_MAX - self.ALPHA_MIN) * pulse)

    def progress(self) -> float:
        """Best-effort progress for the boost HUD."""
        return 0.0 if self._cooldown <= 0 else 1.0 - (self._cooldown / self.COOLDOWN_FRAMES)

    def _cost(self) -> float:
        return self._owner.boost.boost_max * self.COST_RATIO
