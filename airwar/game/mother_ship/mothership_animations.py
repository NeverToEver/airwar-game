"""F08 god-class split: Mothership animation state machines.

This module extracts the entering / docking / undocking animation state
machines from ``GameIntegrator``. The integrator keeps the public
animation query methods (``is_*_animation_active``,
``get_*_animation_progress``, ``get_*_animation_start``) as 1-line
forwarders, and the private ``_*_animation_*`` attributes remain
accessible via property forwarders so existing tests and call sites
work without change.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.config import get_screen_height, get_screen_width

from .event_bus import (
    EVENT_DOCKING_ANIMATION_COMPLETE,
    EVENT_ENTERING_COMPLETE,
    EVENT_UNDOCKING_ANIMATION_COMPLETE,
)

if TYPE_CHECKING:
    from .game_integrator import GameIntegrator


class MothershipAnimations:
    """F08 god-class split: entering / docking / undocking state machines.

    Owns the per-animation flags, frame counters, durations, and target
    positions. State is stored on this object; the integrator exposes
    the legacy ``_*_animation_*`` attribute names via property forwarders
    so existing call sites that read or write those names (including
    tests) keep working without change.
    """

    # ── Entering animation ────────────────────────────────────────────────
    ENTERING_DURATION = 75  # ~1.25s fly-in

    # ── Docking animation ─────────────────────────────────────────────────
    DOCKING_DURATION = 90

    # ── Undocking animation ───────────────────────────────────────────────
    UNDOCKING_EJECT_DURATION = 30
    UNDOCKING_FLYAWAY_DURATION = 90

    def __init__(self, integrator: GameIntegrator) -> None:
        self._integrator = integrator

        # Entering
        self._entering_animation_active = False
        self._entering_animation_frame = 0
        self._entering_start_y: float = 0.0
        self._entering_target_y: float = 0.0
        self._entering_target_x: float = 0.0

        # Docking
        self._docking_animation_active = False
        self._docking_animation_start = None
        self._docking_animation_target = None
        self._docking_animation_frame = 0
        self._docking_start_position = None

        # Undocking
        self._undocking_animation_active = False
        self._undocking_animation_start = None
        self._undocking_animation_target = None
        self._undocking_animation_frame = 0
        self._undocking_start_position = None
        self._undocking_eject_target = None
        self._undocking_phase = 1

    # ── Duration accessors used by the original `_update_*_animation` ────

    @property
    def _entering_duration(self) -> int:
        return self.ENTERING_DURATION

    @property
    def _docking_animation_duration(self) -> int:
        return self.DOCKING_DURATION

    @property
    def _undocking_animation_duration(self) -> int:
        return self.UNDOCKING_EJECT_DURATION  # used for progress reporting

    @property
    def _undocking_eject_duration(self) -> int:
        return self.UNDOCKING_EJECT_DURATION

    @property
    def _undocking_flyaway_duration(self) -> int:
        return self.UNDOCKING_FLYAWAY_DURATION

    # ── Lifecycle hooks called by the integrator ──────────────────────────

    def start_entering(self) -> None:
        """Start the fly-in animation (called via event handler)."""
        screen_width = get_screen_width()
        screen_height = get_screen_height()
        target_x = screen_width // 2
        target_y = int(screen_height * 0.35)
        start_y = screen_height + 200

        self._entering_animation_active = True
        self._entering_animation_frame = 0
        self._entering_target_x = target_x
        self._entering_target_y = target_y
        self._entering_start_y = start_y

        self._integrator._mother_ship.set_position(target_x, start_y)
        self._integrator._mother_ship.show()

    def start_docking(self) -> None:
        """Start the docking animation (called via event handler)."""
        self._docking_animation_active = True
        self._docking_animation_frame = 0
        self._docking_start_position = (
            self._integrator._game_scene.player.rect.x,
            self._integrator._game_scene.player.rect.y,
        )
        # Convert docking bay center to topleft for set_player_position_topleft
        dock_center = self._integrator._mother_ship.get_docking_position()
        pw = self._integrator._game_scene.player.rect.width
        ph = self._integrator._game_scene.player.rect.height
        self._docking_animation_target = (
            dock_center[0] - pw // 2,
            dock_center[1] - ph // 2,
        )
        self._integrator._player_control_disabled = True
        self._integrator._activate_invincibility()

    def start_undocking(self) -> None:
        """Start the undocking animation (called via event handler)."""
        self._undocking_animation_active = True
        self._undocking_animation_frame = 0
        self._undocking_phase = 1
        self._integrator._undocking_cooldown_multiplier = (
            self._integrator._calculate_undocking_cooldown_multiplier()
        )
        self._integrator._progress_bar_ui.hide()

        dock_pos = self._integrator._mother_ship.get_docking_position()
        # Convert docking position (center) to topleft for player rect
        pw = self._integrator._game_scene.player.rect.width
        ph = self._integrator._game_scene.player.rect.height
        start_x = dock_pos[0] - pw // 2
        start_y = dock_pos[1] - ph // 2

        self._undocking_start_position = (start_x, start_y)
        # Eject target: backward and downward from the mothership
        self._undocking_eject_target = (start_x, start_y + 140)

        self._integrator._player_control_disabled = True

    # ── Per-frame tick entry points ──────────────────────────────────────

    def tick_entering(self) -> None:
        self._entering_animation_frame += 1
        progress = min(self._entering_animation_frame / self.ENTERING_DURATION, 1.0)
        eased = self._ease_out_cubic(progress)

        current_y = self._entering_start_y + (self._entering_target_y - self._entering_start_y) * eased
        self._integrator._mother_ship.set_position(int(self._entering_target_x), int(current_y))

        # Fire missiles during fly-in for cover
        self._integrator._update_mothership_firing()
        self._integrator._update_mothership_bullets()

        if progress >= 1.0:
            self._entering_animation_active = False
            self._integrator._event_bus.publish(EVENT_ENTERING_COMPLETE)

    def tick_docking(self) -> None:
        if not self._integrator._game_scene or not self._docking_start_position:
            self._docking_animation_active = False
            return

        self._docking_animation_frame += 1
        progress = min(self._docking_animation_frame / self.DOCKING_DURATION, 1.0)

        eased_progress = self._ease_in_out_cubic(progress)

        start_x, start_y = self._docking_start_position
        target_x, target_y = self._docking_animation_target

        current_x = start_x + (target_x - start_x) * eased_progress
        current_y = start_y + (target_y - start_y) * eased_progress

        self._integrator._game_scene.set_player_position_topleft(current_x, current_y)

        # Continue firing during docking animation for cover fire
        self._integrator._update_mothership_firing()
        self._integrator._update_mothership_bullets()

        if progress >= 1.0:
            self._docking_animation_active = False
            self._docking_animation_frame = 0
            self._integrator._player_control_disabled = False
            self._integrator._event_bus.publish(EVENT_DOCKING_ANIMATION_COMPLETE)

    def tick_undocking(self) -> None:
        if not self._integrator._game_scene or not self._undocking_start_position:
            self._undocking_animation_active = False
            return

        self._undocking_animation_frame += 1

        if self._undocking_phase == 1:
            # Phase 1: eject player backward from docking bay
            progress = min(self._undocking_animation_frame / self.UNDOCKING_EJECT_DURATION, 1.0)
            eased = self._ease_out_quad(progress)

            sx, sy = self._undocking_start_position
            tx, ty = self._undocking_eject_target
            cx = sx + (tx - sx) * eased
            cy = sy + (ty - sy) * eased
            self._integrator._game_scene.set_player_position_topleft(cx, cy)

            if progress >= 1.0:
                # Phase 1 complete — start mothership flyaway
                self._undocking_animation_frame = 0
                self._undocking_phase = 2
                self._integrator._player_control_disabled = False
                self._integrator._deactivate_invincibility()
                self._integrator._mother_ship.activate_flyaway()

        elif self._undocking_phase == 2:
            # Phase 2: mothership flies away upward; player is free
            # Keep updating mothership so flyaway motion continues
            self._integrator._mother_ship.update()

            if not self._integrator._mother_ship.is_visible():
                # Mothership has flown off screen — animation complete
                self._undocking_animation_active = False
                self._undocking_animation_frame = 0
                self._undocking_phase = 1
                self._integrator._mother_ship.deactivate_flyaway()
                self._integrator._apply_cooldown_multiplier_from_player()
                self._integrator._event_bus.publish(EVENT_UNDOCKING_ANIMATION_COMPLETE)
                self._integrator._clear_undocking_cooldown_modifier()

    # ── Easing helpers (unchanged from original) ──────────────────────────

    @staticmethod
    def _ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - ((-2 * t + 2) ** 3) / 2

    @staticmethod
    def _ease_out_quad(t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    @staticmethod
    def _ease_out_cubic(t: float) -> float:
        return 1 - (1 - t) ** 3


__all__ = ["MothershipAnimations"]
