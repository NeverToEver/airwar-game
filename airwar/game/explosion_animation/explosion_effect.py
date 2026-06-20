"""Explosion effect — individual explosion particle and rendering."""

import math
import random
from collections import OrderedDict

import pygame

from airwar.core_bindings import (
    batch_render_particles,
    batch_update_particles,
    generate_explosion_particles,
)

from ..constants import GAME_CONSTANTS
from .explosion_particle import ExplosionParticle

# Pre-rendered glow texture cache — avoids per-frame pygame.draw.circle() loops
# 限制缓存大小防止内存泄漏
# Note: the LRU helpers below call ``.move_to_end`` and ``.popitem(last=...)``,
# which are ``OrderedDict``-only APIs. Using a plain ``{}`` here is a silent
# regression that only surfaces at runtime (the dummy SDL driver never
# reaches the explosion render path during tests). See commit cfd0d5c.
_MAX_CACHE_SIZE = 64
_glow_texture_cache: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()
_spark_core_cache: "OrderedDict[int, pygame.Surface]" = OrderedDict()
_flash_cache: "OrderedDict[int, pygame.Surface]" = OrderedDict()


def _get_glow_texture(radius: int, base_color=(255, 120, 20), alpha_mult=0.15) -> pygame.Surface:
    """Get or create a pre-rendered soft radial glow texture.

    The glow is rendered once and cached — callers just blit it.

    The cache is LRU (least-recently-used): on hit the key is moved to
    the back, on insert at capacity the front (oldest) entry is evicted.
    """
    cache_key = (radius, base_color, alpha_mult)
    if cache_key in _glow_texture_cache:
        _glow_texture_cache.move_to_end(cache_key)
        return _glow_texture_cache[cache_key]
    if len(_glow_texture_cache) >= _MAX_CACHE_SIZE:
        _glow_texture_cache.popitem(last=False)
    size = radius * 2 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        ring_alpha = int(255 * alpha_mult * (r / radius))
        if ring_alpha > 0:
            pygame.draw.circle(
                surf,
                (*base_color, ring_alpha),
                (radius + 1, radius + 1),
                r,
            )
    _glow_texture_cache[cache_key] = surf
    return surf


def _get_spark_core(size: int) -> pygame.Surface:
    """Get or create a cached bright dot for spark particle cores.

    LRU eviction: on hit the key is moved to the back, on insert at
    capacity the front (oldest) entry is evicted.
    """
    if size in _spark_core_cache:
        _spark_core_cache.move_to_end(size)
        return _spark_core_cache[size]
    if len(_spark_core_cache) >= _MAX_CACHE_SIZE:
        _spark_core_cache.popitem(last=False)
    s = size * 2 + 2
    surf = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 202, 132, 210), (size + 1, size + 1), size)
    _spark_core_cache[size] = surf
    return surf


def _get_flash_surface(radius: int) -> pygame.Surface:
    """Get or create a cached flash surface with dual circles.

    The flash consists of an outer white circle and an inner warm-tinted circle.

    LRU eviction: on hit the key is moved to the back, on insert at
    capacity the front (oldest) entry is evicted.
    """
    if radius in _flash_cache:
        _flash_cache.move_to_end(radius)
        return _flash_cache[radius]
    if len(_flash_cache) >= _MAX_CACHE_SIZE:
        _flash_cache.popitem(last=False)
    size = radius * 4 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    pygame.draw.circle(surf, (255, 188, 96, 180), (radius * 2 + 1, radius * 2 + 1), radius)
    pygame.draw.circle(surf, (255, 154, 72, 115), (radius * 2 + 1, radius * 2 + 1), int(radius * 0.6))
    _flash_cache[radius] = surf
    return surf


