"""Player movement component.

Owns: position update, ctrl/precision mode, input-mode settings
(hold vs toggle), and movement speed multiplication logic.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
The component holds no mutable state outside ``ctrl_mode`` and
``shift_boost_mode``; speed and base_speed live on the Player for
backward-compat (read by 30+ callers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.config import get_screen_height, get_screen_width

if TYPE_CHECKING:
    from airwar.protocols import InputSourceProtocol


class PlayerMovement:
    """Movement state: position update, ctrl/precision, input modes.

    Args:
        owner: The Player instance that owns this component. Required
            because the component reads the player's ``rect``,
            ``base_speed``, and several cross-component flags.
        input_handler: Source of movement direction / boost / precision
            key state.
    """

    def __init__(self, owner, input_handler: InputSourceProtocol) -> None:
        self._owner = owner
        self._input_handler = input_handler
        # Input mode: 'hold' (default) or 'toggle'
        self.ctrl_mode: str = "hold"
        self.shift_boost_mode: str = "hold"
        # Toggle-mode latches
        self._precision_toggle_active: bool = False
        self._boost_toggle_active: bool = False
        # Boost edge detection (last frame pressed state)
        self._boost_pressed_last_frame = False

    # ------------------------------------------------------------------
    # Public API (called by Player or by tests)
    # ------------------------------------------------------------------

    @property
    def precision_active(self) -> bool:
        if self.ctrl_mode == "toggle":
            return self._precision_toggle_active
        return self._input_handler.is_precision_pressed()

    def apply_settings(self, settings: dict) -> None:
        """Apply the player's input-mode settings (hold vs toggle).

        Mirrors the legacy behavior: when transitioning away from
        ``toggle`` for either key, the toggle latch is cleared.
        """
        new_ctrl = settings.get("ctrl_mode", "hold")
        new_shift = settings.get("shift_boost_mode", "hold")
        if new_ctrl != "toggle" and self.ctrl_mode == "toggle":
            self._precision_toggle_active = False
        if new_shift != "toggle" and self.shift_boost_mode == "toggle":
            self._boost_toggle_active = False
        self.ctrl_mode = new_ctrl
        self.shift_boost_mode = new_shift

    def is_precision_pressed(self) -> bool:
        """Underlying precision press, regardless of mode."""
        return self._input_handler.is_precision_pressed()

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Run one frame of movement. Player dispatches to this AFTER
        checking ``is_controls_locked`` and AFTER the phase-dash/boost
        logic has determined whether normal movement should occur.

        Position is clamped to the screen bounds (0..screen_w - rect.w,
        0..screen_h - rect.h). Speed is read from the owner so callers
        can still tweak it (precision mode sets
        ``owner.speed = owner.base_speed * PRECISION_SPEED_MULT``).
        """
        owner = self._owner
        direction = self._input_handler.get_movement_direction()
        owner.rect.x += direction.x * owner.speed
        owner.rect.y += direction.y * owner.speed
        owner.rect.x = max(0, min(owner.rect.x, get_screen_width() - owner.rect.width))
        owner.rect.y = max(0, min(owner.rect.y, get_screen_height() - owner.rect.height))

    def update_precision_state(self) -> bool:
        """Read the precision key + update the toggle latch.

        Returns:
            Whether precision mode is active for the current frame.
        """
        ctrl_pressed = self._input_handler.is_precision_pressed()
        if self.ctrl_mode == "toggle":
            ctrl_just_pressed = self._input_handler.is_precision_just_pressed()
            if ctrl_just_pressed:
                self._precision_toggle_active = not self._precision_toggle_active
            return self._precision_toggle_active
        return ctrl_pressed
