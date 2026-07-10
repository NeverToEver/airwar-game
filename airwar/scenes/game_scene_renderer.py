"""GameScene rendering coordinator.

After the Phase 4 split, :meth:`GameScene.render` is a thin delegation
to :class:`GameSceneRenderer`. This keeps the scene class focused on
game-loop orchestration and lets the render path be reviewed /
modified without touching the rest of the scene.

Layering contract (top-of-screen wins):
    game renderer
    -> haunting world
    -> bullets + haunting post bullets
    -> HUD + buff stats
    -> pause button
    -> boost gauge
    -> ammo magazine
    -> mothership
    -> boss enrage overlay
    -> explosions
    -> give-up UI
    -> homecoming progress
    -> warning banner
    -> aim crosshair
    -> haunting HUD corruption
    -> homecoming sequence
    -> base talent console
    -> reward selector
    -> notifications (topmost)
    -> haunting foreground
    -> haunting transition flicker
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_scene import GameScene


class GameSceneRenderer:
    """Per-frame rendering for :class:`GameScene`.

    Owns no game state of its own; reads from the scene and forwards
    each section to the appropriate sub-renderer.
    """

    def __init__(self, scene: GameScene) -> None:
        self._scene = scene
        # Low-health effects are only occasional, but allocating full-screen
        # alpha surfaces when they do fire causes visible frame-time spikes.
        self._damage_overlay_size: tuple[int, int] | None = None
        self._damage_aberration = None
        self._damage_flash = None
        self._damage_aberration_frame = 0

    def dispose(self) -> None:
        """Release full-screen transient effect surfaces on scene exit."""
        self._damage_overlay_size = None
        self._damage_aberration = None
        self._damage_flash = None
        self._damage_aberration_frame = 0

    def render(self, surface) -> None:
        scene = self._scene
        is_docked = bool(scene._mother_ship_integrator and scene._mother_ship_integrator.is_docked())
        if scene.game_renderer:
            scene.game_renderer.entity_renderer.player_docked = is_docked
        if scene._ui_manager:
            scene._ui_manager.set_player_docked(is_docked)

        scene._ui_manager.render_game(
            surface, scene.player, scene.spawn_controller.enemies, scene.spawn_controller.boss
        )
        scene._render_haunting_world(surface)
        scene._ui_manager.render_bullets(surface, scene.player, scene.spawn_controller.enemy_bullets)
        scene._render_haunting_post_bullets(surface)
        scene._ui_manager.render_hud(surface, scene.player)
        scene._ui_manager.render_buff_stats_panel(surface, scene.player)
        scene._render_pause_button(surface)
        self._render_boost_gauge(surface)
        self._render_ammo_magazine(surface)
        self._render_mothership(surface)
        self._render_boss_enrage(surface, is_docked)
        scene._game_loop_manager.render_explosions(surface)
        scene._input_coordinator.render_give_up(surface)
        self._render_homecoming_progress(surface)
        self._render_warning_banner(surface)
        self._render_aim_crosshair(surface)
        # Juice overlay — chromatic aberration when low HP, red flash on damage.
        # Drawn above the world, below the homecoming/console/reward topmost layer.
        self._render_damage_overlay(surface)
        self._render_haunting_corruption(surface)
        self._render_homecoming_sequence(surface)
        self._render_base_talent_console(surface)
        self._render_reward_selector(surface)
        scene._ui_manager.render_notification(surface)
        scene._render_haunting_foreground(surface)
        self._render_haunting_flicker(surface)

    # ------------------------------------------------------------------
    # Section helpers
    # ------------------------------------------------------------------

    def _render_boost_gauge(self, surface) -> None:
        scene = self._scene
        if scene._boost_gauge is None:
            return
        status = scene.player.get_boost_status()
        scene._boost_gauge.render(surface, status["current"], status["max"], status["active"], status)

    def _render_ammo_magazine(self, surface) -> None:
        scene = self._scene
        if not (scene._ammo_magazine and scene._mother_ship_integrator):
            return
        ms_data = scene._mother_ship_integrator.get_status_data()
        scene._ammo_magazine.render(
            surface,
            ammo_count=ms_data.get("ammo_count", 0.0),
            ammo_max=ms_data.get("ammo_max", 10.0),
            is_cooldown=ms_data.get("is_in_cooldown", False),
            is_docked=ms_data.get("is_docked", False),
            is_warning=ms_data.get("ammo_warning", False),
            is_present=ms_data.get("is_present", False),
            cooldown_remaining=ms_data.get("cooldown_remaining", 0.0),
            cooldown_reduction=ms_data.get("cooldown_reduction", 0.0),
        )

    def _render_mothership(self, surface) -> None:
        scene = self._scene
        if scene._mother_ship_integrator:
            scene._mother_ship_integrator.render(surface)

    def _render_boss_enrage(self, surface, is_docked: bool) -> None:
        scene = self._scene
        boss = scene.spawn_controller.boss if scene.spawn_controller else None
        if not is_docked:
            scene._boss_enrage_renderer.render(surface, boss)

    def _render_homecoming_progress(self, surface) -> None:
        scene = self._scene
        if scene._homecoming_ui and scene._homecoming_detector and scene._homecoming_detector.is_active():
            scene._homecoming_ui.render_progress(surface)

    def _render_warning_banner(self, surface) -> None:
        scene = self._scene
        if scene._warning_banner:
            scene._warning_banner.render(surface)

    def _render_aim_crosshair(self, surface) -> None:
        """Render the aim crosshair (moved from GameScene in Phase 5-ε)."""
        scene = self._scene
        if not scene.game_controller or not scene.game_controller.is_playing():
            return
        if scene.game_controller.state.is_paused:
            return
        if scene.reward_selector and scene.reward_selector.visible:
            return
        scene._aim_crosshair.render(surface, scene._aim_assist.get_aim_position())

    def _render_damage_overlay(self, surface) -> None:
        """Juice overlay: low-HP chromatic aberration + damage flash.

        Two stacked effects:
        1. **Low-HP chromatic aberration** (sustained): when health < 50%, blend
           horizontally offset world copies using additive blend. Intensity ramps
           from 0 (at 50% HP) to 1 (at 0% HP).
        2. **Damage flash** (transient): when ``state.damage_intensity > 0``,
           fill a red-tinted fullscreen surface with alpha = damage_intensity.

        Both are no-ops when the relevant state is 0.
        """
        import pygame  # local import keeps the module's import cost flat
        scene = self._scene
        state = scene.game_controller.state if scene.game_controller else None
        if state is None or not scene.player:
            return

        # Effect 1: low-HP chromatic aberration. Only when health < 50%.
        health_ratio = 1.0
        max_hp = getattr(scene.player, "max_health", 1) or 1
        health_ratio = max(0.0, min(1.0, scene.player.health / max_hp))
        if health_ratio < 0.5:
            # Map [0, 0.5] → [1, 0] — 0% HP = full aberration, 50% HP = none.
            intensity = 1.0 - (health_ratio * 2.0)
            offset_px = max(1, int(2 * intensity))  # 1px at 25% HP, 2px at 0%
            aberration, _flash = self._get_damage_overlays(surface.get_size(), pygame)
            self._damage_aberration_frame += 1

            # A horizontal split is the conventional chromatic-aberration cue.
            # Refreshing its full-screen composite every second frame keeps the
            # effect stable while avoiding four full-screen copies per render.
            if self._damage_aberration_frame == 1 or self._damage_aberration_frame % 2 == 0:
                aberration.fill((0, 0, 0, 0))
                aberration.blit(surface, (offset_px, 0), special_flags=pygame.BLEND_RGBA_ADD)
                aberration.blit(surface, (-offset_px, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(aberration, (0, 0))
        else:
            self._damage_aberration_frame = 0

        # Effect 2: damage flash. Red vignette that fades over ~30 frames.
        if state.damage_intensity > 0.05:
            _aberration, flash = self._get_damage_overlays(surface.get_size(), pygame)
            alpha = int(180 * state.damage_intensity)
            # Per-pixel alpha is substantially faster than Surface.set_alpha()
            # for a full-screen pygame blit, while retaining the same tint.
            flash.fill((220, 60, 50, alpha))
            surface.blit(flash, (0, 0))

    def _get_damage_overlays(self, size: tuple[int, int], pygame):
        """Return reusable full-screen surfaces for transient damage effects."""
        if self._damage_overlay_size != size:
            self._damage_overlay_size = size
            self._damage_aberration = pygame.Surface(size, pygame.SRCALPHA)
            self._damage_flash = pygame.Surface(size, pygame.SRCALPHA)
            self._damage_flash.fill((220, 60, 50))
            self._damage_aberration_frame = 0
        return self._damage_aberration, self._damage_flash

    def _render_haunting_corruption(self, surface) -> None:
        scene = self._scene
        if scene._haunting_renderer and not scene._should_suppress_haunting():
            scene._haunting_renderer.render_hud_corruption(surface)

    def _render_haunting_flicker(self, surface) -> None:
        scene = self._scene
        if scene._haunting_renderer and not scene._should_suppress_haunting():
            scene._haunting_renderer.render_transition_flicker(surface)

    def _render_homecoming_sequence(self, surface) -> None:
        scene = self._scene
        if scene._homecoming_ui and scene._homecoming_sequence:
            scene._homecoming_ui.render_sequence(surface, scene._homecoming_sequence, scene.player)

    def _render_base_talent_console(self, surface) -> None:
        scene = self._scene
        if not (scene._homecoming_base_pending and scene._base_talent_console and scene._talent_balance_manager):
            return
        mothership_status = scene._mother_ship_integrator.get_status_data() if scene._mother_ship_integrator else None
        scene._base_talent_console.render(
            surface,
            scene._talent_balance_manager,
            scene.reward_system,
            player=scene.player,
            game_controller=scene.game_controller,
            mothership_status=mothership_status,
            requisition_points=(scene.game_controller.state.requisition_points if scene.game_controller else 0),
            missions=scene._base_talent_console.get_missions() if scene._base_talent_console else None,
        )
        if scene._homecoming_coordinator:
            scene._homecoming_coordinator.sync_mission_progress(scene.game_controller, scene._survival_frames)

    def _render_reward_selector(self, surface) -> None:
        scene = self._scene
        if scene.reward_selector.visible:
            scene.reward_selector.render(surface)


__all__ = ["GameSceneRenderer"]
