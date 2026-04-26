"""Explosion manager — unified trigger and update for explosions."""
from typing import Any, Dict

import pygame

from .explosion_pool import ExplosionPool
from ..constants import GAME_CONSTANTS


class ExplosionManager:
    """Explosion manager — provides unified explosion trigger and update interface"""

    DEFAULT_MAX_PER_SECOND = 30.0

    def __init__(
        self,
        max_per_second: float = DEFAULT_MAX_PER_SECOND,
        pool_max_size: int = 20
    ) -> None:
        self._pool = ExplosionPool(max_size=pool_max_size)
        self._max_per_second = max_per_second
        self._time_accumulator = 0.0
        self._explosions_this_second = 0
        self._dropped_explosions = 0
        self._total_explosions = 0

    def trigger(
        self,
        x: float,
        y: float,
        radius: int
    ) -> bool:
        """Trigger explosion effect

        Args:
            x: Explosion center X coordinate
            y: Explosion center Y coordinate
            radius: Explosion radius (pixels)

        Returns:
            True if successfully triggered, False if dropped due to frequency limit
        """
        if self._explosions_this_second >= self._max_per_second:
            self._dropped_explosions += 1
            return False

        effect = self._pool.acquire()
        if effect is None:
            self._dropped_explosions += 1
            return False

        effect.trigger(x, y, radius)
        self._explosions_this_second += 1
        self._total_explosions += 1

        return True

    def update(self, dt: float = 1.0) -> None:
        """Update explosion system state

        Args:
            dt: Time multiplier
        """
        self._time_accumulator += dt

        if self._time_accumulator >= GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION:
            self._explosions_this_second = 0
            self._time_accumulator = 0.0

        self._pool.update()

    def render(self, surface: pygame.Surface) -> None:
        """Render all active explosion effects

        Args:
            surface: PyGame rendering surface
        """
        for effect in self._pool.get_active_effects():
            effect.render(surface)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        pool_stats = self._pool.get_stats()
        return {
            **pool_stats,
            'max_per_second': self._max_per_second,
            'explosions_this_second': self._explosions_this_second,
            'dropped_explosions': self._dropped_explosions,
            'total_explosions': self._total_explosions,
            'active_count': len(self._pool.get_active_effects())
        }

    def reset_stats(self) -> None:
        """Reset statistics"""
        self._dropped_explosions = 0
        self._total_explosions = 0
