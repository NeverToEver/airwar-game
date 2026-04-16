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
        self.boss_spawn_interval = 1800
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
        escape_time = int(base_health / bullet_damage * 2.5)
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
        return boss

    def cleanup(self) -> None:
        self.enemies = [e for e in self.enemies if e.active]
        if self.boss and not self.boss.active:
            if self.boss.is_escaped():
                pass
            self.boss = None
