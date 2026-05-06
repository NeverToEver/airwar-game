"""Bullet sprite rendering — single, spread, laser, and explosive missile."""
import pygame
from ._sprites_common import (
    _bytes_to_surface,
    _single_bullet_glow_cache,
    _spread_bullet_glow_cache,
    _laser_bullet_glow_cache,
    _explosive_missile_cache,
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
    if owner == "player":
        # Player bullets: bright magenta/pink - more visible
        bullet_color = (255, 150, 220)
        core_color = (255, 220, 255)
        # Larger player bullet for visibility
        ew, eh = int(width * 1.4), int(height * 1.3)
    elif owner == "mothership":
        bullet_color = (75, 210, 245)
        core_color = (210, 250, 255)
        ew, eh = int(width * 1.2), int(height * 1.15)
    else:
        bullet_color = (255, 220, 50)
        core_color = None
        ew, eh = width, height

    cache_key = (int(ew), int(eh), owner)
    if cache_key not in _single_bullet_glow_cache:
        data = create_single_bullet_glow(float(ew), float(eh))
        surf_w = int(ew + 16)
        surf_h = int(eh + 12)
        glow = _bytes_to_surface(data, surf_w, surf_h)
        _single_bullet_glow_cache[cache_key] = glow
    else:
        glow = _single_bullet_glow_cache[cache_key]

    if owner == "player":
        surface.blit(glow, (int(center_x - ew / 2 - 10), int(top_y - 5)))
        # Draw larger diamond shape for player
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
    elif owner == "mothership":
        surface.blit(glow, (int(center_x - ew / 2 - 10), int(top_y - 5)))
        points = [
            (center_x, top_y),
            (center_x + ew * 0.35, top_y + eh * 0.22),
            (center_x + ew * 0.22, top_y + eh),
            (center_x - ew * 0.22, top_y + eh),
            (center_x - ew * 0.35, top_y + eh * 0.22),
        ]
        pygame.draw.polygon(surface, bullet_color, points)
        pygame.draw.line(surface, core_color, (center_x, top_y + 2), (center_x, top_y + eh - 2), 2)
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
    # Player bullets: purple/magenta, Enemy bullets: orange/yellow
    if owner == "player":
        outer_color = (200, 120, 255)
        inner_color = (230, 180, 255)
    else:
        outer_color = (255, 180, 80)
        inner_color = (255, 220, 150)
    cache_key = (radius, owner)
    if cache_key not in _spread_bullet_glow_cache:
        data = create_spread_bullet_glow(float(radius))
        surf_size = radius * 4 + 8
        glow = _bytes_to_surface(data, surf_size, surf_size)
        _spread_bullet_glow_cache[cache_key] = glow
    else:
        glow = _spread_bullet_glow_cache[cache_key]
    surface.blit(glow, (center[0] - radius * 2 - 4, center[1] - radius * 2 - 4))
    pygame.draw.circle(surface, outer_color, center, radius + 2)
    pygame.draw.circle(surface, inner_color, center, radius)


def draw_laser_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float, owner: str = "player") -> None:
    center_x = x + width / 2
    # Player: green laser, Enemy: red/orange laser for distinction
    if owner == "player":
        outer_color = (30, 200, 80)
        inner_color = (80, 255, 150)
        core_color = (200, 255, 220)
    else:
        outer_color = (255, 30, 60)
        inner_color = (255, 80, 120)
        core_color = (255, 255, 255)
    cache_key = (int(height), owner)
    if cache_key not in _laser_bullet_glow_cache:
        data = create_laser_bullet_glow(height)
        glow = _bytes_to_surface(data, 24, int(height) + 12)
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
        data = create_explosive_missile_glow(width, height)
        surf_w = bw * 3 + 12
        surf_h = int(height) + 10
        glow_surf = _bytes_to_surface(data, surf_w, surf_h)
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
