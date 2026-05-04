"""Game loop orchestration — coordinates all per-frame update logic."""
from typing import Protocol, Callable, List
from ..constants import PlayerConstants
from ...config import get_screen_width, get_screen_height
from ..explosion_animation import ExplosionManager
from .game_controller import GameplayState

try:
    from airwar.core_bindings import batch_update_movements as rust_batch_move, RUST_AVAILABLE as _RUST_OK
    _HAS_BATCH_MOVE = _RUST_OK
except ImportError:
    _HAS_BATCH_MOVE = False
    rust_batch_move = None


class GameControllerProtocol(Protocol):
    """Protocol for game controller dependency injection."""
    @property
    def state(self): ...
    def update(self, player, has_regen: bool) -> None: ...
    def on_enemy_killed(self, score: int) -> None: ...
    def on_boss_killed(self, score: int) -> None: ...


class GameRendererProtocol(Protocol):
    """Protocol for game renderer dependency injection."""
    def update_death_animation(self) -> None: ...


class SpawnControllerProtocol(Protocol):
    """Protocol for spawn controller dependency injection."""
    def update(self, score: int, slow_factor: float) -> bool: ...
    def balance_for_player_dps(self, player_dps: float) -> None: ...
    def spawn_boss(self, cycle_count: int, bullet_damage: float, player_dps: float = None): ...
    def cleanup(self) -> None: ...
    @property
    def enemies(self) -> List: ...
    @property
    def boss(self): ...
    def show_notification(self, message: str) -> None: ...


class RewardSystemProtocol(Protocol):
    """Protocol for reward system dependency injection."""
    @property
    def slow_factor(self) -> float: ...
    def apply_lifesteal(self, player, score: int) -> None: ...


class BulletManagerProtocol(Protocol):
    """Protocol for bullet manager dependency injection."""
    def update_all(self) -> None: ...
    def cleanup(self) -> None: ...
    def clear_enemy_bullets(self, include_clear_immune: bool = False) -> None: ...


class BossManagerProtocol(Protocol):
    """Protocol for boss manager dependency injection."""
    def update(self, player) -> None: ...
    def on_boss_hit(self, score: int) -> None: ...
    @property
    def boss(self): ...


class PlayerProtocol(Protocol):
    """Protocol for player dependency injection."""
    def update(self) -> None: ...
    def auto_fire(self) -> None: ...
    def cleanup_inactive_bullets(self) -> None: ...
    bullet_damage: float
    fire_interval: int
    controls_locked: bool
    def get_weapon_status(self) -> dict: ...
    @property
    def active(self) -> bool: ...