class ExplosionEffect:
    """Explosion effect — manages the complete lifecycle of an explosion animation"""

    PARTICLE_COUNT = 15
    SPARK_COUNT = 10
    DEBRIS_COUNT = 5
    PARTICLE_LIFE_MIN = 20
    PARTICLE_LIFE_MAX = 40
    SPARK_LIFE_MIN = 10
    SPARK_LIFE_MAX = 25
    DEBRIS_LIFE_MIN = 25
    DEBRIS_LIFE_MAX = 50
    PARTICLE_SPEED_MIN = 3.0
    PARTICLE_SPEED_MAX = 8.0
    SPARK_SPEED_MIN = 5.0
    SPARK_SPEED_MAX = 12.0
    DEBRIS_SPEED_MIN = 2.0
    DEBRIS_SPEED_MAX = 5.0
    PARTICLE_SIZE_MIN = 2.0
    PARTICLE_SIZE_MAX = 5.0
    SPARK_SIZE_MIN = 1.0
    SPARK_SIZE_MAX = 2.0
    DEBRIS_SIZE_MIN = 1.5
    DEBRIS_SIZE_MAX = 3.0
    CENTRAL_GLOW_ALPHA_MAX = 92
    CORE_FLASH_ALPHA_MAX = 82
    SHOCKWAVE_ALPHA_MAX = 58
    PARTICLE_ALPHA_MAX = 170
    INNER_CORE_ALPHA_BONUS = 22

    def __init__(self) -> None:
        self._particles: list[ExplosionParticle] = []
        self._sparks: list[ExplosionParticle] = []
        self._debris: list[ExplosionParticle] = []
        self._particle_pool: list[ExplosionParticle] = []  # Pool for reusing particles
        self._active = False
        self._x = 0.0
        self._y = 0.0
        self._radius = 0
        self._glow_surf_cache = None
        self._glow_surf_size = 0
        self._shockwave_radius = 0
        self._shockwave_max_radius = 0
        self._core_flash = 1.0
        self._central_glow = 1.0

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
        self._sparks.clear()
        self._debris.clear()
        self._glow_surf_cache = None
        self._glow_surf_size = 0
        self._shockwave_radius = 0
        self._shockwave_max_radius = radius * 2.5
        self._core_flash = 1.0
        self._central_glow = 1.0
        self._generate_particles()

    def _acquire_particle(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: int,
        max_life: int,
        size: float,
        particle_type: str = "main",
    ) -> ExplosionParticle:
        """Acquire a particle, reusing from pool if available"""
        if self._particle_pool:
            p = self._particle_pool.pop()
            p.x = x
            p.y = y
            p.vx = vx
            p.vy = vy
            p.life = life
            p.max_life = max_life
            p.size = size
            p.particle_type = particle_type
            return p
        return ExplosionParticle(
            x=x, y=y, vx=vx, vy=vy, life=life, max_life=max_life, size=size, particle_type=particle_type
        )

    def _generate_particles(self) -> None:
        """Generate explosion particles using Rust."""
        particle_data = generate_explosion_particles(
            self._x,
            self._y,
            self.PARTICLE_COUNT,
            self.PARTICLE_LIFE_MIN,
            self.PARTICLE_LIFE_MAX,
            self.PARTICLE_SPEED_MIN,
            self.PARTICLE_SPEED_MAX,
            self.PARTICLE_SIZE_MIN,
            self.PARTICLE_SIZE_MAX,
        )
        for x, y, vx, vy, life, max_life, size in particle_data:
            self._particles.append(self._acquire_particle(x, y, vx, vy, life, max_life, size))

        for _ in range(self.SPARK_COUNT):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(self.SPARK_SPEED_MIN, self.SPARK_SPEED_MAX)
            life = random.randint(self.SPARK_LIFE_MIN, self.SPARK_LIFE_MAX)
            size = random.uniform(self.SPARK_SIZE_MIN, self.SPARK_SIZE_MAX)
            self._sparks.append(
                self._acquire_particle(
                    self._x, self._y, math.cos(angle) * speed, math.sin(angle) * speed, life, life, size, "spark"
                )
            )

        for _ in range(self.DEBRIS_COUNT):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(self.DEBRIS_SPEED_MIN, self.DEBRIS_SPEED_MAX)
            life = random.randint(self.DEBRIS_LIFE_MIN, self.DEBRIS_LIFE_MAX)
            size = random.uniform(self.DEBRIS_SIZE_MIN, self.DEBRIS_SIZE_MAX)
            self._debris.append(
                self._acquire_particle(
                    self._x, self._y, math.cos(angle) * speed, math.sin(angle) * speed, life, life, size, "debris"
                )
            )

    def update(self, dt: float = 1.0) -> bool:
        """Update explosion state

        Args:
            dt: Time multiplier

        Returns:
            True if explosion is still in progress, False if finished
        """
        if not self._active:
            return False

        max_lives = [p.max_life for p in self._particles]
        particle_data = [(p.x, p.y, p.vx, p.vy, p.life, p.max_life, p.size) for p in self._particles]
        results = batch_update_particles(particle_data, dt)
        original_particles = self._particles
        self._particles = []
        for i, (result, original_max_life) in enumerate(zip(results, max_lives, strict=False)):
            x, y, vx, vy, life, size, is_alive = result
            if is_alive:
                self._particles.append(self._acquire_particle(x, y, vx, vy, life, original_max_life, size))
            else:
                self._particle_pool.append(original_particles[i])

        # Sparks and debris still use Python update (different damping per type).
        for i in range(len(self._sparks) - 1, -1, -1):
            self._sparks[i].update(dt)
            if not self._sparks[i].is_alive():
                self._particle_pool.append(self._sparks.pop(i))

        for i in range(len(self._debris) - 1, -1, -1):
            self._debris[i].update(dt)
            if not self._debris[i].is_alive():
                self._particle_pool.append(self._debris.pop(i))

        self._shockwave_radius += 4.0 * dt
        self._core_flash = max(0.0, self._core_flash - 0.22 * dt)
        decay_rate = 0.03 if not self._particles else 0.015
        self._central_glow = max(0.0, self._central_glow - decay_rate * dt)

        if not self._particles and not self._sparks and not self._debris:
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

        self._render_central_glow(surface)
        self._render_core_flash(surface)
        self._render_shockwave(surface)
        self._render_debris(surface)
        self._render_particles(surface)
        self._render_sparks(surface)

    def _render_central_glow(self, surface: pygame.Surface) -> None:
        """Render central glow core using direct draw.

        Uses pygame.draw.circle instead of cached textures to avoid
        set_alpha() mutation on shared cached surfaces.
        """
        if self._central_glow <= 0.01:
            return

        glow_radius = int(self._radius * 0.8 * self._central_glow)
        if glow_radius < 2:
            return

        alpha = int(self.CENTRAL_GLOW_ALPHA_MAX * self._central_glow)
        center = (int(self._x), int(self._y))
        # Draw concentric circles for soft glow effect
        for i in range(glow_radius, 0, -max(1, glow_radius // 6)):
            layer_alpha = int(alpha * (i / glow_radius) * 0.7)
            if layer_alpha > 0:
                pygame.draw.circle(surface, (255, 120, 20, layer_alpha), center, i)

    def _render_core_flash(self, surface: pygame.Surface) -> None:
        """Render bright flash at explosion center.

        Uses direct draw calls instead of cached+copied surfaces to avoid
        per-frame Surface allocation (~10 copies/frame with 10 explosions).
        """
        if self._core_flash <= 0.01:
            return

        flash_radius = int(12 * self._core_flash)
        if flash_radius < 1:
            return

        center = (int(self._x), int(self._y))
        alpha = int(self.CORE_FLASH_ALPHA_MAX * self._core_flash)
        draw_radius = flash_radius * 2

        # Outer glow — direct draw avoids Surface.copy() + set_alpha()
        pygame.draw.circle(surface, (255, 255, 200, alpha), center, draw_radius)
        # Inner bright core
        inner_alpha = min(255, alpha + 60)
        pygame.draw.circle(surface, (255, 255, 255, inner_alpha), center, max(1, draw_radius // 2))

    def _render_shockwave(self, surface: pygame.Surface) -> None:
        """Render expanding shockwave ring"""
        if self._shockwave_radius <= 0:
            return

        progress = self._shockwave_radius / self._shockwave_max_radius
        if progress > 1.0:
            return

        alpha = int(self.SHOCKWAVE_ALPHA_MAX * (1.0 - progress))
        if alpha < 5:
            return

        thickness = max(1, int(3 * (1.0 - progress * 0.5)))

        pygame.draw.circle(
            surface, (255, 150, 50, alpha), (int(self._x), int(self._y)), int(self._shockwave_radius), thickness
        )

        inner_alpha = int(28 * (1.0 - progress))
        if inner_alpha > 10:
            pygame.draw.circle(
                surface,
                (255, 200, 100, inner_alpha),
                (int(self._x), int(self._y)),
                int(self._shockwave_radius * 0.7),
                max(1, thickness - 1),
            )

    def _render_debris(self, surface: pygame.Surface) -> None:
        """Render debris particles"""
        for particle in self._debris:
            self._render_debris_particle(surface, particle)

    def _render_debris_particle(self, surface: pygame.Surface, particle: ExplosionParticle) -> None:
        """Render a debris particle with trail effect.

        Uses direct draw calls instead of cached+set_alpha surfaces to avoid
        cache corruption (set_alpha mutates the cached surface in-place).
        """
        alpha = min(self.PARTICLE_ALPHA_MAX, particle.get_alpha())
        if alpha < GAME_CONSTANTS.ANIMATION.PARTICLE_ALPHA_VISIBILITY_THRESHOLD:
            return

        life_ratio = particle.life / particle.max_life
        gray = int(180 * life_ratio)
        color = (gray + 50, gray + 30, gray)
        size = max(1, int(particle.size * (alpha / 255)))

        # Trail dots
        for i in range(2):
            trail_alpha = int(alpha * (1.0 - i / 3) * 0.5)
            trail_size = max(1, size - i)
            trail_x = int(particle.x - particle.vx * i * 0.3)
            trail_y = int(particle.y - particle.vy * i * 0.3)
            if trail_alpha > 10:
                pygame.draw.circle(surface, (*color, trail_alpha), (trail_x, trail_y), trail_size)

        # Main debris dot
        pygame.draw.circle(surface, (*color, alpha), (int(particle.x), int(particle.y)), size)

    def _render_particles(self, surface: pygame.Surface) -> None:
        """Render main explosion particles with glow — batched via Rust."""
        if not self._particles:
            return

        # Render each particle individually using cached textures.
        # This avoids allocating a full-screen RGBA buffer (~8 MB at 1920×1080)
        # per explosion per frame — the previous batch_render_particles approach
        # was the single largest performance bottleneck.
        for particle in self._particles:
            self._render_main_particle(surface, particle)

    def _render_main_particle(self, surface: pygame.Surface, particle: ExplosionParticle) -> None:
        """Render a main particle with soft glow — uses cached textures."""
        alpha = min(self.PARTICLE_ALPHA_MAX, particle.get_alpha())
        if alpha < GAME_CONSTANTS.ANIMATION.PARTICLE_ALPHA_VISIBILITY_THRESHOLD:
            return

        color = particle.get_color()
        size = max(1, int(particle.size * (alpha / 255)))
        px, py = int(particle.x), int(particle.y)

        # Soft glow — direct draw avoids set_alpha() cache pollution
        glow_radius = size * 3
        if glow_radius >= 4:
            for i in range(glow_radius, 0, -max(1, glow_radius // 4)):
                layer_alpha = int(alpha * (i / glow_radius) * 0.08)
                if layer_alpha > 0:
                    pygame.draw.circle(surface, (*color, layer_alpha), (px, py), i)

        # Core dot
        pygame.draw.circle(surface, (*color, alpha), (px, py), size)

        # Bright inner core
        inner_size = max(1, size // 2)
        bright_alpha = min(255, alpha + self.INNER_CORE_ALPHA_BONUS)
        pygame.draw.circle(surface, (255, 255, 255, bright_alpha), (px, py), inner_size)

    def _render_sparks(self, surface: pygame.Surface) -> None:
        """Render fast spark particles"""
        for spark in self._sparks:
            self._render_spark_particle(surface, spark)

    def _render_spark_particle(self, surface: pygame.Surface, particle: ExplosionParticle) -> None:
        """Render a spark particle using direct draw to avoid cache pollution."""
        alpha = min(self.PARTICLE_ALPHA_MAX, particle.get_alpha())
        if alpha < GAME_CONSTANTS.ANIMATION.PARTICLE_ALPHA_VISIBILITY_THRESHOLD:
            return

        core_size = max(1, int(particle.size))
        color = particle.get_color()
        pygame.draw.circle(surface, (*color, alpha), (int(particle.x), int(particle.y)), core_size)

    def reset(self) -> None:
        """Reset effect instance (called before returning to pool)"""
        # Pool alive particles for reuse instead of discarding them
        for p in self._particles:
            p.life = 0
            self._particle_pool.append(p)
        for s in self._sparks:
            s.life = 0
            self._particle_pool.append(s)
        for d in self._debris:
            d.life = 0
            self._particle_pool.append(d)
        self._particles.clear()
        self._sparks.clear()
        self._debris.clear()
        self._active = False
        self._x = 0.0
        self._y = 0.0
        self._radius = 0
        self._glow_surf_cache = None
        self._glow_surf_size = 0
        self._shockwave_radius = 0
        self._shockwave_max_radius = 0
        self._core_flash = 0.0
        self._central_glow = 0.0

    def is_active(self) -> bool:
        """Check if explosion effect is active"""
        return self._active
