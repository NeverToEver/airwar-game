"""Enemy and boss spawning controller with wave management."""
import random
from typing import List, Optional, TYPE_CHECKING
from ...entities import Enemy, Boss, EnemySpawner, BossData, Bullet
from ...entities.interfaces import IBulletSpawner
from ...config import get_screen_width, BASE_ENEMY_PARAMS

if TYPE_CHECKING:
    from ..systems.difficulty_manager import DifficultyManager

from ..spawners.enemy_bullet_spawner import EnemyBulletSpawner


class SpawnController:
    """Enemy and boss spawn controller with wave-based spawning.

        Manages enemy wave lifecycle and boss spawn timing. Uses EnemySpawner
        for enemy creation and tracks boss state for escape/cleanup logic.

        Attributes:
            enemies: List of active Enemy entities.
            enemy_bullets: List of active enemy bullet entities.
            boss: Current Boss instance or None.
        """
    BOSS_SPAWN_INTERVAL = 1800
    ESCAPE_PENALTY_MULT = 1.5
    ENEMY_EXIT_X_OFFSETS = [-300, 300, 0, -150, 150]
    ENEMY_EXIT_END_Y = -100
    BOSS_BASE_HEALTH = 2000
    BOSS_HEALTH_SCALING = 0.5
    ESCAPE_TIME_DIVISOR = 45
    MIN_ESCAPE_TIME = 1200
    MAX_ESCAPE_TIME = 3600
    BOSS_BASE_SPEED = 1.5
    BOSS_SPEED_INCREMENT = 0.1
    BOSS_BASE_SCORE = 400
    BOSS_SCORE_INCREMENT = 100
    BOSS_SPRITE_WIDTH = 120
    BOSS_SPRITE_HEIGHT = 100
    BOSS_BASE_FIRE_RATE = 45
    BOSS_FIRE_RATE_DECREMENT = 2
    BOSS_SPAWN_Y = -100
    def __init__(self, settings: dict):
        self.enemy_spawner = EnemySpawner()
        self.enemy_spawner.set_params(
            health=settings['enemy_health'],
            speed=settings['enemy_speed'],
            spawn_rate=settings['spawn_rate']
        )

        self.enemies: List[Enemy] = []
        self.enemy_bullets: List[Bullet] = []
        self.boss: Optional[Boss] = None
        self.boss_spawn_timer = 0
        self.boss_spawn_interval = settings.get('boss_spawn_interval', self.BOSS_SPAWN_INTERVAL)
        self._base_boss_spawn_interval = self.boss_spawn_interval
        self._escape_penalty_multiplier = settings.get('escape_penalty_multiplier', self.ESCAPE_PENALTY_MULT)
        self.boss_killed = False
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self._difficulty_manager: Optional['DifficultyManager'] = None

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner
        self.enemy_spawner.set_bullet_spawner(spawner)

    def set_difficulty_manager(self, manager: 'DifficultyManager') -> None:
        self._difficulty_manager = manager

    def get_current_params(self) -> dict:
        if self._difficulty_manager:
            return self._difficulty_manager.get_current_params()

        return {
            'speed': BASE_ENEMY_PARAMS['speed'],
            'fire_rate': BASE_ENEMY_PARAMS['fire_rate'],
            'aggression': BASE_ENEMY_PARAMS['aggression'],
            'spawn_rate': BASE_ENEMY_PARAMS['spawn_rate'],
            'multiplier': 1.0,
            'boss_kills': 0,
            'complexity': 1,
        }

    def init_bullet_system(self) -> None:
        bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        self.set_bullet_spawner(bullet_spawner)

    def update(self, score: int, slow_factor: float, player_pos: tuple = None) -> bool:
        # Don't spawn new enemies when boss is active
        if self.boss is None:
            self.enemy_spawner.update(self.enemies, slow_factor, player_pos)

        self.boss_spawn_timer += 1
        if self.boss is None and self.boss_spawn_timer >= self.boss_spawn_interval / slow_factor:
            self.boss_spawn_timer = 0
            return True
        return False

    def spawn_boss(self, boss_kill_count: int, bullet_damage: int) -> Boss:
        # Force all existing enemies to exit when boss appears
        for enemy in self.enemies:
            if enemy.active and getattr(enemy, '_state', None) == 'active':
                enemy.begin_exit(
                    enemy.rect.x + random.choice(self.ENEMY_EXIT_X_OFFSETS),
                    self.ENEMY_EXIT_END_Y
                )

        screen_width = get_screen_width()
        base_health = self.BOSS_BASE_HEALTH * (1 + boss_kill_count * self.BOSS_HEALTH_SCALING)
        escape_time = round(base_health / bullet_damage * self.ESCAPE_TIME_DIVISOR)
        escape_time = max(self.MIN_ESCAPE_TIME, min(escape_time, self.MAX_ESCAPE_TIME))

        boss_data = BossData(
            health=base_health,
            speed=self.BOSS_BASE_SPEED + boss_kill_count * self.BOSS_SPEED_INCREMENT,
            score=self.BOSS_BASE_SCORE + boss_kill_count * self.BOSS_SCORE_INCREMENT,
            width=self.BOSS_SPRITE_WIDTH,
            height=self.BOSS_SPRITE_HEIGHT,
            fire_rate=self.BOSS_BASE_FIRE_RATE - boss_kill_count * self.BOSS_FIRE_RATE_DECREMENT,
            phase=1,
            escape_time=escape_time
        )

        boss = Boss(screen_width // 2 - boss_data.width // 2, self.BOSS_SPAWN_Y, boss_data)
        if self._bullet_spawner:
            boss.set_bullet_spawner(self._bullet_spawner)
        self.boss = boss
        self.boss_spawn_interval = self._base_boss_spawn_interval
        return boss

    def reset_boss_timer(self, penalty: bool = False) -> None:
        self.boss_spawn_timer = 0
        if penalty:
            self.boss_spawn_interval = int(self._base_boss_spawn_interval * self._escape_penalty_multiplier)

    def cleanup(self) -> None:
        self.cleanup_enemies()
        self._handle_boss_cleanup()

    def cleanup_enemies(self) -> None:
        if not self.enemies:
            return
        if not any(not e.active for e in self.enemies):
            return
        self.enemies = [e for e in self.enemies if e.active]

    def _handle_boss_cleanup(self) -> None:
        if self.boss and not self.boss.active:
            self.reset_boss_timer(penalty=self.boss.is_escaped())
            self.boss = None
