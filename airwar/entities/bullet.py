"""Bullet entity module.

Provides the Bullet class for all projectiles in the game, including
player bullets, enemy bullets, lasers, and explosive missiles.
"""

import pygame
from collections import deque
from typing import Optional, List
from .base import Entity, BulletData, Vector2
from ..utils.sprites import draw_bullet, draw_explosive_missile
from ..config import SCREEN_HEIGHT


class Bullet(Entity):
    """Bullet entity for all projectiles.

    Handles movement, collision tracking, and rendering. Supports various
    bullet types (single, spread, laser, explosive) with trail effects
    for laser bullets.

    Class Attributes:
        _trail_surface_cache: Cache for trail surface rendering.
        _trail_cache_order: LRU cache order for trail surfaces (deque).
        _TRAIL_CACHE_MAX_SIZE: Maximum number of cached trail surfaces.

    Attributes:
        data: BulletData containing bullet configuration.
        velocity: Current velocity vector.
        _trail: Trail positions for laser bullets (deque, maxlen=8).
        _hit_enemies: List of enemy IDs already hit by this bullet.
    """

    _trail_surface_cache: dict = {}
    _trail_cache_order: deque = deque()
    _TRAIL_CACHE_MAX_SIZE: int = 256

    def __init__(self, x: float, y: float, data: BulletData):
        super().__init__(x, y, 10, 10)
        self.data = data
        self.velocity = Vector2(0, -data.speed)
        self._trail: deque = deque(maxlen=8)
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
            self._trail.append((self.rect.x, self.rect.y, self.rect.width, self.rect.height))

        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        if self.rect.y < -self.rect.height:
            self.active = False

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)

    def render(self, surface: pygame.Surface) -> None:
        if not self._sprite:
            if self.data.is_explosive:
                draw_explosive_missile(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height)
            else:
                draw_bullet(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, self.data.bullet_type, self.data.owner)
        else:
            surface.blit(self._sprite, self.get_rect())

        if (self.data.bullet_type == "laser" or self.data.is_laser) and self._trail:
            # Player laser: green, Enemy laser: red
            if self.data.owner == "player":
                trail_color = (30, 255, 100)
            else:
                trail_color = (255, 30, 30)
            trail_len = len(self._trail)
            for i, (tx, ty, tw, th) in enumerate(self._trail):
                alpha = int(120 * (i / trail_len))
                cache_key = (tw, th, alpha, self.data.owner)
                if cache_key not in Bullet._trail_surface_cache:
                    if len(Bullet._trail_surface_cache) >= Bullet._TRAIL_CACHE_MAX_SIZE:
                        oldest = Bullet._trail_cache_order.popleft()
                        Bullet._trail_surface_cache.pop(oldest, None)
                    trail_surface = pygame.Surface((tw, th), pygame.SRCALPHA)
                    trail_color_with_alpha = trail_color + (alpha,)
                    trail_surface.fill(trail_color_with_alpha)
                    Bullet._trail_surface_cache[cache_key] = trail_surface
                    Bullet._trail_cache_order.append(cache_key)
                else:
                    trail_surface = Bullet._trail_surface_cache[cache_key]
                surface.blit(trail_surface, (tx, ty))

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite
