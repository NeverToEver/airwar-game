"""Player boost component.

Owns: boost energy (current/max), recovery rate, recovery delay,
ramp, and the ``is_boost_active`` flag.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
Energy values and the active flag are exposed as Player-level
attributes (read by 30+ callers) that delegate here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.player import Player


class PlayerBoost:
    """Boost energy, recovery ramp, and active-flag bookkeeping.

    Args:
        owner: The Player instance (reads ``boost_max``/``boost_current``
            via attributes that delegate back here, and writes
            ``owner.is_boost_active``).
    """

    DEFAULT_RECOVERY_RATE = 1.0
    DEFAULT_BOOST_MAX = 200
    DEFAULT_RECOVERY_DELAY = 90
    DEFAULT_RECOVERY_RAMP = 120
    BOOST_RAMP_MIN = 0.15
    BOOST_RAMP_DELTA = 0.85
    DEFAULT_SPEED_MULT = 1.7

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self.is_boost_active: bool = False
        self.boost_max: float = self.DEFAULT_BOOST_MAX
        self.boost_current: float = self.DEFAULT_BOOST_MAX
        self.boost_recovery_rate: float = self.DEFAULT_RECOVERY_RATE
        self.boost_recovery_delay: int = self.DEFAULT_RECOVERY_DELAY
        self.boost_recovery_ramp: int = self.DEFAULT_RECOVERY_RAMP
        # Per-difficulty speed multiplier (legacy: constant 1.7).
        self._boost_speed_mult: float = self.DEFAULT_SPEED_MULT
        # Idle counter used by recovery ramp (frames since last consume).
        self._boost_idle_frames: int = 0
        # Toggle-mode latch (set by movement component on key edge).
        self._boost_toggle_active: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def consume_one_frame(self) -> None:
        """Drain one frame of boost (called by movement during boost)."""
        self.boost_current = max(0, self.boost_current - 1)

    def set_active_flag(self, value: bool) -> None:
        """Update the active flag (set by movement each frame)."""
        self.is_boost_active = value

    def set_toggle_active(self, value: bool) -> None:
        """Set the toggle latch (used by movement on key edge)."""
        self._boost_toggle_active = value

    def read_toggle_active(self) -> bool:
        return self._boost_toggle_active

    def is_boost_active_q(self) -> bool:
        """Expose boost_active without the collision-prone name."""
        return self.is_boost_active

    def reset_idle(self) -> None:
        self._boost_idle_frames = 0

    def update_recovery(self, active_blocked: bool = False) -> None:
        """Tick the recovery ramp.

        Args:
            active_blocked: True when boost is intentionally suppressed
                (e.g. during phase-dash). The active flag is forced
                False, but recovery still advances so the next time the
                player boosts the energy is ready.
        """
        if active_blocked:
            self.is_boost_active = False
        self._boost_idle_frames += 1
        if self._boost_idle_frames > self.boost_recovery_delay:
            ramp_frames = self._boost_idle_frames - self.boost_recovery_delay
            t = 1.0 if self.boost_recovery_ramp <= 0 else min(1.0, ramp_frames / self.boost_recovery_ramp)
            rate = self.boost_recovery_rate * (self.BOOST_RAMP_MIN + self.BOOST_RAMP_DELTA * t)
            self.boost_current = min(self.boost_max, self.boost_current + rate)
