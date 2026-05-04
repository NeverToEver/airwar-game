"""Explosion manager — unified trigger and update for explosions."""
import math
from dataclasses import dataclass
from typing import Any, Dict

import pygame

from .explosion_pool import ExplosionPool
from ..constants import GAME_CONSTANTS


@dataclass
class _QueuedExplosion:
    delay: int
    x: float
    y: float
    radius: int


class ExplosionManager:
    """Explosion manager — provides unified explosion trigger and update interface"""

    DEFAULT_MAX_PER_SECOND = 30.0
    BOSS_DEATH_MAX_ACTIVE_DELAY = 26

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
        self._queued_explosions: list[_QueuedExplosion] = []

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

    def trigger_boss_death(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """Queue a multi-stage boss wreck explosion without owning boss lifetime."""
        span_x = max(40.0, width * 0.42)
        span_y = max(32.0, height * 0.34)
        base_radius = max(28, int(max(width, height) * 0.18))
        offsets = [
            (0.0, 0.0, 0, 1.45),
            (-0.55, -0.12, 4, 0.86),
            (0.58, -0.08, 8, 0.9),
            (-0.28, 0.28, 12, 0.72),
            (0.26, 0.34, 16, 0.76),
            (-0.08, -0.34, 20, 0.68),
            (0.0, 0.12, self.BOSS_DEATH_MAX_ACTIVE_DELAY, 1.05),
        ]
        for offset_x, offset_y, delay, scale in offsets:
            wobble_x = math.sin(delay * 0.73) * width * 0.035
            wobble_y = math.cos(delay * 0.61) * height * 0.03
            explosion = _QueuedExplosion(
                delay=delay,
                x=x + span_x * offset_x + wobble_x,
                y=y + span_y * offset_y + wobble_y,
                radius=max(18, int(base_radius * scale)),
            )
            if delay <= 0:
                self.trigger(explosion.x, explosion.y, explosion.radius)
            else:
                self._queued_explosions.append(explosion)

    def update(self, dt: float = 1.0) -> None:
        """Update explosion system state

        Args:
            dt: Time multiplier
        """
        self._update_queued_explosions(dt)
        self._time_accumulator += dt

        if self._time_accumulator >= GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION:
            self._explosions_this_second = 0
            self._time_accumulator = 0.0

        self._pool.update()

    def _update_queued_explosions(self, dt: float) -> None:
        if not self._queued_explosions:
            return
        elapsed = max(1, int(dt))
        ready = []
        waiting = []
        for explosion in self._queued_explosions:
            explosion.delay -= elapsed
            if explosion.delay <= 0:
                ready.append(explosion)
            else:
                waiting.append(explosion)
        self._queued_explosions = waiting
        for explosion in ready:
            self.trigger(explosion.x, explosion.y, explosion.radius)

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
            'active_count': len(self._pool.get_active_effects()),
            'queued_count': len(self._queued_explosions),
        }

    def reset_stats(self) -> None:
        """Reset statistics"""
        self._dropped_explosions = 0
        self._total_explosions = 0
