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


def draw_bullet(surface: pygame.Surface, x: float, y: float, width: float = 8, height: float = 16, bullet_type: str = "single", owner: str = "player") -> None:
    if bullet_type == "spread" or bullet_type == "spread_laser":
        draw_spread_bullet(surface, x, y, width, height, owner)
    elif bullet_type == "laser":
        draw_laser_bullet(surface, x, y, width, height, owner)
    else:
        draw_single_bullet(surface, x, y, width, height, owner)


def draw_single_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float, owner: str = "player") -> None:
    center_x = x + width / 2
    top_y = y
    if owner == "enemy":
        # Enemy bullets: bright magenta/pink - more visible
        glow_color = (255, 100, 200, 50)
        bullet_color = (255, 150, 220)
        core_color = (255, 220, 255)
        # Larger enemy bullet for visibility
        ew, eh = int(width * 1.4), int(height * 1.3)
        ex = center_x - ew / 2
        ey = top_y
    else:
        glow_color = (255, 200, 50, 30)
        bullet_color = (255, 220, 50)
        core_color = None
        ew, eh = width, height
        ex, ey = x, y

    cache_key = (int(ew), int(eh), owner)
    if cache_key not in _single_bullet_glow_cache:
        if RUST_AVAILABLE and create_single_bullet_glow:
            data = create_single_bullet_glow(ew, eh)
            surf_w = int(ew + 20)
            surf_h = int(eh + 16)
            glow = _bytes_to_surface(data, surf_w, surf_h)
        else:
            glow = pygame.Surface((int(ew + 20), int(eh + 16)), pygame.SRCALPHA)
            for i in range(8, 0, -1):
                alpha = 40 * (8 - i) // 7
                color = glow_color[:3] + (alpha,)
                pygame.draw.ellipse(glow, color, (10 - i, 5 - i // 2, int(ew) + i * 2 - 10, int(eh) + i - 4))
        _single_bullet_glow_cache[cache_key] = glow
    else:
        glow = _single_bullet_glow_cache[cache_key]

    if owner == "enemy":
        surface.blit(glow, (int(center_x - ew / 2 - 10), int(top_y - 5)))
        # Draw larger diamond shape for enemy
        points = [
            (center_x, top_y),
            (center_x + ew * 0.5, top_y + eh * 0.4),
            (center_x, top_y + eh),
            (center_x - ew * 0.5, top_y + eh * 0.4),
        ]
        pygame.draw.polygon(surface, bullet_color, points)
        # Bright core
        core_points = [
            (center_x, top_y + eh * 0.15),
            (center_x + ew * 0.2, top_y + eh * 0.45),
            (center_x, top_y + eh * 0.7),
            (center_x - ew * 0.2, top_y + eh * 0.45),
        ]
        pygame.draw.polygon(surface, core_color, core_points)
    else:
        surface.blit(glow, (int(x - 8), int(top_y - 4)))
        points = [
            (center_x, top_y),
            (x + width, y + height * 0.3),
            (center_x, y + height),
            (x, y + height * 0.3),
        ]
        pygame.draw.polygon(surface, bullet_color, points)


def draw_spread_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float, owner: str = "player") -> None:
    center = (int(x + width / 2), int(y + height / 2))
    radius = int(width / 2)
    # Player bullets: orange/yellow, Enemy bullets: purple/magenta
    if owner == "enemy":
        glow_color = (200, 100, 255, 40)
        outer_color = (200, 120, 255)
        inner_color = (230, 180, 255)
    else:
        glow_color = (255, 150, 50, 40)
        outer_color = (255, 180, 80)
        inner_color = (255, 220, 150)
    cache_key = (radius, owner)
    if cache_key not in _spread_bullet_glow_cache:
        if RUST_AVAILABLE and create_spread_bullet_glow:
            data = create_spread_bullet_glow(float(radius))
            surf_size = radius * 4 + 8
            glow = _bytes_to_surface(data, surf_size, surf_size)
        else:
            glow = pygame.Surface((radius * 4 + 8, radius * 4 + 8), pygame.SRCALPHA)
            for i in range(radius + 4, 0, -2):
                alpha = 40 * (radius + 4 - i) // (radius + 4)
                color = glow_color[:3] + (alpha,)
                pygame.draw.circle(glow, color, (radius * 2 + 4, radius * 2 + 4), i)
        _spread_bullet_glow_cache[cache_key] = glow
    else:
        glow = _spread_bullet_glow_cache[cache_key]
    surface.blit(glow, (center[0] - radius * 2 - 4, center[1] - radius * 2 - 4))
    pygame.draw.circle(surface, outer_color, center, radius + 2)
    pygame.draw.circle(surface, inner_color, center, radius)


def draw_laser_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float, owner: str = "player") -> None:
    center_x = x + width / 2
    # Player: red/orange laser, Enemy: green laser for distinction
    if owner == "enemy":
        glow_line_color = (20, 255, 100, 70)
        outer_color = (30, 200, 80)
        inner_color = (80, 255, 150)
        core_color = (200, 255, 220)
    else:
        glow_line_color = (255, 20, 40, 70)
        outer_color = (255, 30, 60)
        inner_color = (255, 80, 120)
        core_color = (255, 255, 255)
    cache_key = (int(height), owner)
    if cache_key not in _laser_bullet_glow_cache:
        if RUST_AVAILABLE and create_laser_bullet_glow:
            data = create_laser_bullet_glow(height)
            glow = _bytes_to_surface(data, 24, int(height) + 12)
        else:
            glow = pygame.Surface((24, int(height) + 12), pygame.SRCALPHA)
            for i in range(10, 0, -2):
                alpha = 70 * (10 - i) // 9
                color = glow_line_color[:3] + (alpha,)
                pygame.draw.line(glow, color, (12, 4), (12, int(height) + 8), i)
        _laser_bullet_glow_cache[cache_key] = glow
    else:
        glow = _laser_bullet_glow_cache[cache_key]
    surface.blit(glow, (int(center_x - 12), int(y - 4)))
    # Double outer glow for intensity
    pygame.draw.line(surface, outer_color, (center_x, y), (center_x, y + height), 6)
    pygame.draw.line(surface, inner_color, (center_x, y), (center_x, y + height), 4)
    # Bright white-hot core
    pygame.draw.line(surface, core_color, (center_x, y), (center_x, y + height), 2)


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
