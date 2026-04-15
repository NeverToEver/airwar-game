import pygame
import random
import math
from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from .base import Entity, EnemyData, Vector2
from .bullet import Bullet, BulletData
from .interfaces import IBulletSpawner
from airwar.utils.sprites import draw_enemy_ship, draw_boss_ship

if TYPE_CHECKING:
    from airwar.scenes.game_scene import GameScene


class Enemy(Entity):
    def __init__(self, x: float, y: float, data: EnemyData):
        super().__init__(x, y, 40, 40)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = random.randint(0, data.fire_rate)
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self.entity_id = id(self)

    def update(self, *args, **kwargs) -> None:
        self.rect.y += self.data.speed

        from airwar.config import get_screen_height
        screen_height = get_screen_height()
        if self.rect.y > screen_height:
            self.active = False

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire()

    def _fire(self) -> None:
        bullets = self._create_bullets()
        
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _create_bullets(self) -> List[Bullet]:
        bullets = []
        center_x = self.rect.centerx - 5
        
        if self.data.bullet_type == "spread":
            for angle in [-20, 0, 20]:
                bullet_data = BulletData(
                    damage=self._get_damage(),
                    speed=5.0,
                    owner="enemy",
                    bullet_type="spread"
                )
                bullet = Bullet(center_x + angle, self.rect.bottom, bullet_data)
                bullet.velocity = Vector2(angle * 0.1, 5)
                bullets.append(bullet)
        elif self.data.bullet_type == "laser":
            bullet_data = BulletData(
                damage=self._get_damage(),
                speed=5.0,
                owner="enemy",
                bullet_type="laser"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(0, 8)
            bullets.append(bullet)
        else:
            bullet_data = BulletData(
                damage=self._get_damage(),
                speed=5.0,
                owner="enemy",
                bullet_type="single"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullets.append(bullet)
        
        return bullets

    def _get_damage(self) -> int:
        if self.data.bullet_type == "spread":
            return 8
        elif self.data.bullet_type == "laser":
            return 25
        else:
            return 15

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def render(self, surface: pygame.Surface) -> None:
        if not self._sprite:
            health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
            draw_enemy_ship(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, health_ratio)
        else:
            surface.blit(self._sprite, self.get_rect())

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite

    def take_damage(self, damage: int) -> None:
        self.health -= damage
        if self.health <= 0:
            self.active = False


class EnemySpawner:
    def __init__(self):
        self.spawn_timer = 0
        self.health = 100
        self.speed = 3.0
        self.spawn_rate = 30
        self.bullet_type = "single"
        self._bullet_spawner: Optional[IBulletSpawner] = None

    def set_params(self, health: int, speed: float, spawn_rate: int, bullet_type: str = "single") -> None:
        self.health = health
        self.speed = speed
        self.spawn_rate = spawn_rate
        self.bullet_type = bullet_type

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def update(self, enemies: List[Enemy], slow_factor: float = 1.0) -> None:
        from airwar.config import get_screen_width
        screen_width = get_screen_width()

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_rate:
            self.spawn_timer = 0
            x = random.randint(0, screen_width - 40)

            bullet_types = ["single", "spread", "laser"]
            bullet_type = random.choice(bullet_types)

            data = EnemyData(
                health=self.health,
                speed=self.speed * slow_factor,
                bullet_type=bullet_type,
                fire_rate=90 if bullet_type == "laser" else 120
            )
            enemy = Enemy(x, -40, data)
            if self._bullet_spawner:
                enemy.set_bullet_spawner(self._bullet_spawner)
            enemies.append(enemy)


@dataclass
class BossData:
    health: int = 500
    speed: float = 1.5
    score: int = 5000
    width: float = 120
    height: float = 100
    fire_rate: int = 60
    phase: int = 1
    escape_time: int = 1500


class Boss(Entity):
    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.move_direction = 1
        self.move_timer = 0
        self.attack_pattern = 0
        self.entering = True
        self.entry_y = y
        self.target_y = 80
        self.survival_timer = 0
        self.escaped = False
        self._show_escape_warning = False
        self.phase = data.phase
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self.entity_id = id(self)

    def update(self, *args, **kwargs) -> None:
        from airwar.config import get_screen_width
        screen_width = get_screen_width()

        if self.entering:
            self.rect.y += 2
            if self.rect.y >= self.target_y:
                self.rect.y = self.target_y
                self.entering = False
            return

        self.survival_timer += 1

        if self.survival_timer >= self.data.escape_time:
            self.escaped = True
            self.active = False
            return

        if self.survival_timer >= self.data.escape_time - 180:
            self._show_escape_warning = True
            self.rect.y -= 0.5

        self.move_timer += 1
        if self.move_timer >= 60:
            self.move_timer = 0
            self.move_direction *= -1

        self.rect.x += self.move_direction * self.data.speed

        if self.rect.x <= 0:
            self.rect.x = 0
            self.move_direction = 1
        elif self.rect.x >= screen_width - self.rect.width:
            self.rect.x = screen_width - self.rect.width
            self.move_direction = -1

        self.phase_timer += 1
        if self.phase_timer >= 300 and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire()

    def _fire(self) -> None:
        bullets = []
        
        if self.attack_pattern == 0:
            bullets = self._spread_attack()
        elif self.attack_pattern == 1:
            bullets = self._aim_attack()
        else:
            bullets = self._wave_attack()

        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _spread_attack(self) -> List[Bullet]:
        bullets = []
        center_x = self.rect.centerx
        bullet_count = 5 + self.phase

        for i in range(bullet_count):
            angle = -90 + (180 / (bullet_count - 1)) * i
            rad = math.radians(angle)
            speed = 5.0
            vx = math.cos(rad) * speed
            vy = math.sin(rad) * speed

            bullet_data = BulletData(
                damage=10 + self.phase * 2,
                speed=5.0,
                owner="enemy",
                bullet_type="spread"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(vx, vy)
            bullets.append(bullet)
        
        return bullets

    def _aim_attack(self, player_pos: Tuple[float, float] = None) -> List[Bullet]:
        bullets = []
        
        if player_pos is None:
            player_pos = (self.rect.centerx, self.rect.bottom + 500)
        
        player_x = player_pos[0]
        player_y = player_pos[1]
        
        bullet_data = BulletData(
            damage=15 + self.phase * 3,
            speed=7.0,
            owner="enemy",
            bullet_type="laser"
        )

        for i in range(3):
            bullet = Bullet(
                self.rect.centerx - 30 + i * 30,
                self.rect.bottom,
                bullet_data
            )
            dx = player_x - self.rect.centerx
            dy = player_y - self.rect.bottom
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                bullet.velocity = Vector2(dx / dist * 6, dy / dist * 6)
            bullets.append(bullet)
        
        return bullets

    def _wave_attack(self) -> List[Bullet]:
        bullets = []
        center_x = self.rect.centerx

        for i in range(8):
            angle = -90 + 22.5 * i
            rad = math.radians(angle)
            speed = 4.0

            bullet_data = BulletData(
                damage=8,
                speed=speed,
                owner="enemy",
                bullet_type="single"
            )
            bullet = Bullet(center_x, self.rect.centery, bullet_data)
            bullet.velocity = Vector2(math.cos(rad) * speed, math.sin(rad) * speed)
            bullets.append(bullet)
        
        return bullets

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def render(self, surface: pygame.Surface) -> None:
        health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
        draw_boss_ship(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, health_ratio)

        if self.entering:
            warning_y = 20
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.3 + 0.7
            warning_surf = pygame.font.Font(None, 36).render("! WARNING !", True, (255, 50, 50))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

        if self._show_escape_warning and not self.entering:
            warning_y = 50
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.02)) * 0.3 + 0.7
            warning_surf = pygame.font.Font(None, 28).render("ESCAPING...", True, (255, 200, 50))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

    def take_damage(self, damage: int) -> int:
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return self.data.score
        return 0

    def is_entering(self) -> bool:
        return self.entering

    def is_escaped(self) -> bool:
        return self.escaped

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)
