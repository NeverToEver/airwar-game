import pygame
from typing import Optional, List
from .base import Entity, BulletData, Vector2
from airwar.utils.sprites import draw_bullet
from airwar.utils.render_cache import SurfaceCache


class Bullet(Entity):
    def __init__(self, x: float, y: float, data: BulletData):
        super().__init__(x, y, 10, 10)
        self.data = data
        self.velocity = Vector2(0, -data.speed)
        self._trail: List[pygame.Rect] = []
        self._hit_enemies: List[int] = []

        if data.angle_offset != 0:
            import math
            angle_rad = math.radians(data.angle_offset)
            self.velocity = Vector2(
                data.speed * math.sin(angle_rad),
                -data.speed * math.cos(angle_rad)
            )

    def update(self, *args, **kwargs) -> None:
        if self.data.bullet_type == "laser" or self.data.is_laser:
            self._trail.append(pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height))
            if len(self._trail) > 8:
                self._trail.pop(0)

        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        from airwar.config import SCREEN_HEIGHT
        if self.rect.y < -self.rect.height:
            self.active = False

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)

    def render(self, surface: pygame.Surface) -> None:
        if not self._sprite:
            draw_bullet(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, self.data.bullet_type)
        else:
            surface.blit(self._sprite, self.get_rect())

        if (self.data.bullet_type == "laser" or self.data.is_laser) and self._trail:
            for i, trail_rect in enumerate(self._trail):
                alpha = int(100 * (i / len(self._trail)))
                trail_surface = SurfaceCache.get_rect_fill(
                    trail_rect.width,
                    trail_rect.height,
                    (255, 0, 100, alpha),
                )
                surface.blit(trail_surface, trail_rect)

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite
