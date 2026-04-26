"""Bullet sprite rendering — single, spread, laser, and explosive missile."""
import pygame
from ._sprites_common import (
    _bytes_to_surface,
    _single_bullet_glow_cache,
    _spread_bullet_glow_cache,
    _laser_bullet_glow_cache,
    _explosive_missile_cache,
    RUST_AVAILABLE,
    create_single_bullet_glow,
    create_spread_bullet_glow,
    create_laser_bullet_glow,
    create_explosive_missile_glow,
)


def draw_bullet(surface: pygame.Surface, x: float, y: float, width: float = 8, height: float = 16, bullet_type: str = "single") -> None:
    if bullet_type == "spread" or bullet_type == "spread_laser":
        draw_spread_bullet(surface, x, y, width, height)
    elif bullet_type == "laser":
        draw_laser_bullet(surface, x, y, width, height)
    else:
        draw_single_bullet(surface, x, y, width, height)


def draw_single_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center_x = x + width / 2
    top_y = y
    cache_key = (int(width), int(height))
    if cache_key not in _single_bullet_glow_cache:
        if RUST_AVAILABLE and create_single_bullet_glow:
            data = create_single_bullet_glow(width, height)
            surf_w = int(width + 16)
            surf_h = int(height + 12)
            glow = _bytes_to_surface(data, surf_w, surf_h)
        else:
            glow = pygame.Surface((int(width + 16), int(height + 12)), pygame.SRCALPHA)
            for i in range(6, 0, -1):
                alpha = 30 * (6 - i) // 5
                glow_color = (255, 200, 50, alpha)
                pygame.draw.ellipse(glow, glow_color, (8 - i, 4 - i // 2, int(width) + i * 2 - 6, int(height) + i - 2))
        _single_bullet_glow_cache[cache_key] = glow
    else:
        glow = _single_bullet_glow_cache[cache_key]
    surface.blit(glow, (int(x - 8), int(top_y - 4)))

    points = [
        (center_x, top_y),
        (x + width, y + height * 0.3),
        (center_x, y + height),
        (x, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, (255, 220, 50), points)


def draw_spread_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center = (int(x + width / 2), int(y + height / 2))
    radius = int(width / 2)
    cache_key = (radius)
    if cache_key not in _spread_bullet_glow_cache:
        if RUST_AVAILABLE and create_spread_bullet_glow:
            data = create_spread_bullet_glow(float(radius))
            surf_size = radius * 4 + 8
            glow = _bytes_to_surface(data, surf_size, surf_size)
        else:
            glow = pygame.Surface((radius * 4 + 8, radius * 4 + 8), pygame.SRCALPHA)
            for i in range(radius + 4, 0, -2):
                alpha = 40 * (radius + 4 - i) // (radius + 4)
                pygame.draw.circle(glow, (255, 150, 50, alpha), (radius * 2 + 4, radius * 2 + 4), i)
        _spread_bullet_glow_cache[cache_key] = glow
    else:
        glow = _spread_bullet_glow_cache[cache_key]
    surface.blit(glow, (center[0] - radius * 2 - 4, center[1] - radius * 2 - 4))
    pygame.draw.circle(surface, (255, 180, 80), center, radius + 2)
    pygame.draw.circle(surface, (255, 220, 150), center, radius)


def draw_laser_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center_x = x + width / 2
    cache_key = (int(height))
    if cache_key not in _laser_bullet_glow_cache:
        if RUST_AVAILABLE and create_laser_bullet_glow:
            data = create_laser_bullet_glow(height)
            glow = _bytes_to_surface(data, 24, int(height) + 12)
        else:
            glow = pygame.Surface((24, int(height) + 12), pygame.SRCALPHA)
            for i in range(10, 0, -2):
                alpha = 70 * (10 - i) // 9
                pygame.draw.line(glow, (255, 20, 40, alpha), (12, 4), (12, int(height) + 8), i)
        _laser_bullet_glow_cache[cache_key] = glow
    else:
        glow = _laser_bullet_glow_cache[cache_key]
    surface.blit(glow, (int(center_x - 12), int(y - 4)))
    # Double outer glow for intensity
    pygame.draw.line(surface, (255, 30, 60), (center_x, y), (center_x, y + height), 6)
    pygame.draw.line(surface, (255, 80, 120), (center_x, y), (center_x, y + height), 4)
    # Bright white-hot core
    pygame.draw.line(surface, (255, 255, 255), (center_x, y), (center_x, y + height), 2)


def draw_explosive_missile(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    """Draw a small missile projectile pointing upward (direction of travel)."""
    cx = int(x + width / 2)
    ty = int(y)
    bh = int(height * 0.55)
    nh = int(height * 0.25)
    bw = int(width * 0.8)
    nw = int(width * 0.5)
    bw_half = bw // 2
    nw_half = nw // 2

    cache_key = (bw, int(height))
    if cache_key not in _explosive_missile_cache:
        if RUST_AVAILABLE and create_explosive_missile_glow:
            data = create_explosive_missile_glow(width, height)
            surf_w = bw * 3 + 12
            surf_h = int(height) + 10
            glow_surf = _bytes_to_surface(data, surf_w, surf_h)
        else:
            glow_surf = pygame.Surface((bw * 3 + 12, int(height) + 10), pygame.SRCALPHA)
            for i in range(6, 0, -1):
                alpha = 35 * (6 - i) // 5
                pygame.draw.ellipse(glow_surf, (255, 80, 20, alpha),
                                    (bw + 6 - i * 2, 2 - i, int(height) + i * 2, int(height) + i * 2))
        _explosive_missile_cache[cache_key] = glow_surf
    else:
        glow_surf = _explosive_missile_cache[cache_key]

    surface.blit(glow_surf, (cx - bw - 6, ty - 2))

    # Flame trail
    flame_h = int(height * 0.25)
    flame_w = int(width * 0.45)
    flame_y = ty
    flame_points = [(cx, flame_y - flame_h), (cx - flame_w, flame_y + flame_h), (cx + flame_w, flame_y + flame_h)]
    pygame.draw.polygon(surface, (255, 200, 30), flame_points)
    pygame.draw.polygon(surface, (255, 255, 150), [(cx, flame_y - flame_h + 2), (cx - flame_w + 3, flame_y + flame_h - 1), (cx + flame_w - 3, flame_y + flame_h - 1)])

    # Body
    body_top = ty + flame_h
    body_rect = pygame.Rect(cx - bw_half, body_top, bw, bh)
    pygame.draw.rect(surface, (200, 80, 20), body_rect)
    pygame.draw.rect(surface, (255, 130, 40), pygame.Rect(cx - bw_half + 2, body_top + 2, bw - 4, bh - 4))

    # Nose cone
    nose_base_y = body_top + bh
    nose_points = [(cx, nose_base_y + nh), (cx - nw_half, nose_base_y), (cx + nw_half, nose_base_y)]
    pygame.draw.polygon(surface, (255, 60, 10), nose_points)
    pygame.draw.polygon(surface, (255, 140, 60), [(cx, nose_base_y + nh - 2), (cx - nw_half + 3, nose_base_y + 1), (cx + nw_half - 3, nose_base_y + 1)])

    # Fins
    fin_h = int(height * 0.2)
    fin_w = int(width * 0.35)
    fin_y = nose_base_y
    pygame.draw.polygon(surface, (180, 60, 10), [(cx - bw_half, fin_y), (cx - bw_half - fin_w, fin_y - fin_h), (cx - bw_half, fin_y - fin_h)])
    pygame.draw.polygon(surface, (180, 60, 10), [(cx + bw_half, fin_y), (cx + bw_half + fin_w, fin_y - fin_h), (cx + bw_half, fin_y - fin_h)])
