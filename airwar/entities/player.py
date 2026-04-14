import pygame
from typing import List, Optional
from .base import Entity, Vector2
from .bullet import Bullet, BulletData
from airwar.utils.sprites import draw_player_ship


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 50, 60)
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.fire_cooldown = 0
        self.bullet_damage = 50
        self._bullets: List[Bullet] = []
        self.hitbox_width = 20
        self.hitbox_height = 24
        self.hitbox_timer = 0

    def get_hitbox(self):
        hitbox_x = self.rect.x + (self.rect.width - self.hitbox_width) / 2
        hitbox_y = self.rect.y + (self.rect.height - self.hitbox_height) / 2
        from .base import Rect
        return Rect(hitbox_x, hitbox_y, self.hitbox_width, self.hitbox_height)

    def colliderect(self, other) -> bool:
        return self.get_hitbox().colliderect(other)

    def update(self, *args, **kwargs) -> None:
        keys = kwargs.get('keys', [])
        from airwar.config import PLAYER_SPEED, get_screen_width, get_screen_height
        screen_width = get_screen_width()
        screen_height = get_screen_height()

        def is_pressed(*kcodes):
            for k in kcodes:
                if k < len(keys) and keys[k]:
                    return True
            return False

        if is_pressed(pygame.K_LEFT, pygame.K_a):
            self.rect.x -= PLAYER_SPEED
        if is_pressed(pygame.K_RIGHT, pygame.K_d):
            self.rect.x += PLAYER_SPEED
        if is_pressed(pygame.K_UP, pygame.K_w):
            self.rect.y -= PLAYER_SPEED
        if is_pressed(pygame.K_DOWN, pygame.K_s):
            self.rect.y += PLAYER_SPEED

        self.rect.x = max(0, min(self.rect.x, screen_width - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, screen_height - self.rect.height))

        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        for bullet in self._bullets:
            bullet.update()

        self._bullets = [b for b in self._bullets if b.active]

        self.hitbox_timer += 1

    def auto_fire(self) -> None:
        from airwar.config import PLAYER_FIRE_RATE
        if self.fire_cooldown <= 0:
            self.fire_cooldown = PLAYER_FIRE_RATE
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
            bullet = Bullet(
                self.rect.x + self.rect.width / 2 - 5,
                self.rect.y - 10,
                BulletData(damage=self.bullet_damage)
            )
            self._bullets.append(bullet)
            return bullet
        return None

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
