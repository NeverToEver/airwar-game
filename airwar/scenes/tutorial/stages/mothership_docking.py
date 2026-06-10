"""Mothership-docking tutorial stage (id ``mothership_docking``).

Four-phase flow driven by ``scene._dock_sub_phase``:

1. ``approach`` -- hold H to fill the dock hold bar; on full the
   player transitions to ``entering``.
2. ``entering`` -- 30-frame eased pull toward the mothership docking
   bay. Player controls and damage stay locked.
3. ``docked`` -- the mothership fires a missile-volley at the nearest
   active enemy on a fixed cadence. Ammo drains continuously; once
   the magazine empties we transition to ``eject_player``.
4. ``eject_player`` -- two-phase un-dock: player is pushed downward
   for ``dock_undock_player_frames`` then the mothership itself
   accelerates off-screen for ``DOCK_UNDOCK_FRAMES``.

The stage also drives the ``_advance_after_delay`` countdown when the
scene marks the stage complete (per the legacy coordinator).
"""

from __future__ import annotations

import pygame

from .base import BaseStage

MOTHERSHIP_STAGE_ID = "mothership_docking"


class MothershipDockingStage(BaseStage):
    """Per-frame mothership-docking stage logic.

    Reads and mutates the scene's existing state attributes (e.g.
    ``_dock_sub_phase``, ``_hold_h_frames``, ``_mothership_ammo``) so
    the rest of the scene (renderer, mission data, completion check)
    keeps working unchanged.
    """

    stage_id: str = MOTHERSHIP_STAGE_ID

    def update(self) -> None:
        scene = self._scene
        self._update_mothership(scene)
        sub_phase = scene._dock_sub_phase
        if sub_phase == "approach":
            self._update_approach(scene)
        elif sub_phase == "entering":
            self._update_entering(scene)
        elif sub_phase == "docked":
            self._update_docked(scene)
        elif sub_phase == "eject_player":
            self._update_eject(scene)

        if scene._stage_completed:
            scene._advance_after_delay()

    # -- Helpers --------------------------------------------------------

    def _update_mothership(self, scene) -> None:
        mothership = scene._mothership
        if mothership is None:
            return
        sw, sh = scene._get_screen_dimensions()
        mothership_departing = scene._dock_sub_phase == "eject_player" and scene._dock_undock_phase == "mothership"
        if not mothership_departing:
            mothership.show()
        mothership.set_player_input(0, 0)
        if not mothership_departing:
            mothership.set_position(sw // 2, max(190, int(sh * 0.32)))
        mothership.update()

    # -- Sub-phase updates --------------------------------------------

    def _update_approach(self, scene) -> None:
        if scene._mothership:
            scene._mothership.show()
            scene._mothership.show_phantom()

        if pygame.K_h in scene._keys_down:
            scene._hold_h_frames = min(scene.DOCK_HOLD_FRAMES, scene._hold_h_frames + 1)
        else:
            scene._hold_h_frames = max(0, scene._hold_h_frames - 3)

        if scene._hold_h_frames < scene.DOCK_HOLD_FRAMES:
            return

        scene._dock_sub_phase = "entering"
        scene._player_enter_timer = 0
        scene._player_enter_start_center = pygame.Vector2(scene._player.center)
        scene._docked = False
        scene._bullets.clear()
        scene._enemy_bullets.clear()
        if scene._mothership:
            scene._mothership.hide_phantom()

    def _update_entering(self, scene) -> None:
        scene._player_enter_timer = min(scene.DOCK_ENTER_FRAMES, scene._player_enter_timer + 1)
        t = scene._player_enter_timer / scene.DOCK_ENTER_FRAMES
        eased = t * t
        target = pygame.Vector2(scene._docking_player_center())
        current = scene._player_enter_start_center.lerp(target, eased)
        scene._player.center = (round(current.x), round(current.y))

        if scene._player_enter_timer < scene.DOCK_ENTER_FRAMES:
            return

        scene._dock_sub_phase = "docked"
        scene._docked = True
        scene._mothership_ammo = scene.MOTHERSHIP_STARTING_AMMO
        scene._mothership_fire_timer = scene.MOTHERSHIP_VOLLEY_FRAMES
        scene._player.center = scene._docking_player_center()
        if scene._mothership:
            scene._mothership.hide_phantom()

    def _update_docked(self, scene) -> None:
        scene._player.center = scene._docking_player_center()
        if scene._mothership:
            scene._mothership.hide_phantom()

        scene._mothership_fire_timer -= 1
        if scene._mothership_fire_timer <= 0:
            scene._mothership_fire_timer = scene.MOTHERSHIP_VOLLEY_FRAMES
            scene._mothership_destroy_nearest_enemy()

        scene._mothership_ammo = max(0.0, scene._mothership_ammo - scene.MOTHERSHIP_AMMO_DRAIN)
        if not scene._ammo_warning_triggered and scene._mothership_ammo < scene.WARNING_CELL_THRESHOLD:
            scene._ammo_warning_triggered = True
            if scene._warning_banner:
                scene._warning_banner.activate()

        if scene._mothership_ammo <= 0:
            scene._dock_sub_phase = "eject_player"
            scene._dock_undock_timer = scene._dock_undock_player_frames
            scene._dock_undock_phase = "player"
            scene._dock_eject_position = pygame.Vector2(scene._player.center)
            scene._docked = False
            if scene._mothership:
                scene._mothership.hide_phantom()

    def _update_eject(self, scene) -> None:
        if scene._dock_undock_phase == "player":
            elapsed = scene._dock_undock_player_frames - scene._dock_undock_timer + 1
            progress = min(1.0, elapsed / scene._dock_undock_player_frames)
            eased = 1 - (1 - progress) * (1 - progress)
            _, sh = scene._get_screen_dimensions()
            target_y = min(sh - 90, scene._dock_eject_position.y + 140)
            current_y = scene._dock_eject_position.y + (target_y - scene._dock_eject_position.y) * eased
            scene._player.center = (round(scene._dock_eject_position.x), round(current_y))
            scene._dock_undock_timer = max(0, scene._dock_undock_timer - 1)
            if scene._dock_undock_timer > 0:
                return

            scene._dock_undock_phase = "mothership"
            scene._dock_undock_timer = scene.DOCK_UNDOCK_FRAMES
            if scene._mothership:
                scene._mothership.activate_flyaway()
            return

        if scene._dock_undock_phase == "mothership":
            scene._dock_undock_timer = max(0, scene._dock_undock_timer - 1)


__all__ = ["MOTHERSHIP_STAGE_ID", "MothershipDockingStage"]
