from typing import List, Optional
from airwar.entities import Enemy, Boss, EnemySpawner, BossData, Bullet
from airwar.entities.interfaces import IBulletSpawner
from airwar.config import get_screen_width


class SpawnController:
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
        self.boss_spawn_interval = settings.get('boss_spawn_interval', 1800)
        self._base_boss_spawn_interval = self.boss_spawn_interval
        self._escape_penalty_multiplier = settings.get('escape_penalty_multiplier', 1.5)
        self.boss_killed = False
        self._bullet_spawner: Optional[IBulletSpawner] = None

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner
        self.enemy_spawner.set_bullet_spawner(spawner)

    def init_bullet_system(self) -> None:
        from airwar.game.spawners.enemy_bullet_spawner import EnemyBulletSpawner
        bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        self.set_bullet_spawner(bullet_spawner)

    def update(self, score: int, slow_factor: float) -> bool:
        self.enemy_spawner.update(self.enemies, slow_factor)

        self.boss_spawn_timer += 1
        if self.boss is None and self.boss_spawn_timer >= self.boss_spawn_interval / slow_factor:
            self.boss_spawn_timer = 0
            return True
        return False

    def spawn_boss(self, cycle_count: int, bullet_damage: int) -> Boss:
        screen_width = get_screen_width()
        base_health = 2000 * (1 + cycle_count * 0.5)
        escape_time = int(base_health / bullet_damage * 45)
        escape_time = max(1200, min(escape_time, 3600))

        boss_data = BossData(
            health=base_health,
            speed=1.5 + cycle_count * 0.1,
            score=5000 + cycle_count * 1000,
            width=120,
            height=100,
            fire_rate=60 - cycle_count * 3,
            phase=1,
            escape_time=escape_time
        )

        boss = Boss(screen_width // 2 - boss_data.width // 2, -100, boss_data)
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

        i = 0
        while i < len(self.enemies):
            if not self.enemies[i].active:
                self.enemies.pop(i)
            else:
                i += 1

    def _handle_boss_cleanup(self) -> None:
        if self.boss and not self.boss.active:
            self.reset_boss_timer(penalty=self.boss.is_escaped())
            self.boss = None
