import pygame
from typing import Optional, List
from .base import Entity, BulletData, Vector2
from airwar.utils.sprites import draw_bullet


class Bullet(Entity):
    def __init__(self, x: float, y: float, data: BulletData):
        super().__init__(x, y, 10, 10)
        self.data = data
        self.velocity = Vector2(0, -data.speed)
        self._trail: List[pygame.Rect] = []

    def update(self, *args, **kwargs) -> None:
        if self.data.bullet_type == "laser":
            self._trail.append(pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height))
            if len(self._trail) > 8:
                self._trail.pop(0)

        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        from airwar.config import SCREEN_HEIGHT
        if self.rect.y < -self.rect.height:
            self.active = False

    def render(self, surface: pygame.Surface) -> None:
        if not self._sprite:
            draw_bullet(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, self.data.bullet_type)
        else:
            surface.blit(self._sprite, self.get_rect())

        if self.data.bullet_type == "laser" and self._trail:
            for i, trail_rect in enumerate(self._trail):
                alpha = int(100 * (i / len(self._trail)))
                trail_surface = pygame.Surface((trail_rect.width, trail_rect.height), pygame.SRCALPHA)
                trail_surface.fill((255, 0, 100, alpha))
                surface.blit(trail_surface, trail_rect)

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite
