import math
import random
from typing import List

import pygame

from airwar.game.explosion_animation.explosion_particle import ExplosionParticle


# Global glow surface cache for particles
_particle_glow_cache = {}


def _get_particle_glow_surface(glow_radius: int) -> pygame.Surface:
    """Get or create a cached glow surface for a particle."""
    cache_key = glow_radius
    if cache_key not in _particle_glow_cache:
        surf = pygame.Surface((glow_radius * 2 + 2, glow_radius * 2 + 2), pygame.SRCALPHA)
        _particle_glow_cache[cache_key] = surf
    return _particle_glow_cache[cache_key]


def clear_particle_glow_cache() -> None:
    """Clear the particle glow surface cache."""
    _particle_glow_cache.clear()


class ExplosionEffect:
    """Explosion effect — manages the complete lifecycle of an explosion animation"""

    PARTICLE_COUNT = 30
    PARTICLE_LIFE_MIN = 20
    PARTICLE_LIFE_MAX = 40
    PARTICLE_SPEED_MIN = 3.0
    PARTICLE_SPEED_MAX = 8.0
    PARTICLE_SIZE_MIN = 2.0
    PARTICLE_SIZE_MAX = 5.0

    def __init__(self) -> None:
        self._particles: List[ExplosionParticle] = []
        self._active = False
        self._x = 0.0
        self._y = 0.0
        self._radius = 0
        self._glow_surf_cache = None
        self._glow_surf_size = 0

    def trigger(self, x: float, y: float, radius: int) -> None:
        """Trigger explosion effect

        Args:
            x: Explosion center X coordinate
            y: Explosion center Y coordinate
            radius: Explosion radius (pixels)
        """
        self._x = x
        self._y = y
        self._radius = radius
        self._active = True
        self._particles.clear()
        self._glow_surf_cache = None
        self._glow_surf_size = 0
        self._generate_particles()

    def _generate_particles(self) -> None:
        """Generate explosion particles"""
        for _ in range(self.PARTICLE_COUNT):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(
                self.PARTICLE_SPEED_MIN,
                self.PARTICLE_SPEED_MAX
            )
            life = random.randint(
                self.PARTICLE_LIFE_MIN,
                self.PARTICLE_LIFE_MAX
            )
            size = random.uniform(
                self.PARTICLE_SIZE_MIN,
                self.PARTICLE_SIZE_MAX
            )

            self._particles.append(ExplosionParticle(
                x=self._x,
                y=self._y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life,
                max_life=life,
                size=size
            ))

    def update(self, dt: float = 1.0) -> bool:
        """Update explosion state

        Args:
            dt: Time multiplier

        Returns:
            True if explosion is still in progress, False if finished
        """
        if not self._active:
            return False

        for particle in self._particles:
            particle.update(dt)

        self._particles = [p for p in self._particles if p.is_alive()]

        if not self._particles:
            self._active = False
            return False

        return True

    def render(self, surface: pygame.Surface) -> None:
        """Render explosion effect

        Args:
            surface: PyGame rendering surface
        """
        if not self._active:
            return

        self._render_radius_indicator(surface)
        self._render_particles(surface)

    def _render_radius_indicator(self, surface: pygame.Surface) -> None:
        """Render explosion radius indicator"""
        if self._radius <= 0:
            return

        alpha = int(100 * (len(self._particles) / self.PARTICLE_COUNT))
        if alpha < 5:
            return

        radius_surf = pygame.Surface(
            (self._radius * 2 + 20, self._radius * 2 + 20),
            pygame.SRCALPHA
        )
        pygame.draw.circle(
            radius_surf,
            (255, 100, 30, alpha),
            (self._radius + 10, self._radius + 10),
            self._radius,
            2
        )
        surface.blit(
            radius_surf,
            (self._x - self._radius - 10, self._y - self._radius - 10)
        )

    def _render_particles(self, surface: pygame.Surface) -> None:
        """Render all particles"""
        for particle in self._particles:
            self._render_particle(surface, particle)

    def _render_particle(
        self,
        surface: pygame.Surface,
        particle: ExplosionParticle
    ) -> None:
        """Render a single particle"""
        alpha = particle.get_alpha()
        if alpha < 10:
            return

        color = particle.get_color()

        glow_radius = int(particle.size * 2)
        if glow_radius > 0:
            glow_surf = _get_particle_glow_surface(glow_radius)
            # Clear and redraw the glow (size-based cache)
            glow_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(
                glow_surf,
                (*color, int(alpha * 0.3)),
                (glow_radius + 1, glow_radius + 1),
                glow_radius
            )
            surface.blit(
                glow_surf,
                (int(particle.x) - glow_radius - 1, int(particle.y) - glow_radius - 1)
            )

        pygame.draw.circle(
            surface,
            color,
            (int(particle.x), int(particle.y)),
            max(1, int(particle.size * (alpha / 255)))
        )

    def reset(self) -> None:
        """Reset effect instance (called before returning to pool)"""
        self._particles.clear()
        self._active = False
        self._x = 0.0
        self._y = 0.0
        self._radius = 0
        self._glow_surf_cache = None
        self._glow_surf_size = 0

    def is_active(self) -> bool:
        """Check if explosion effect is active"""
        return self._active
