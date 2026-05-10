"""UI particles — particle system for visual effects in the UI."""
from __future__ import annotations

import math
import random
from typing import Tuple

import pygame

from airwar.config.design_tokens import get_design_tokens


PARTICLE_TEXTURE_SIZES = (2, 3, 4, 6, 8, 12, 16, 20)


class ParticleSystem:
    """Particle system using Flyweight pattern for texture caching."""

    _texture_cache: dict[tuple[int, str], pygame.Surface] = {}

    def __init__(self) -> None:
        self._particles: list[dict] = []
        self._animation_time = 0
        self._tokens = get_design_tokens()
        self._init_cache()

    def _init_cache(self) -> None:
        """Pre-create particle textures for common sizes."""
        colors_config = self._tokens.colors
        for base_size in PARTICLE_TEXTURE_SIZES:
            for color_key in ['particle', 'particle_alt']:
                key = (base_size, color_key)
                if key not in self._texture_cache:
                    surf = pygame.Surface((base_size * 4, base_size * 4), pygame.SRCALPHA)
                    color = colors_config.PARTICLE_PRIMARY if color_key == 'particle' else colors_config.PARTICLE_ALT
                    for i in range(base_size * 2, 0, -2):
                        layer_alpha = int(180 * (base_size * 2 - i) / (base_size * 2) * 0.28)
                        pygame.draw.circle(
                            surf,
                            (*color, layer_alpha),
                            (base_size * 2, base_size * 2),
                            i
                        )
                    self._texture_cache[key] = surf

    def _init_particles(self, count: int = 40, color_key: str = 'particle') -> None:
        """Initialize particle data arrays."""
        self._particles = []
        animation_config = self._tokens.animation
        for _ in range(count):
            self._particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(animation_config.PARTICLE_SPEED_MIN, animation_config.PARTICLE_SPEED_MAX),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
                'color_key': color_key,
            })

    def update(self, direction: float = -1) -> None:
        """Update particle positions and lifetimes."""
        self._animation_time += 1
        for p in self._particles[:]:
            p['y'] += p['speed'] * 0.003 * direction
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)

    def render(self, surface: pygame.Surface, color: Tuple[int, int, int]) -> None:
        """Render all active particles to the given surface."""
        width, height = surface.get_size()

        for p in self._particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self._animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = round(p['size'] * (0.7 + 0.3 * pulse))
            size = max(1, min(size, 20))

            base_size = self._texture_size_for_particle(size)

            cache_key = (base_size, p.get('color_key', 'particle'))
            if cache_key in self._texture_cache:
                particle_surf = self._texture_cache[cache_key]
                particle_surf.set_alpha(alpha)
                surface.blit(particle_surf, (x - base_size * 2, y - base_size * 2))
            else:
                particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                for i in range(size * 2, 0, -2):
                    layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                    pygame.draw.circle(particle_surf, (*color, layer_alpha),
                                     (size * 2, size * 2), i)
                surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def reset(self, count: int = 40, color_key: str = 'particle') -> None:
        """Reset particle system with fresh particle data."""
        self._animation_time = 0
        self._init_particles(count, color_key)

    @staticmethod
    def _texture_size_for_particle(size: int) -> int:
        for texture_size in PARTICLE_TEXTURE_SIZES:
            if size <= texture_size:
                return texture_size
        return PARTICLE_TEXTURE_SIZES[-1]
