"""Bullet entity module.

Provides the Bullet class for all projectiles in the game, including
player bullets, enemy bullets, lasers, and explosive missiles.
"""

import math
from collections import deque
from typing import List

import pygame
from .base import Entity, BulletData, Vector2
from airwar.config import get_screen_width, get_screen_height


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
    OFFSCREEN_MARGIN: int = 80

    def __init__(self, x: float, y: float, data: BulletData):
        super().__init__(x, y, 10, 10)
        self.data = data
        self.velocity = Vector2(0, -data.speed)
        self._trail: deque = deque(maxlen=8)
        self._hit_enemies: List[int] = []

        if data.angle_offset != 0:
            angle_rad = math.radians(data.angle_offset)
            self.velocity = Vector2(
                data.speed * math.sin(angle_rad),
                -data.speed * math.cos(angle_rad)
            )

    def update(self, *args, **kwargs) -> None:
        if getattr(self, "held", False):
            return

        if self.data.bullet_type == "laser" or self.data.is_laser:
            self._trail.append((self.rect.x, self.rect.y, self.rect.width, self.rect.height))

        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        if self._is_offscreen():
            self.active = False

    def _is_offscreen(self) -> bool:
        margin = self.OFFSCREEN_MARGIN
        return (
            self.rect.right < -margin
            or self.rect.left > get_screen_width() + margin
            or self.rect.bottom < -margin
            or self.rect.top > get_screen_height() + margin
        )

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)

    def render(self, surface: pygame.Surface) -> None:
        if self._sprite:
            surface.blit(self._sprite, self.get_rect())

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite
