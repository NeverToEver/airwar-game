"""GameSceneUpdater — owns GameScene's per-frame update body.

Phase 5-ε: extracted from GameScene to slim the facade to ≤450 lines.
Mirrors the Boss / Homecoming / Mothership split pattern: facade +
sub-component with constructor injection of ``self`` (typed as ``object``
to avoid circular imports). The 26 IGameSceneProtocol forwarders and
the 8 properties stay on the facade.

The 15 PIPELINE_ORDER steps are wired through the existing
``airwar.scenes.update_pipeline.UpdatePipeline`` skeleton (Phase 3 F05).
Short-circuit semantics match the original inlined body: ``homecoming``,
``entrance_animation``, ``dying_animation``, and ``pause_check`` each
return ``False`` to claim the frame; ``reward_selector`` is registered
in SHORT_CIRCUIT_STEPS but does not short-circuit (preserves the
pre-extraction behavior where the visible reward selector still allows
the early homecoming / aim blocks to run before the pause check at the
``pause_check`` step claims the frame).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.game.constants import GAME_CONSTANTS
from airwar.game.frame_context import FrameContext, SimulationStep
from airwar.game.managers.game_controller import GameplayState
from airwar.game.mother_ship.event_bus import EVENT_UNDOCK_REQUESTED
from airwar.game.systems.lock_manager import LockLayer, LockRequest

from .update_pipeline import UpdatePipeline

if TYPE_CHECKING:
    from .game_scene_protocols import GameSceneProtocol


class GameSceneUpdater:
    """Per-frame update body extracted from GameScene (Phase 5-ε).

    Owns the 15 PIPELINE_ORDER steps + 7 migrated helpers + 4 state attrs.
    Reads scene state via ``self._scene.<attr>``; writes cross-step state
    via instance attrs on ``self`` (e.g. ``_docked``).
    """

    # Mirrored from GameScene so the updater owns the persistence timing values.
    BULLET_CLEAR_RADIUS = GAME_CONSTANTS.PERSISTENCE.BULLET_CLEAR_RADIUS
    BULLET_CLEAR_DEDUP_FRAMES = GAME_CONSTANTS.PERSISTENCE.BULLET_CLEAR_DEDUP_FRAMES

    def __init__(self, scene: GameSceneProtocol) -> None:
        self._scene = scene
        # Cross-step handoff: ``mothership_integrator`` step writes this;
        # ``core_logic`` step reads it for the docking position lock.
        self._docked = False
        self._phase_dash_invincibility_active = False
        self._survival_frames = 0
        self._last_bullet_clear_frame = GAME_CONSTANTS.GAMEPLAY.bullet_clear_dedup_initial_frame()
        self._auto_save_elapsed = 0.0
        self._frame = SimulationStep(FrameContext.FIXED_DELTA_SECONDS, 0.0)
        self._pipeline = UpdatePipeline()
        self._wire_steps()

    def run(self, frame: FrameContext | None = None) -> None:
        """Execute the 15 PIPELINE_ORDER steps in canonical order with short-circuit."""
        scene = self._scene
        if not getattr(scene, "_entered", False) or scene.game_controller is None or scene.player is None:
            return
        context = frame or FrameContext(
            FrameContext.FIXED_DELTA_SECONDS,
            FrameContext.FIXED_DELTA_SECONDS,
            1,
        )
        for step in context.steps():
            self._frame = step
            self._pipeline.execute()

    def reset_state(self) -> None:
        """Reset per-frame state for a fresh ``enter()`` on the owning scene.

        Called by ``GameScene.enter()`` so each scene entry starts from a
        known baseline (auto-save timer = 0, survival frames = 0, etc.).
        """
        self._phase_dash_invincibility_active = False
        self._survival_frames = 0
        self._last_bullet_clear_frame = GAME_CONSTANTS.GAMEPLAY.bullet_clear_dedup_initial_frame()
        self._auto_save_elapsed = 0.0
        self._docked = False
        self._frame = SimulationStep(FrameContext.FIXED_DELTA_SECONDS, 0.0)

    # ---- Step registration ----

    def _wire_steps(self) -> None:
        """Bind each PIPELINE_ORDER step to a private method on this updater."""
        self._pipeline.add_step("tick_hit_stop", self._step_tick_hit_stop)
        self._pipeline.add_step("reward_selector", self._step_reward_selector)
        self._pipeline.add_step("aim_assist", self._step_aim_assist)
        self._pipeline.add_step("homecoming", self._step_homecoming)
        self._pipeline.add_step("warning_banner", self._step_warning_banner)
        self._pipeline.add_step("entrance_animation", self._step_entrance_animation)
        self._pipeline.add_step("dying_animation", self._step_dying_animation)
        self._pipeline.add_step("pause_check", self._step_pause_check)
        self._pipeline.add_step("mothership_integrator", self._step_mothership_integrator)
        self._pipeline.add_step("give_up_detector", self._step_give_up_detector)
        self._pipeline.add_step("core_logic", self._step_core_logic)
        self._pipeline.add_step("phase_dash_sync", self._step_phase_dash_sync)
        self._pipeline.add_step("collision", self._step_collision)
        self._pipeline.add_step("post_collision_cleanup", self._step_post_collision_cleanup)
        self._pipeline.add_step("milestone_check", self._step_milestone_check)
        self._pipeline.add_step("auto_save", self._step_auto_save)

    # ---- Step implementations ----

    def _step_tick_hit_stop(self) -> None:
        """Step 0: decrement hit_stop_timer every frame.

        Bug fix (Phase 7, 2026-06-10): ``hit_stop_timer`` is set to 4 by
        ``GameController.on_player_hit`` (~67ms Smash-Bros-style hit
        freeze) and previously only decremented in
        ``GameController.update()`` -- which is called from
        ``_step_core_logic``, AFTER ``_step_pause_check`` short-circuits
        when ``hit_stop_timer > 0``. The result was a deadlock: a single
        player hit would freeze the game forever (boss_spawn_timer
        stuck, score frozen, no further enemy spawn). Moving the
        decrement to the very first pipeline step ensures the timer
        ticks down regardless of which subsequent step claims the frame.
        """
        state = getattr(self._scene, "game_controller", None)
        if state is None:
            return
        state = getattr(state, "state", None)
        if state is None:
            return
        timer = getattr(state, "hit_stop_timer", 0)
        if timer > 0:
            state.hit_stop_timer = timer - 1

    def _step_reward_selector(self) -> bool | None:
        """Step 1: update the reward selector UI.

        Returns ``None`` (no short-circuit) to preserve the original
        behavior where subsequent steps (homecoming, aim assist) still
        run when the selector is visible — the short-circuit on
        ``reward_selector.visible`` happens later at the ``pause_check``
        step (L309-310 of the pre-extraction body).
        """
        self._scene.reward_selector.update()
        return None

    def _step_aim_assist(self) -> None:
        """Step 2: aim assist + integrated HUD + homecoming dispatcher update.

        Per the pre-extraction body (L276-281 + L283-288), this step
        bundles the early homecoming coordinator update, the aim
        crosshair system, the aim target sync, the integrated HUD scroll
        / health tank updates, and the homecoming dispatcher update. The
        order matches the original: ``update_base`` → ``aim_assist`` →
        ``_sync_player_aim_target`` → ``_aim_crosshair`` →
        ``_update_homecoming`` → ``integrated_hud``.
        """
        scene = self._scene
        if scene._homecoming_coordinator:
            scene._homecoming_coordinator.update_base(
                scene.game_controller, scene.notification_manager
            )
        scene._aim_assist.update(scene.spawn_controller, scene._get_logical_mouse_pos())
        scene._sync_player_aim_target()
        scene._aim_crosshair.update()
        scene._update_homecoming(self._frame.delta_seconds)

        if scene.game_renderer and scene.game_renderer.integrated_hud:
            unlocked_buffs = getattr(scene.reward_system, "unlocked_buffs", [])
            scene.game_renderer.integrated_hud.update_scroll(len(unlocked_buffs))
            if scene.player:
                scene.game_renderer.integrated_hud.update_health_tank(
                    scene.player.health, scene.player.max_health
                )
            scene.game_renderer.integrated_hud.update()

    def _step_homecoming(self) -> bool | None:
        """Step 3: short-circuit if homecoming is active (L290-291)."""
        if self._scene._is_homecoming_active():
            return False
        return None

    def _step_warning_banner(self) -> None:
        """Step 4: warning banner scroll (always runs, even during dying)."""
        if self._scene._warning_banner:
            self._scene._warning_banner.update()

    def _step_entrance_animation(self) -> bool | None:
        """Step 5: short-circuit during entrance animation (L297-301)."""
        scene = self._scene
        if scene._game_loop_manager.is_entrance_playing():
            scene._game_loop_manager.update_entrance(scene.player)
            if scene._mother_ship_integrator:
                scene._mother_ship_integrator.update(self._frame.delta_seconds, self._frame.elapsed_seconds)
            return False
        return None

    def _step_dying_animation(self) -> bool | None:
        """Step 6: short-circuit during dying animation (L303-307)."""
        scene = self._scene
        gc = scene.game_controller
        if gc is None:
            return None
        is_dying = gc.state.gameplay_state == GameplayState.DYING
        if is_dying:
            scene._game_loop_manager.update_game(scene.player)
            return False
        return None

    def _step_pause_check(self) -> bool | None:
        """Step 7: short-circuit when paused, reward selector visible, or hit-stop active (L309-310).

        The original L309-310 checks ``is_paused OR reward_selector.visible``.
        Hit-stop piggybacks on the same short-circuit: when ``hit_stop_timer > 0``
        the gameplay tick is skipped for ~4 frames (~67ms at 60fps), matching
        the canonical "Smash Bros"-style hit-pause length.
        """
        scene = self._scene
        gc = scene.game_controller
        if gc is None:
            return None
        if gc.state.is_paused or scene.reward_selector.visible:
            return False
        # Hit-stop: freeze gameplay ticks (but UI and render still run).
        hit_stop = getattr(gc.state, "hit_stop_timer", 0)
        if hit_stop > 0:
            return False
        return None

    def _step_mothership_integrator(self) -> None:
        """Step 8: mothership integrator update + ammo warning + docked handoff (L312-317).

        Sets ``self._docked`` so the next ``core_logic`` step can apply
        the docking position lock without re-querying the integrator.
        """
        scene = self._scene
        self._docked = False
        if scene._mother_ship_integrator:
            scene._mother_ship_integrator.update(self._frame.delta_seconds, self._frame.elapsed_seconds)
            self._docked = scene._mother_ship_integrator.is_docked()
        self._update_mothership_ammo_warning()

    def _step_give_up_detector(self) -> None:
        """Step 9: give-up input detector (L319)."""
        self._scene._input_coordinator.update_give_up(self._frame.delta_seconds)

    def _step_core_logic(self) -> None:
        """Step 10: game loop + docking position lock (L320-326).

        Reads ``self._docked`` from the prior ``mothership_integrator``
        step; writes ``player.rect.x/y`` when docked to lock the player
        to the mothership docking bay. The docked flag is pushed onto
        the boss BEFORE ``update_game`` runs so the enrage trigger
        skips its screen-center grab while docking owns the player
        position — the two position writers can no longer fight
        within the same frame.
        """
        scene = self._scene
        boss = scene.spawn_controller.boss
        if boss is not None:
            boss.player_position_locked = self._docked
        scene._game_loop_manager.update_game(scene.player)
        if self._docked:
            dock_pos = scene._mother_ship_integrator.get_docking_position()
            scene.player.rect.x = dock_pos[0] - scene.player.rect.width // 2
            scene.player.rect.y = dock_pos[1] - scene.player.rect.height // 2
            if hasattr(scene.player, "sync_hitbox"):
                scene.player.sync_hitbox()

    def _step_phase_dash_sync(self) -> None:
        """Step 11: phase dash invincibility sync (L328)."""
        self._sync_player_phase_dash_invincibility()

    def _step_collision(self) -> None:
        """Step 12: collision detection (L330-334)."""
        scene = self._scene
        scene._game_loop_manager.check_collisions(
            scene.player,
            scene.spawn_controller.enemy_bullets,
            self._on_player_damaged,
        )

    def _step_post_collision_cleanup(self) -> None:
        """Step 13: post-collision cleanup (L337-339)."""
        scene = self._scene
        scene.spawn_controller.cleanup()
        scene._bullet_manager.cleanup()
        scene.player.cleanup_inactive_bullets()

    def _step_milestone_check(self) -> None:
        """Step 14: milestone reward check (L341)."""
        self._scene._milestone_manager.check_and_trigger(self._scene.player)

    def _step_auto_save(self) -> None:
        """Step 15: side effects — survival counter, haunting effect, auto-save (L343-348).

        ``_update_haunting_effect`` is not a named PIPELINE_ORDER step
        (per the plan), so it lives here in the trailing side-effects
        block alongside the auto-save timer bookkeeping. This matches
        the pre-extraction order: ``survival_frames`` → ``haunting`` →
        ``auto_save_timer` → ``juice.update()``.
        """
        scene = self._scene
        self._survival_frames += 1
        self._update_haunting_effect()
        # Juice controller decays trauma each frame, so its offset naturally
        # returns to (0, 0) over ~13 frames.
        juice = getattr(scene, "_juice_controller", None)
        if juice is not None:
            juice.update()
        self._auto_save_elapsed += self._frame.delta_seconds
        if self._auto_save_elapsed >= scene.AUTO_SAVE_INTERVAL_SECONDS:
            self._auto_save_elapsed = 0.0
            self._try_auto_save()

    # ---- Migrated helpers (verbatim from GameScene) ----

    def _update_haunting_effect(self) -> None:
        scene = self._scene
        if not scene._haunting_renderer or not scene.spawn_controller:
            return
        enemy_pressure = len(scene.spawn_controller.enemies)
        if scene.spawn_controller.boss:
            enemy_pressure += 3
        if scene.spawn_controller.enemy_bullets:
            enemy_pressure += min(8, len(scene.spawn_controller.enemy_bullets) // 6)
        scene._haunting_renderer.update(enemy_pressure)

    def _try_auto_save(self) -> None:
        """Periodic auto-save while game is running normally."""
        scene = self._scene
        if not scene._mother_ship_integrator:
            return
        if scene._mother_ship_integrator.is_docked():
            return
        if not scene.game_controller or not scene.game_controller.is_playing():
            return
        scene.save_snapshot(force_outside_mothership=True)

    def _sync_player_phase_dash_invincibility(self) -> None:
        scene = self._scene
        if not scene.game_controller or not scene.player:
            return

        scene._sync_lock_manager_targets()
        if scene.player.is_phase_dash_invincible():
            self._phase_dash_invincibility_active = True
            scene._lock_manager.acquire(
                LockLayer.PHASE_DASH,
                LockRequest(invincible=True, is_silent_invincible=True, invincibility_duration=2),
            )
            return

        if not self._phase_dash_invincibility_active:
            return

        self._phase_dash_invincibility_active = False
        scene._lock_manager.release(LockLayer.PHASE_DASH)

    def _update_mothership_ammo_warning(self) -> None:
        """Check ammo level and activate warning banner when critically low."""
        scene = self._scene
        if not scene._mother_ship_integrator or not scene._warning_banner:
            return

        status = scene._mother_ship_integrator.get_status_data()
        if not status.get("ammo_warning", False):
            return

        if scene._warning_banner.is_active:
            return

        def trigger_undock() -> None:
            bus = scene.event_bus
            if bus is None:
                raise RuntimeError(
                    "F02 D5: warning_banner.on_complete requires the EventBus "
                    "to be wired (publishes EVENT_UNDOCK_REQUESTED)."
                )
            bus.publish(EVENT_UNDOCK_REQUESTED)

        scene._warning_banner.activate(on_complete=trigger_undock)

    def _on_player_damaged(self, damage: int, player) -> None:
        """Handle player hit: apply damage, clear nearby enemy bullets, trigger juice."""
        scene = self._scene
        gc = scene.game_controller
        if gc is None:
            return
        gc.on_player_hit(damage, player)
        self._clear_nearby_enemy_bullets(player)
        # Juice: screen shake + 4-frame hit-stop.
        juice = getattr(scene, "_juice_controller", None)
        if juice is not None:
            juice.add_trauma(0.4)

    def _clear_nearby_enemy_bullets(self, player) -> None:
        """Clear enemy bullets within BULLET_CLEAR_RADIUS of the player after being hit."""
        scene = self._scene
        if not scene.spawn_controller:
            return
        if self._survival_frames - self._last_bullet_clear_frame < self.BULLET_CLEAR_DEDUP_FRAMES:
            return
        self._last_bullet_clear_frame = self._survival_frames
        px = player.rect.centerx
        py = player.rect.centery
        r2 = self.BULLET_CLEAR_RADIUS * self.BULLET_CLEAR_RADIUS
        for bullet in scene.spawn_controller.enemy_bullets:
            if not bullet.active:
                continue
            dx = bullet.rect.centerx - px
            dy = bullet.rect.centery - py
            if dx * dx + dy * dy <= r2:
                bullet.active = False

    def _on_give_up_complete(self) -> None:
        gc = self._scene.game_controller
        if gc is None:
            return
        gc.on_player_hit(
            GAME_CONSTANTS.DAMAGE.INSTANT_KILL, self._scene.player
        )


__all__ = ["GameSceneUpdater"]
