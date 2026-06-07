"""Game loop orchestration — coordinates all per-frame update logic."""

import logging
import struct
from collections.abc import Callable

from airwar.config import get_screen_height, get_screen_width
from airwar.core_bindings import batch_update_movements, batch_update_movements_buf

from ..constants import PlayerConstants
from ..explosion_animation import ExplosionManager
from ..protocols import (
    BossManagerProtocol,
    BulletManagerProtocol,
    CollisionControllerProtocol,
    GameControllerProtocol,
    GameRendererProtocol,
    PlayerProtocol,
    RewardSystemProtocol,
    SpawnControllerProtocol,
)
from ..systems.lock_manager import LockLayer, LockRequest
from .game_controller import GameplayState

logger = logging.getLogger(__name__)


class GameLoopManager:
    """Game loop manager — orchestrates all per-frame update logic.

    Coordinates the update order of all managers and systems each frame:
    input → player update → spawn controller → boss → collision → UI.

    Attributes:
        _controllers: Ordered list of per-frame update callables.
    """

    def __init__(
        self,
        game_controller: GameControllerProtocol,
        game_renderer: GameRendererProtocol,
        spawn_controller: SpawnControllerProtocol,
        reward_system: RewardSystemProtocol,
        bullet_manager: BulletManagerProtocol,
        boss_manager: BossManagerProtocol,
        collision_controller: CollisionControllerProtocol,
        lock_manager=None,
    ):
        self._game_controller = game_controller
        self._game_renderer = game_renderer
        self._spawn_controller = spawn_controller
        self._reward_system = reward_system
        self._bullet_manager = bullet_manager
        self._boss_manager = boss_manager
        self._collision_controller = collision_controller
        self._lock_manager = lock_manager

        self._init_explosion_system()

    def _init_explosion_system(self) -> None:
        """Initialize explosion animation system"""
        self._explosion_manager = ExplosionManager()
        self._collision_controller.set_explosion_callback(self._on_explosion)

    def _on_explosion(self, x: float, y: float, radius: int) -> None:
        """Explosion callback handler"""
        self._explosion_manager.trigger(x, y, radius)

    def _on_boss_destroyed(self) -> None:
        boss = self._spawn_controller.boss
        if boss:
            self._explosion_manager.trigger_boss_death(
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
            )
        self._boss_manager.on_boss_killed()

    def _handle_boss_killed(self, score: int) -> None:
        """Handle boss killed event with proper error handling.

        Args:
            score: Score gained from killing the boss.
        """
        try:
            self._on_boss_destroyed()
        except Exception:
            logger.exception("Error in _on_boss_destroyed")
        self._game_controller.on_boss_killed(score)

    def update_entrance(self, player: PlayerProtocol) -> bool:
        state = self._game_controller.state
        state.entrance_timer += 1
        progress = state.entrance_timer / state.entrance_duration

        if progress >= 1.0:
            state.is_entrance_playing = False
            player.rect.y = get_screen_height() - PlayerConstants.SCREEN_BOTTOM_OFFSET
            return False
        else:
            self._animate_entrance(player, progress)
            return True

    def _animate_entrance(self, player: PlayerProtocol, progress: float) -> None:
        screen_width = get_screen_width()
        target_y = get_screen_height() - PlayerConstants.SCREEN_BOTTOM_OFFSET
        start_y = PlayerConstants.INITIAL_Y
        player.rect.y = int(start_y + (target_y - start_y) * progress)
        player.rect.x = screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET

    def update_game(self, player: PlayerProtocol) -> None:
        self._update_core(player)

    def _update_core(self, player: PlayerProtocol) -> None:
        has_regen = "Regeneration" in self._reward_system.unlocked_buffs
        self._game_controller.update(player, has_regen)
        self._refresh_locks()

        if self._game_controller.state.gameplay_state == GameplayState.DYING:
            self._game_renderer.update_death_animation()
            self._explosion_manager.update()
            return

        self._game_renderer.update_death_animation()
        self._explosion_manager.update()
        if self._lock_manager:
            self._sync_boss_enrage_lock()
            player.update()
            player.auto_fire()
        else:
            restore_controls_locked = player.is_controls_locked
            if self._should_lock_player_for_boss_enrage():
                player.is_controls_locked = True
            player.update()
            player.auto_fire()
            player.is_controls_locked = restore_controls_locked

        self._bullet_manager.update_all()
        self._update_enemy_spawning(player)
        self._update_entities()

        if self._spawn_controller.boss:
            self._boss_manager.update(player)

        if not player.active:
            self._game_controller.state.running = False

    def _should_lock_player_for_boss_enrage(self) -> bool:
        boss = self._boss_manager.boss
        return bool(boss and getattr(boss, "should_lock_player_movement", lambda: False)())

    def _sync_boss_enrage_lock(self) -> None:
        if not self._lock_manager:
            return
        boss = self._boss_manager.boss
        if not boss:
            self._lock_manager.release(LockLayer.BOSS_ENRAGE)
            return
        if self._should_lock_player_for_boss_enrage():
            in_transition = getattr(boss, "_enrage_transition_timer", 0) > 0
            self._lock_manager.acquire(
                LockLayer.BOSS_ENRAGE,
                LockRequest(
                    lock_controls=True,
                    invincible=in_transition,
                ),
            )
        else:
            self._lock_manager.release(LockLayer.BOSS_ENRAGE)

    def _refresh_locks(self) -> None:
        if self._lock_manager and self._lock_manager.has_locks():
            self._lock_manager.refresh()

    def _update_enemy_spawning(self, player: PlayerProtocol) -> None:
        player_pos = (player.rect.centerx, player.rect.centery)
        player_dps = self._estimate_player_dps(player)
        self._spawn_controller.balance_for_player_dps(player_dps)
        spawn_needed = self._spawn_controller.update(
            self._game_controller.state.score, self._reward_system.slow_factor, player_pos
        )

        if spawn_needed:
            boss = self._spawn_controller.spawn_boss(
                self._game_controller.state.boss_kill_count, player.bullet_damage, player_dps
            )
            self._game_controller.show_notification(f"! BOSS 来袭 ({int(boss.data.escape_time / 60)}秒) !")

    def _estimate_player_dps(self, player: PlayerProtocol) -> float:
        weapon_status = player.get_weapon_status() if hasattr(player, "get_weapon_status") else {}
        bullets_per_shot = 6 if weapon_status.get("spread") else 2
        fire_interval = max(1, int(getattr(player, "fire_interval", PlayerConstants.FIRE_COOLDOWN)))
        damage = float(getattr(player, "bullet_damage", PlayerConstants.BULLET_DAMAGE))
        return damage * bullets_per_shot / fire_interval * 60

    # Binary buffer formats for movement FFI.
    # base: B(move_type) + 3*pad + 11*f32 = 48 bytes. Must match Rust
    # `BASE_BUF_STRIDE = 48` in `airwar_core/src/movement.rs`. The
    # previous fmt "<Bxxxfff fffffff" was 9 floats (44 bytes / 11
    # fields) and crashed the FFI because
    # `Enemy.get_rust_batch_params` returns a 12-element base tuple.
    # Fixed 2026-06-07.
    _MOVEMENT_BASE_FMT = "<Bxxx fffffffffff"
    _MOVEMENT_BASE_SIZE = struct.calcsize(_MOVEMENT_BASE_FMT)  # 48
    # extra: 7*f32 + i32 = 32 bytes
    _MOVEMENT_EXTRA_FMT = "<fffffffI"
    _MOVEMENT_EXTRA_SIZE = struct.calcsize(_MOVEMENT_EXTRA_FMT)  # 32

    def _update_entities(self) -> None:
        enemies = self._spawn_controller.enemies
        if not enemies:
            return

        # Batch Rust movement — only for enemies in 'active' state (not entering/exiting)
        if batch_update_movements_buf is not None:
            batch_indices = []
            base_buf_parts = []
            extra_buf_parts = []

            for i, enemy in enumerate(enemies):
                if enemy.is_ready_for_batch_movement():
                    try:
                        base, extra = enemy.get_rust_batch_params()
                    except (ValueError, TypeError):
                        logger.warning(
                            "Skipping enemy with invalid Rust batch movement params: %r",
                            enemy,
                            exc_info=True,
                        )
                        continue
                    if base is not None and extra is not None:
                        # Pack base: (move_type:u8, pad, timer, active_x, active_y,
                        #   move_range_x, move_range_y, offset, amplitude, frequency,
                        #   speed, direction, zigzag_interval)
                        base_buf_parts.append(
                            struct.pack(
                                self._MOVEMENT_BASE_FMT,
                                base[0],
                                base[1],
                                base[2],
                                base[3],
                                base[4],
                                base[5],
                                base[6],
                                base[7],
                                base[8],
                                base[9],
                                base[10],
                                base[11],
                            )
                        )
                        # Pack extra: (spiral_radius, current_x, current_y,
                        #   noise_scale_x, noise_scale_y, noise_amplitude_x,
                        #   noise_amplitude_y, noise_seed)
                        extra_buf_parts.append(
                            struct.pack(
                                self._MOVEMENT_EXTRA_FMT,
                                extra[0],
                                extra[1],
                                extra[2],
                                extra[3],
                                extra[4],
                                extra[5],
                                extra[6],
                                extra[7],
                            )
                        )
                        batch_indices.append(i)
                    elif base is None and extra is None:
                        # enemy not ready for batch — fine
                        continue
                    else:
                        logger.error(
                            "get_rust_batch_params returned mismatched pair: base=%r extra=%r for %r",
                            base,
                            extra,
                            enemy,
                        )
                        continue

            if base_buf_parts:
                base_buf = b"".join(base_buf_parts)
                extra_buf = b"".join(extra_buf_parts)
                results = batch_update_movements_buf(base_buf, extra_buf)
                for j, (new_x, new_y, new_timer) in enumerate(results):
                    idx = batch_indices[j]
                    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))
        elif batch_update_movements is not None:
            # Fallback: tuple-based batch movement
            base_list = []
            extra_list = []
            batch_indices = []
            for i, enemy in enumerate(enemies):
                if enemy.is_ready_for_batch_movement():
                    try:
                        base, extra = enemy.get_rust_batch_params()
                    except (ValueError, TypeError):
                        continue
                    if base is not None and extra is not None:
                        base_list.append(base)
                        extra_list.append(extra)
                        batch_indices.append(i)
                    elif base is None and extra is None:
                        # enemy not ready for batch — fine
                        continue
                    else:
                        logger.error(
                            "get_rust_batch_params returned mismatched pair: base=%r extra=%r for %r",
                            base,
                            extra,
                            enemy,
                        )
                        continue
            if base_list:
                results = batch_update_movements(base_list, extra_list)
                for j, (new_x, new_y, new_timer) in enumerate(results):
                    idx = batch_indices[j]
                    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))

        for enemy in enemies:
            enemy.update(self._spawn_controller.enemies, self._reward_system.slow_factor)

    def check_collisions(
        self,
        player: PlayerProtocol,
        enemy_bullets: list,
        on_player_hit: Callable,
    ) -> None:
        self._collision_controller.check_all_collisions(
            player=player,
            enemies=self._spawn_controller.enemies,
            boss=self._spawn_controller.boss,
            enemy_bullets=enemy_bullets,
            reward_system=self._reward_system,
            explosive_level=self._reward_system.explosive_level,
            piercing_level=self._reward_system.piercing_level,
            player_invincible=self._game_controller.state.is_player_invincible,
            score_multiplier=self._game_controller.state.score_multiplier,
            on_enemy_killed=self._game_controller.on_enemy_killed,
            on_boss_killed=self._handle_boss_killed,
            on_boss_hit=self._boss_manager.on_boss_hit,
            on_player_hit=on_player_hit,
            on_lifesteal=self._reward_system.apply_lifesteal,
        )

    def is_entrance_playing(self) -> bool:
        return self._game_controller.state.is_entrance_playing

    def is_game_running(self) -> bool:
        return self._game_controller.state.running

    def render_explosions(self, surface) -> None:
        """Render all active explosion effects

        Args:
            surface: PyGame rendering surface
        """
        self._explosion_manager.render(surface)

    def get_explosion_stats(self) -> dict:
        """Get explosion system statistics

        Returns:
            dict: Statistics about the explosion system
        """
        return self._explosion_manager.get_stats()

    def trigger_boss_death_explosion(self, centerx: int, centery: int, width: int, height: int) -> None:
        """Trigger a boss death explosion at the given position."""
        self._explosion_manager.trigger_boss_death(centerx, centery, width, height)
