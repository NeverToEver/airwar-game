import pygame
from typing import List, Optional, TYPE_CHECKING
from .base import Entity, Vector2
from .bullet import Bullet, BulletData
from airwar.utils.sprites import draw_player_ship

if TYPE_CHECKING:
    from airwar.input.input_handler import InputHandler


class Player(Entity):
    def __init__(self, x: float, y: float, input_handler: 'InputHandler'):
        super().__init__(x, y, 50, 60)
        self._input_handler = input_handler
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.fire_cooldown = 0
        self.bullet_damage = 50
        self._bullets: List[Bullet] = []
        self.hitbox_width = 20
        self.hitbox_height = 24
        self.hitbox_timer = 0
        self._shot_mode = 'normal'
        self._laser_active = False
        self._laser_timer = 0
        self._laser_duration = 0
        self._laser_flicker = False

    def get_hitbox(self):
        hitbox_x = self.rect.x + (self.rect.width - self.hitbox_width) / 2
        hitbox_y = self.rect.y + (self.rect.height - self.hitbox_height) / 2
        from .base import Rect
        return Rect(hitbox_x, hitbox_y, self.hitbox_width, self.hitbox_height)

    def colliderect(self, other) -> bool:
        return self.get_hitbox().colliderect(other)

    def update(self, *args, **kwargs) -> None:
        from airwar.config import PLAYER_SPEED, get_screen_width, get_screen_height

        direction = self._input_handler.get_movement_direction()
        self.rect.x += direction.x * PLAYER_SPEED
        self.rect.y += direction.y * PLAYER_SPEED

        screen_width = get_screen_width()
        screen_height = get_screen_height()

        self.rect.x = max(0, min(self.rect.x, screen_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, screen_height - self.rect.height))

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        if self._laser_active:
            self._laser_timer -= 1
            self._laser_flicker = (self._laser_timer // 4) % 2 == 0
            if self._laser_timer <= 0:
                self._laser_active = False

        for bullet in self._bullets:
            bullet.update()

        self._bullets = [b for b in self._bullets if b.active]

        self.hitbox_timer += 1

    def auto_fire(self) -> None:
        from airwar.config import PLAYER_FIRE_RATE
        if self.fire_cooldown <= 0:
            self.fire_cooldown = PLAYER_FIRE_RATE

            if self._shot_mode == 'shotgun':
                center_x = self.rect.x + self.rect.width / 2 - 5
                for angle in [-15, 0, 15]:
                    bullet = Bullet(
                        center_x,
                        self.rect.y - 10,
                        BulletData(damage=self.bullet_damage),
                        angle_offset=angle,
                        bullet_type='shotgun'
                    )
                    self._bullets.append(bullet)
            elif self._shot_mode == 'laser':
                bullet = Bullet(
                    self.rect.x + self.rect.width / 2 - 3,
                    self.rect.y - 10,
                    BulletData(damage=self.bullet_damage, bullet_type='laser', is_laser=True)
                )
                self._bullets.append(bullet)
            else:
                bullet = Bullet(
                    self.rect.x + self.rect.width / 2 - 5,
                    self.rect.y - 10,
                    BulletData(damage=self.bullet_damage)
                )
                self._bullets.append(bullet)

    def fire(self) -> Optional[Bullet]:
        from airwar.config import PLAYER_FIRE_RATE
        if self.fire_cooldown <= 0:
            self.fire_cooldown = PLAYER_FIRE_RATE

            if self._shot_mode == 'shotgun':
                center_x = self.rect.x + self.rect.width / 2 - 5
                bullet = None
                for angle in [-15, 0, 15]:
                    b = Bullet(
                        center_x,
                        self.rect.y - 10,
                        BulletData(damage=self.bullet_damage),
                        angle_offset=angle,
                        bullet_type='shotgun'
                    )
                    self._bullets.append(b)
                    if bullet is None:
                        bullet = b
                return bullet
            elif self._shot_mode == 'laser':
                bullet = Bullet(
                    self.rect.x + self.rect.width / 2 - 3,
                    self.rect.y - 10,
                    BulletData(damage=self.bullet_damage, bullet_type='laser', is_laser=True)
                )
                self._bullets.append(bullet)
                return bullet
            else:
                bullet = Bullet(
                    self.rect.x + self.rect.width / 2 - 5,
                    self.rect.y - 10,
                    BulletData(damage=self.bullet_damage)
                )
                self._bullets.append(bullet)
                return bullet
        return None

    def activate_shotgun(self) -> None:
        self._shot_mode = 'shotgun'

    def activate_laser(self, duration: int = 180) -> None:
        self._shot_mode = 'laser'
        self._laser_active = True
        self._laser_timer = duration
        self._laser_duration = duration

    def is_laser_active(self) -> bool:
        return self._laser_active and self._laser_flicker

    def get_laser_progress(self) -> float:
        if self._laser_duration > 0:
            return self._laser_timer / self._laser_duration
        return 0.0

    def render(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0) -> None:
        if not self._sprite:
            draw_player_ship(surface, self.rect.x + offset_x, self.rect.y + offset_y, self.rect.width, self.rect.height)
        else:
            surface.blit(self._sprite, (self.rect.x + offset_x, self.rect.y + offset_y))

        self._render_hitbox(surface)

        for bullet in self._bullets:
            bullet.render(surface)

    def _render_hitbox(self, surface: pygame.Surface) -> None:
        if (self.hitbox_timer // 8) % 2 == 0:
            hb = self.get_hitbox()
            pygame.draw.rect(surface, (255, 100, 100, 150), (hb.x, hb.y, hb.width, hb.height), 2)

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite

    def get_bullets(self) -> List[Bullet]:
        return self._bullets

    def take_damage(self, damage: int) -> None:
        self.health -= damage
        if self.health <= 0:
            self.active = False
