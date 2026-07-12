"""Player aim component.

Owns: aim target, facing angle/direction, and the rotated-sprite cache.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
The facing direction is read by :class:`PlayerWeapon` to compute
muzzle positions and bullet velocity; the sprite cache is read by
:attr:`Player.render`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from airwar.entities.base import Vector2
from airwar.utils.sprites import get_player_sprite

if TYPE_CHECKING:
    from airwar.entities.player import Player


class PlayerAim:
    """Aim state: target, facing angle/direction, rotated sprite cache.

    Args:
        owner: The Player instance (reads ``rect`` for the aim origin
            and ``hitbox_timer`` for sprite rotation animation ticks).
    """

    AIM_TURN_RATE_DEGREES = 7.0
    ROTATED_SPRITE_ANGLE_STEP = 2.0
    ROTATED_SPRITE_CACHE_MAX = 192

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self._aim_target: tuple[float, float] | None = None
        self._facing_angle_degrees: float = 0.0
        self._facing_direction: Vector2 = Vector2(0, -1)
        self._rotated_sprite_cache: dict[tuple[int, int, int], pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def set_aim_target(self, x: float, y: float) -> None:
        self._aim_target = (x, y)

    def get_facing_direction(self) -> Vector2:
        return self._facing_direction

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Turn the ship toward the aim target at AIM_TURN_RATE_DEGREES."""
        if self._aim_target is None:
            return
        target_direction = self._get_aim_direction(self._owner.rect.centerx, self._owner.rect.centery)
        if target_direction.length() <= 0:
            return
        target_angle = self._direction_to_angle_degrees(target_direction)
        delta = self._shortest_angle_delta(self._facing_angle_degrees, target_angle)
        max_step = self.AIM_TURN_RATE_DEGREES
        if abs(delta) <= max_step:
            self._facing_angle_degrees = target_angle
        else:
            self._facing_angle_degrees += max_step if delta > 0 else -max_step
        self._facing_angle_degrees = self._normalize_angle_degrees(self._facing_angle_degrees)
        self._facing_direction = self._angle_to_direction(self._facing_angle_degrees)

    def rotated_ship_sprite(self) -> pygame.Surface:
        """Return the rotated ship sprite, using a per-size/per-angle cache."""
        owner = self._owner
        width = int(owner.rect.width)
        height = int(owner.rect.height)
        angle_bucket = self._rotation_angle_bucket(self._facing_angle_degrees)
        cache_key = (width, height, angle_bucket)
        sprite = self._rotated_sprite_cache.get(cache_key)
        if sprite is None:
            if len(self._rotated_sprite_cache) >= self.ROTATED_SPRITE_CACHE_MAX:
                self._rotated_sprite_cache.pop(next(iter(self._rotated_sprite_cache)))
            base_sprite = get_player_sprite(width, height)
            sprite = pygame.transform.rotozoom(base_sprite, -angle_bucket, 1.0)
            self._rotated_sprite_cache[cache_key] = sprite
        return sprite

    # ------------------------------------------------------------------
    # Aim math helpers
    # ------------------------------------------------------------------

    def _get_aim_direction(self, origin_x: float, origin_y: float) -> Vector2:
        if self._aim_target is None:
            return self._facing_direction

        dx = self._aim_target[0] - origin_x
        dy = self._aim_target[1] - origin_y
        length = math.hypot(dx, dy)
        if length <= 0.001:
            return self._facing_direction

        return Vector2(dx / length, dy / length)

    @classmethod
    def _rotation_angle_bucket(cls, angle_degrees: float) -> int:
        bucket = round(angle_degrees / cls.ROTATED_SPRITE_ANGLE_STEP) * cls.ROTATED_SPRITE_ANGLE_STEP
        return int(cls._normalize_angle_degrees(bucket))

    @staticmethod
    def _direction_to_angle_degrees(direction: Vector2) -> float:
        return math.degrees(math.atan2(direction.x, -direction.y))

    @staticmethod
    def _angle_to_direction(angle_degrees: float) -> Vector2:
        angle_rad = math.radians(angle_degrees)
        return Vector2(math.sin(angle_rad), -math.cos(angle_rad))

    @staticmethod
    def _normalize_angle_degrees(angle_degrees: float) -> float:
        return ((angle_degrees + 180.0) % 360.0) - 180.0

    @classmethod
    def _shortest_angle_delta(cls, current: float, target: float) -> float:
        return cls._normalize_angle_degrees(target - current)
