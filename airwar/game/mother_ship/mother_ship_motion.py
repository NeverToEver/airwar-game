"""Mothership motion — visibility, position, flyaway, and animation.

Extracted from :class:`MotherShip` in Phase 5-γ. Owns the 11
state-and-motion methods plus ``update`` (the motion integrator) and
``update_animation`` (the per-frame pulse calc). The renderer
(:class:`MotherShipRenderer`) reads position + pulse values from this
component via the coordinator reference.
"""

import math

import pygame


class MotherShipMotion:
    """Position, visibility, flyaway, and pulse state for the mothership.

    Public surface (called by :class:`MotherShip` facade):

    - :meth:`show` / :meth:`hide` / :meth:`is_visible` — visibility
    - :meth:`set_position` — explicit teleport
    - :meth:`show_phantom` / :meth:`hide_phantom` — phantom preview toggle
    - :meth:`set_player_input` — WASD/arrow input for the docked ship
    - :meth:`activate_flyaway` / :meth:`deactivate_flyaway` /
      :meth:`is_flyaway_mode` — exit-from-screen motion
    - :meth:`get_docking_position` — bay coordinates for docking
    - :meth:`update_animation` — per-frame pulse calc
    - :meth:`update` — per-frame motion integrator

    Owned attributes (read by :class:`MotherShipRenderer`):
    ``_visible``, ``_phantom_visible``, ``_phantom_started_at``,
    ``_phantom_fade_duration_ms``, ``_initial_x``, ``_initial_y``,
    ``_position``, ``_animation_time``, ``_velocity``,
    ``_player_input``, ``_engine_pulse``, ``_wing_pulse``,
    ``_flyaway_mode``, ``_flyaway_velocity_y``, ``_flyaway_accel``,
    plus ``_screen_width`` / ``_screen_height`` for arena clamping.
    """

    DOCKING_BAY_X_OFFSET = 0
    DOCKING_BAY_Y_OFFSET = 85

    ACCELERATION = 0.25
    MAX_SPEED = 3.0
    FRICTION = 1.0  # No friction — direct response, symmetric feel

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._visible = False
        self._phantom_visible = False
        self._phantom_started_at = 0
        self._phantom_fade_duration_ms = 520
        self._initial_x = screen_width // 2
        self._initial_y = int(screen_height * 0.35)
        self._position = (self._initial_x, self._initial_y)
        self._animation_time = 0

        self._velocity = [0.0, 0.0]
        self._player_input = [0, 0]

        self._engine_pulse = 0.0
        self._wing_pulse = 0.0

        self._flyaway_mode = False
        self._flyaway_velocity_y = 0.0
        self._flyaway_accel = 0.15

    # ── Visibility ────────────────────────────────────────────────────────

    def show(self) -> None:
        self._visible = True
        self._animation_time = 0

    def hide(self) -> None:
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def set_position(self, x: int, y: int) -> None:
        self._position = (x, y)

    # ── Phantom preview ───────────────────────────────────────────────────

    def show_phantom(self) -> None:
        if not self._phantom_visible:
            self._phantom_started_at = pygame.time.get_ticks()
        self._phantom_visible = True

    def hide_phantom(self) -> None:
        self._phantom_visible = False
        self._phantom_started_at = 0

    # ── Docked-ship input ─────────────────────────────────────────────────

    def set_player_input(self, x: int, y: int) -> None:
        self._player_input = [x, y]

    # ── Flyaway ───────────────────────────────────────────────────────────

    def activate_flyaway(self) -> None:
        """Enter flyaway mode: accelerate upward and exit screen top."""
        self._flyaway_mode = True
        self._flyaway_velocity_y = 0.0

    def deactivate_flyaway(self) -> None:
        """Exit flyaway mode."""
        self._flyaway_mode = False
        self._flyaway_velocity_y = 0.0

    def is_flyaway_mode(self) -> bool:
        return self._flyaway_mode

    def get_docking_position(self) -> tuple:
        return (
            self._position[0] + self.DOCKING_BAY_X_OFFSET,
            self._position[1] + self.DOCKING_BAY_Y_OFFSET,
        )

    # ── Animation / motion ────────────────────────────────────────────────

    def update_animation(self) -> None:
        if self._visible:
            self._animation_time += 0.05
            self._engine_pulse = 0.5 + 0.5 * math.sin(self._animation_time * 2)
            self._wing_pulse = 0.3 + 0.3 * math.sin(self._animation_time * 1.5)

    def update(self) -> None:
        if not self._visible:
            return

        if self._flyaway_mode:
            self._flyaway_velocity_y -= self._flyaway_accel
            new_x = self._position[0]
            new_y = self._position[1] + self._flyaway_velocity_y
            self._position = (int(new_x), int(new_y))
            # Auto-hide when fully off the top of the screen
            if new_y < -200:
                self.hide()
                self._flyaway_mode = False
            return

        self._velocity[0] += self._player_input[0] * self.ACCELERATION
        self._velocity[1] += self._player_input[1] * self.ACCELERATION
        for i in range(2):
            if abs(self._velocity[i]) > self.MAX_SPEED:
                self._velocity[i] = self.MAX_SPEED if self._velocity[i] > 0 else -self.MAX_SPEED
        if self._player_input[0] == 0:
            self._velocity[0] *= self.FRICTION
        if self._player_input[1] == 0:
            self._velocity[1] *= self.FRICTION
        new_x = self._position[0] + self._velocity[0]
        new_y = self._position[1] + self._velocity[1]
        new_x = max(130, min(self._screen_width - 130, new_x))
        new_y = max(80, min(self._screen_height - 150, new_y))
        self._position = (int(new_x), int(new_y))


__all__ = ["MotherShipMotion"]