class CollisionControllerProtocol(Protocol):
    """Protocol for collision controller dependency injection."""
    def check_all_collisions(self, **kwargs) -> None: ...


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
    ):
        self._game_controller = game_controller
        self._game_renderer = game_renderer
        self._spawn_controller = spawn_controller
        self._reward_system = reward_system
        self._bullet_manager = bullet_manager
        self._boss_manager = boss_manager
        self._collision_controller = collision_controller

        self._init_explosion_system()

    def _init_explosion_system(self) -> None:
        """Initialize explosion animation system"""
        self._explosion_manager = ExplosionManager()
        self._collision_controller.set_explosion_callback(
            self._on_explosion
        )

    def _on_explosion(self, x: float, y: float, radius: int) -> None:
        """Explosion callback handler"""
        self._explosion_manager.trigger(x, y, radius)

    def update_entrance(self, player: PlayerProtocol) -> bool:
        state = self._game_controller.state
        state.entrance_timer += 1
        progress = state.entrance_timer / state.entrance_duration

        if progress >= 1.0:
            state.entrance_animation = False
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

    def update_game(self, player: PlayerProtocol) -> bool:
        try:
            self._update_core(player)
            return True
        except Exception as e:
            import logging
            logging.error(f"Game update error: {e}", exc_info=True)
            self._game_controller.show_notification("游戏错误 - 请查看日志")
            self._game_controller.state.running = False
            return False

    def _update_core(self, player: PlayerProtocol) -> None:
        has_regen = 'Regeneration' in self._reward_system.unlocked_buffs
        self._game_controller.update(player, has_regen)

        if self._game_controller.state.gameplay_state == GameplayState.DYING:
            self._game_renderer.update_death_animation()
            self._explosion_manager.update()
            return

        self._game_renderer.update_death_animation()
        self._explosion_manager.update()
        restore_controls_locked = player.controls_locked
        if self._should_lock_player_for_boss_enrage():
            player.controls_locked = True
        player.update()
        player.auto_fire()
        player.controls_locked = restore_controls_locked

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

    def _update_enemy_spawning(self, player: PlayerProtocol) -> None:
        player_pos = (player.rect.centerx, player.rect.centery)
        player_dps = self._estimate_player_dps(player)
        self._spawn_controller.balance_for_player_dps(player_dps)
        spawn_needed = self._spawn_controller.update(
            self._game_controller.state.score,
            self._reward_system.slow_factor,
            player_pos
        )

        if spawn_needed:
            boss = self._spawn_controller.spawn_boss(
                self._game_controller.state.boss_kill_count,
                player.bullet_damage,
                player_dps
            )
            self._game_controller.show_notification(
                f"! BOSS 来袭 ({int(boss.data.escape_time/60)}秒) !"
            )

    def _estimate_player_dps(self, player: PlayerProtocol) -> float:
        weapon_status = player.get_weapon_status() if hasattr(player, "get_weapon_status") else {}
        bullets_per_shot = 6 if weapon_status.get("spread") else 2
        fire_interval = max(1, int(getattr(player, "fire_interval", PlayerConstants.FIRE_COOLDOWN)))
        return float(getattr(player, "bullet_damage", PlayerConstants.BULLET_DAMAGE)) * bullets_per_shot / fire_interval * 60

    def _update_entities(self) -> None:
        enemies = self._spawn_controller.enemies
        if not enemies:
            return

        # Batch Rust movement — only for enemies in 'active' state (not entering/exiting)
        if _HAS_BATCH_MOVE:
            base_list = []
            extra_list = []
            batch_indices = []
            for i, enemy in enumerate(enemies):
                if enemy.is_ready_for_batch_movement():
                    try:
                        base, extra = enemy.get_rust_batch_params()
                    except (ValueError, TypeError):
                        continue
                    if base is not None:
                        base_list.append(base)
                        extra_list.append(extra)
                        batch_indices.append(i)
            if base_list:
                results = rust_batch_move(base_list, extra_list)
                for j, (new_x, new_y, new_timer) in enumerate(results):
                    idx = batch_indices[j]
                    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))

        for enemy in enemies:
            enemy.update(self._spawn_controller.enemies, self._reward_system.slow_factor)

    def check_collisions(
        self,
        player: PlayerProtocol,
        enemy_bullets: List,
        on_player_hit: Callable,
    ) -> None:
        try:
            self._collision_controller.check_all_collisions(
                player=player,
                enemies=self._spawn_controller.enemies,
                boss=self._spawn_controller.boss,
                enemy_bullets=enemy_bullets,
                reward_system=self._reward_system,
                explosive_level=self._reward_system.explosive_level,
                piercing_level=self._reward_system.piercing_level,
                player_invincible=self._game_controller.state.player_invincible,
                score_multiplier=self._game_controller.state.score_multiplier,
                on_enemy_killed=lambda score: self._game_controller.on_enemy_killed(score),
                on_boss_killed=lambda score: (
                    self._boss_manager.on_boss_killed(),
                    self._game_controller.on_boss_killed(score),
                ),
                on_boss_hit=lambda score: self._boss_manager.on_boss_hit(score),
                on_player_hit=on_player_hit,
                on_lifesteal=lambda player, score: self._reward_system.apply_lifesteal(player, score),
                on_clear_bullets=lambda: self._bullet_manager.clear_enemy_bullets(),
            )
        except Exception as e:
            import logging
            logging.critical(f"Collision detection error: {e}", exc_info=True)
            self._game_controller.state.running = False

    def is_entrance_playing(self) -> bool:
        return self._game_controller.state.entrance_animation

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
