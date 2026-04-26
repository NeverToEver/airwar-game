"""Shared sprite utilities — caches, glow effects, gradients, and ripples."""
import pygame
import math

# Try to import Rust sprite functions
try:
    from airwar.core_bindings import (
        create_single_bullet_glow,
        create_spread_bullet_glow,
        create_laser_bullet_glow,
        create_explosive_missile_glow,
        create_glow_circle,
        RUST_AVAILABLE,
    )
except ImportError:
    create_single_bullet_glow = None
    create_spread_bullet_glow = None
    create_laser_bullet_glow = None
    create_explosive_missile_glow = None
    create_glow_circle = None
    RUST_AVAILABLE = False

# Glow caches shared across modules
_glow_circle_cache = {}
_single_bullet_glow_cache = {}
_spread_bullet_glow_cache = {}
_laser_bullet_glow_cache = {}
_ripple_surface_cache = {}
_explosive_missile_cache = {}


def _bytes_to_surface(data: bytes, width: int, height: int) -> pygame.Surface:
    """Convert RGBA bytes to pygame Surface."""
    surf = pygame.image.frombuffer(bytes(data), (width, height), 'RGBA')
    return surf.convert_alpha()


def prewarm_glow_caches() -> None:
    """Pre-generate all glow surfaces at startup to eliminate cache misses during gameplay."""
    if not RUST_AVAILABLE:
        return

    for width, height in [(8, 16), (6, 12), (10, 20), (4, 8)]:
        key = (width, height)
        if key not in _single_bullet_glow_cache:
            data = create_single_bullet_glow(float(width), float(height))
            surf_w = width + 16
            surf_h = height + 12
            _single_bullet_glow_cache[key] = _bytes_to_surface(data, surf_w, surf_h)

    for width in [8, 10, 12, 14, 16]:
        radius = width // 2
        key = (radius)
        if key not in _spread_bullet_glow_cache:
            data = create_spread_bullet_glow(float(radius))
            surf_size = radius * 4 + 8
            _spread_bullet_glow_cache[key] = _bytes_to_surface(data, surf_size, surf_size)

    for height in [16, 20, 24, 28, 32]:
        key = (height)
        if key not in _laser_bullet_glow_cache:
            data = create_laser_bullet_glow(float(height))
            _laser_bullet_glow_cache[key] = _bytes_to_surface(data, 24, height + 12)

    for width, height in [(10, 20), (8, 16), (12, 24)]:
        bw = int(width * 0.8)
        key = (bw, height)
        if key not in _explosive_missile_cache:
            data = create_explosive_missile_glow(float(width), float(height))
            surf_w = int(width * 0.8 * 3 + 12)
            surf_h = height + 10
            _explosive_missile_cache[key] = _bytes_to_surface(data, surf_w, surf_h)

    for radius, glow_radius in [(8, 8), (10, 10), (12, 12), (15, 15), (20, 15)]:
        key = (radius, (255, 100, 50), glow_radius)
        if key not in _glow_circle_cache:
            data = create_glow_circle(radius, 255, 100, 50, glow_radius)
            surf_size = (radius + glow_radius) * 2 + 4
            _glow_circle_cache[key] = _bytes_to_surface(data, surf_size, surf_size)


def create_gradient_surface(width: int, height: int, color1: tuple, color2: tuple, vertical: bool = True) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(height if vertical else width):
        ratio = i / (height if vertical else width)
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        color = (r, g, b, 255)
        if vertical:
            pygame.draw.line(surface, color, (0, i), (width, i))
        else:
            pygame.draw.line(surface, color, (i, 0), (i, height))
    return surface


def draw_glow_circle(surface: pygame.Surface, center: tuple, radius: int, color: tuple, glow_radius: int = 0) -> None:
    if glow_radius > 0:
        cache_key = (radius, color[:3], glow_radius)
        if cache_key not in _glow_circle_cache:
            glow_surf = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
            for i in range(glow_radius, 0, -2):
                alpha = int(80 * (1 - i / glow_radius))
                glow_color = (*color[:3], alpha)
                pygame.draw.circle(glow_surf, glow_color, (glow_radius + 2, glow_radius + 2), i)
            _glow_circle_cache[cache_key] = glow_surf
        else:
            glow_surf = _glow_circle_cache[cache_key]
        surface.blit(glow_surf, (center[0] - glow_radius - 2, center[1] - glow_radius - 2))
    pygame.draw.circle(surface, color, center, radius)


def draw_ripple(surface: pygame.Surface, x: float, y: float, radius: float, alpha: int, pulse: int = 0) -> None:
    if alpha <= 0:
        return

    surface_size = int(radius * 2 + 40)
    x_pos = int(x - surface_size // 2)
    y_pos = int(y - surface_size // 2)

    pulse_mod = pulse % 20
    phase_offset = pulse * 0.15
    cache_key = (surface_size, int(radius), alpha, pulse_mod)

    if cache_key not in _ripple_surface_cache:
        ripple_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
        center_offset = surface_size // 2

        ring_count = 5
        base_thickness = 2

        for i in range(ring_count):
            ring_radius = int(radius * (1 - i * 0.15))
            if ring_radius < 5:
                continue

            ring_phase = phase_offset + i * 0.8
            intensity = 0.5 + 0.5 * math.sin(ring_phase)
            ring_alpha = int(alpha * 0.5 * intensity)

            if ring_alpha < 15:
                continue

            thickness = max(1, base_thickness + int(intensity * 2))

            ring_color = (180, 220, 255, ring_alpha) if i % 2 == 0 else (220, 240, 255, ring_alpha)
            pygame.draw.circle(ripple_surface, ring_color, (center_offset, center_offset), ring_radius, thickness)

        interference_rings = 3
        for i in range(interference_rings):
            interference_radius = int(radius * (0.4 + i * 0.25))
            if interference_radius < 3:
                continue

            interference_phase = phase_offset * 1.5 + i * 1.2
            interference_intensity = abs(math.sin(interference_phase))
            interference_alpha = int(alpha * 0.3 * interference_intensity)
            if interference_alpha < 10:
                continue

            interference_thickness = 1 if interference_intensity < 0.3 else 2
            pygame.draw.circle(
                ripple_surface,
                (200, 235, 255, interference_alpha),
                (center_offset, center_offset),
                interference_radius,
                interference_thickness,
            )

        _ripple_surface_cache[cache_key] = ripple_surface
    else:
        ripple_surface = _ripple_surface_cache[cache_key]

    surface.blit(ripple_surface, (x_pos, y_pos))
