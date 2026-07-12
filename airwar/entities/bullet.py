"""Bullet entity module.

Provides the Bullet class for all projectiles in the game, including
player bullets, enemy bullets, lasers, and explosive missiles.
"""

import math
from collections import deque

import pygame

from airwar.config import get_screen_height, get_screen_width

from .base import BulletData, Entity, Vector2


class Bullet(Entity):
    """Bullet entity for all projectiles.

    Handles movement, collision tracking, and rendering. Supports various
    bullet types (single, spread, laser, explosive) with trail effects
    for laser bullets.

    Note: The real trail surface cache lives on
    ``airwar.game.rendering.entity_renderer.EntityRenderer``; this class
    keeps no class-level cache of its own.

    Attributes:
        data: BulletData containing bullet configuration.
        velocity: Current velocity vector.
        _trail: Trail positions for laser bullets (deque, maxlen=8).
        _hit_enemies: List of enemy IDs already hit by this bullet.
    """

    OFFSCREEN_MARGIN: int = 80

    def __init__(self, x: float, y: float, data: BulletData):
        super().__init__(x, y, 10, 10)
        self.data = data
        self.velocity = Vector2(0, -data.speed)
        self._trail: deque = deque(maxlen=8)
        self._hit_enemies: list[int] = []

        # Boss enrage held-shot state
        self.held: bool = False
        self.clear_immune: bool = False
        self.release_direction: Vector2 | None = None
        self.enrage_release_speed: float = 0.0
        self.enrage_release_pending: bool = False
        self.enrage_release_delay: int = 0

        if data.angle_offset != 0:
            angle_rad = math.radians(data.angle_offset)
            self.velocity = Vector2(data.speed * math.sin(angle_rad), -data.speed * math.cos(angle_rad))

    def take_damage(self, damage: int) -> None:
        """Bullets do not take damage.

        Required by the :class:`Entity` interface; bullets are destroyed by
        collision or boundary checks, not by incoming damage.
        """
        pass

    def update(self, *args, **kwargs) -> None:
        """Advance the bullet one frame: record trail, move, and cull offscreen.

        For laser bullets, the current rect is appended to the trail
        history (deque maxlen=8) before movement. Bullets flagged as
        `held` (e.g. boss-aimed charged shots) are skipped entirely.
        Bullets that leave the screen plus a small margin are marked
        inactive so cleanup passes can drop them.

        Args:
            *args: Ignored (uniform signature with other entities).
            **kwargs: Ignored (uniform signature with other entities).
        """
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
        """Return whether this bullet has already hit the given enemy.

        Used by piercing logic to avoid double-counting damage on the
        same enemy. Enemy identity is provided by the caller (typically
        `id(enemy)`).

        Args:
            enemy_id: Stable enemy identifier (object id) to check.

        Returns:
            bool: True if the enemy is in this bullet's hit set.
        """
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        """Record that this bullet has hit the given enemy.

        Called by the collision system when a piercing bullet deals
        damage to an enemy; subsequent `has_hit_enemy` calls for the
        same id will return True.

        Args:
            enemy_id: Stable enemy identifier to add to the hit set.
        """
        self._hit_enemies.append(enemy_id)

    def render(self, surface: pygame.Surface) -> None:
        """Blit the bullet's sprite at its current position.

        A no-op if no sprite has been assigned.

        Args:
            surface: Target pygame surface to draw onto.
        """
        if self._sprite:
            surface.blit(self._sprite, self.get_rect())

    def set_sprite(self, sprite: pygame.Surface) -> None:
        """Assign the pre-rendered sprite used by `render`.

        Args:
            sprite: pygame.Surface to blit for this bullet.
        """
        self._sprite = sprite
