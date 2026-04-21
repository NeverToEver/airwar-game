from typing import Protocol, Callable, List
from airwar.game.constants import PlayerConstants
from airwar.config import get_screen_width, get_screen_height


class GameControllerProtocol(Protocol):
    @property
    def state(self): ...
    def update(self, player, has_regen: bool) -> None: ...
    def on_enemy_killed(self, score: int) -> None: ...
    def on_boss_killed(self, score: int) -> None: ...


class GameRendererProtocol(Protocol):
    def update_death_animation(self) -> None: ...


class SpawnControllerProtocol(Protocol):
    def update(self, score: int, slow_factor: float) -> bool: ...
    def spawn_boss(self, cycle_count: int, bullet_damage: float): ...
    def cleanup(self) -> None: ...
    @property
    def enemies(self) -> List: ...
    @property
    def boss(self): ...
    def show_notification(self, message: str) -> None: ...


class RewardSystemProtocol(Protocol):
    @property
    def slow_factor(self) -> float: ...
    @property
    def base_bullet_damage(self) -> float: ...
    def apply_lifesteal(self, player, score: int) -> None: ...


class BulletManagerProtocol(Protocol):
    def update_all(self) -> None: ...
    def cleanup(self) -> None: ...
    def clear_enemy_bullets(self) -> None: ...


class BossManagerProtocol(Protocol):
    def update(self, player) -> None: ...
    def on_boss_hit(self, score: int) -> None: ...


class PlayerProtocol(Protocol):
    def update(self) -> None: ...
    def auto_fire(self) -> None: ...
    def cleanup_inactive_bullets(self) -> None: ...
    @property
    def active(self) -> bool: ...


class CollisionControllerProtocol(Protocol):
    def check_all_collisions(self, **kwargs) -> None: ...


class GameLoopManager:
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
        from airwar.game.explosion_animation import ExplosionManager

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
            self._game_controller.state.running = False
            return False

    def _update_core(self, player: PlayerProtocol) -> None:
        from airwar.game.controllers.game_controller import GameplayState

        has_regen = 'Regeneration' in self._reward_system.unlocked_buffs
        self._game_controller.update(player, has_regen)

        if self._game_controller.state.gameplay_state == GameplayState.DYING:
            self._game_renderer.update_death_animation()
            self._explosion_manager.update()
            return

        self._game_renderer.update_death_animation()
        self._explosion_manager.update()
        player.update()
        player.auto_fire()

        self._bullet_manager.update_all()
        self._update_enemy_spawning(player)
        self._update_entities()

        if self._spawn_controller.boss:
            self._boss_manager.update(player)

        self._spawn_controller.cleanup()
        self._bullet_manager.cleanup()
        player.cleanup_inactive_bullets()

        if not player.active:
            self._game_controller.state.running = False

    def _update_enemy_spawning(self, player: PlayerProtocol) -> None:
        spawn_needed = self._spawn_controller.update(
            self._game_controller.state.score,
            self._reward_system.slow_factor
        )

        if spawn_needed:
            boss = self._spawn_controller.spawn_boss(
                self._game_controller.cycle_count,
                self._reward_system.base_bullet_damage
            )
            self._game_controller.show_notification(
                f"! BOSS APPROACHING ({int(boss.data.escape_time/60)}s) !"
            )

    def _update_entities(self) -> None:
        for enemy in self._spawn_controller.enemies:
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
                player_invincible=self._game_controller.state.player_invincible,
                score_multiplier=self._game_controller.state.score_multiplier,
                on_enemy_killed=lambda score: self._game_controller.on_enemy_killed(score),
                on_boss_killed=lambda score: self._game_controller.on_boss_killed(score),
                on_boss_hit=lambda score: self._boss_manager.on_boss_hit(score),
                on_player_hit=on_player_hit,
                on_lifesteal=lambda player, score: self._reward_system.apply_lifesteal(player, score),
                on_clear_bullets=lambda: self._bullet_manager.clear_enemy_bullets(),
            )
        except Exception as e:
            import logging
            logging.error(f"Collision detection error: {e}", exc_info=True)

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
