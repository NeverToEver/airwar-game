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
        scene._render_aim_crosshair(surface)
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
