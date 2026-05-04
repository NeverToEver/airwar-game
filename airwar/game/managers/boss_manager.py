"""Boss manager module.

Unified management of boss lifecycle, behavior, and combat logic.
Separates boss-related operations from GameScene.

Design principles:
- Single responsibility: Boss lifecycle and combat logic only.
- Dependency injection: Dependencies received via constructor.
- Facade pattern: Unified boss operation entry point.
- Composition over inheritance: Coordinates different components.

Usage:
    from airwar.game.managers import BossManager

    boss_manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
    boss_manager.update(player)
"""

from typing import TYPE_CHECKING

from .game_controller import normalize_score

if TYPE_CHECKING:
    from airwar.game.managers.spawn_controller import SpawnController
    from airwar.game.managers.game_controller import GameController
    from airwar.game.systems.reward_system import RewardSystem
    from airwar.game.managers import BulletManager


class BossManager:
    """Boss lifecycle and combat logic manager.

    Manages boss movement updates, escape handling, kill callbacks, and player collision.

    Responsibilities:
    - Boss movement and state updates.
    - Score settlement and rewards on boss kill.
    - Does not handle boss spawning (handled by SpawnController).
    - Does not handle collision detection (handled by CollisionController).

    Attributes:
        _spawn_controller: Enemy spawn controller (provides boss instance and enemy list).
        _game_controller: Game controller (provides state access and notifications).
        _reward_system: Reward system (provides lifesteal effects).
        _bullet_manager: Bullet manager (provides enemy bullet clearing).
    """

    def __init__(
        self,
        spawn_controller: 'SpawnController',
        game_controller: 'GameController',
        reward_system: 'RewardSystem',
        bullet_manager: 'BulletManager'
    ) -> None:
        """Initialize the boss manager.

        Args:
            spawn_controller: Enemy spawn controller.
            game_controller: Game controller.
            reward_system: Reward system.
            bullet_manager: Bullet manager.
        """
        self._spawn_controller = spawn_controller
        self._game_controller = game_controller
        self._reward_system = reward_system
        self._bullet_manager = bullet_manager
        self._player = None

    def update(self, player) -> None:
        """Update boss state.

        Called during the enemy spawn update flow.

        Args:
            player: Player object for tracking position.
        """
        self._player = player
        boss = self._spawn_controller.boss
        if not boss:
            return

        self._update_boss_movement(boss, player)
        self._handle_boss_escape(boss)

    def _update_boss_movement(self, boss, player) -> None:
        """Update boss movement.

        Args:
            boss: Boss instance.
            player: Player object.
        """
        player_pos = (player.rect.centerx, player.rect.centery)
        enemies = self._spawn_controller.enemies
        slow_factor = self._reward_system.slow_factor * boss.enrage_slow_factor()
        boss.update(enemies, slow_factor=slow_factor, player_pos=player_pos, player=player)

    def _handle_boss_escape(self, boss) -> None:
        """Handle boss escape.

        Shows an escape notification when the boss is alive but escaping.

        Args:
            boss: Boss instance.
        """
        if not boss or boss.active:
            return

        if boss.is_escaped():
            self._game_controller.show_notification("BOSS 逃跑! (+0)")

    def on_boss_hit(self, score: int) -> None:
        """Handle boss hit callback.

        Called when the boss is hit by a player bullet.
        Updates score, checks for kill, and handles kill rewards.

        Args:
            score: Score gained from the hit.
        """
        self._game_controller.show_notification(f"+{score} BOSS 分数!")
        self._game_controller.state.score = normalize_score(
            self._game_controller.state.score + score
        )

        if not self._spawn_controller.boss.active:
            self.on_boss_killed()

    def on_boss_killed(self) -> None:
        """Handle boss killed.

        Applies lifesteal and clears all enemy bullets.
        """
        boss = self._spawn_controller.boss
        if boss and self._player:
            self._reward_system.apply_lifesteal(self._player, boss.data.score)
        self._bullet_manager.clear_enemy_bullets(include_clear_immune=True)

    @property
    def has_boss(self) -> bool:
        """Check if there is an active boss.

        Returns:
            bool: True if a boss exists.
        """
        return self._spawn_controller.boss is not None

    @property
    def boss(self):
        """Get the current boss instance.

        Returns:
            Boss instance or None.
        """
        return self._spawn_controller.boss
