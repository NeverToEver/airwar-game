import pygame
import math
from functools import lru_cache

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

_glow_circle_cache = {}
_single_bullet_glow_cache = {}
_spread_bullet_glow_cache = {}
_laser_bullet_glow_cache = {}
_ripple_surface_cache = {}
_explosive_missile_cache = {}

# Sprite surface caches
_player_sprite_cache = {}
_enemy_sprite_cache = {}
_boss_sprite_cache = {}


def _bytes_to_surface(data: bytes, width: int, height: int) -> pygame.Surface:
    """Convert RGBA bytes to pygame Surface."""
    surf = pygame.image.frombuffer(bytes(data), (width, height), 'RGBA')
    return surf.convert_alpha()


def clear_sprite_caches() -> None:
    """Clear all sprite surface caches."""
    _player_sprite_cache.clear()
    _enemy_sprite_cache.clear()
    _boss_sprite_cache.clear()
    _glow_circle_cache.clear()
    _single_bullet_glow_cache.clear()
    _spread_bullet_glow_cache.clear()
    _laser_bullet_glow_cache.clear()
    _explosive_missile_cache.clear()
    _ripple_surface_cache.clear()


def prewarm_glow_caches() -> None:
    """Pre-generate all glow surfaces at startup to eliminate cache misses during gameplay.

    This is called once at game initialization to warm up the glow caches
    with all commonly used sizes, so no lazy creation happens during gameplay.
    """
    if not RUST_AVAILABLE:
        return

    # Single bullet glows: common player bullet sizes
    for width, height in [(8, 16), (6, 12), (10, 20), (4, 8)]:
        key = (width, height)
        if key not in _single_bullet_glow_cache:
            data = create_single_bullet_glow(float(width), float(height))
            surf_w = width + 16
            surf_h = height + 12
            _single_bullet_glow_cache[key] = _bytes_to_surface(data, surf_w, surf_h)

    # Spread bullet glows: common radii (radius = width/2 for spread bullets)
    for width in [8, 10, 12, 14, 16]:
        radius = width // 2
        key = (radius)
        if key not in _spread_bullet_glow_cache:
            data = create_spread_bullet_glow(float(radius))
            surf_size = radius * 4 + 8
            _spread_bullet_glow_cache[key] = _bytes_to_surface(data, surf_size, surf_size)

    # Laser bullet glows: common heights
    for height in [16, 20, 24, 28, 32]:
        key = (height)
        if key not in _laser_bullet_glow_cache:
            data = create_laser_bullet_glow(float(height))
            _laser_bullet_glow_cache[key] = _bytes_to_surface(data, 20, height + 8)

    # Explosive missile glows: common sizes
    for width, height in [(10, 20), (8, 16), (12, 24)]:
        # Note: bw is computed same as Rust (float arithmetic, not int truncation)
        bw = int(width * 0.8)  # used for cache key only
        key = (bw, height)
        if key not in _explosive_missile_cache:
            data = create_explosive_missile_glow(float(width), float(height))
            # Match Rust float arithmetic: surf_w = (width * 0.8 * 3 + 12) as usize
            surf_w = int(width * 0.8 * 3 + 12)
            surf_h = height + 10
            _explosive_missile_cache[key] = _bytes_to_surface(data, surf_w, surf_h)

    # Glow circles: enemy and player ship sizes
    # Enemy ships use glow_radius 5-15, player uses 8-12
    for radius, glow_radius in [(8, 8), (10, 10), (12, 12), (15, 15), (20, 15)]:
        key = (radius, (255, 100, 50), glow_radius)  # Enemy color
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
            # Always use pygame fallback for glow circles - the Rust version renders differently
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


def get_player_sprite(width: float = 50, height: float = 60) -> pygame.Surface:
    cache_key = (int(width), int(height))
    if cache_key not in _player_sprite_cache:
        # Extended size to account for wings extending beyond width
        extra = round(width * 0.55)
        surf = pygame.Surface((int(width) + extra * 2 + 4, int(height) + 4), pygame.SRCALPHA)
        _draw_player_ship(surf, extra + 2, 2, width, height)
        _player_sprite_cache[cache_key] = surf
    return _player_sprite_cache[cache_key]


def draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    extra = round(width * 0.55)
    sprite = get_player_sprite(width, height)
    surface.blit(sprite, (round(x) - extra - 2, round(y) - 2))


def _draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    """军事风格玩家战机 - 银灰/金色"""
    center_x = x + width / 2

    # 军事配色：银灰 + 琥珀金
    hull_dark = (45, 50, 60)
    hull_mid = (80, 90, 110)
    hull_light = (120, 135, 160)
    hull_highlight = (180, 195, 220)
    amber = (255, 180, 50)
    amber_glow = (255, 200, 80)

    # 左翼
    wing_left = [
        (center_x - width * 0.1, y + height * 0.08),
        (x - width * 0.5, y + height * 0.7),
        (x - width * 0.25, y + height * 0.78),
        (x - width * 0.08, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left)

    wing_left_mid = [
        (center_x - width * 0.1, y + height * 0.08),
        (x - width * 0.08, y + height * 0.55),
        (x + width * 0.05, y + height * 0.42),
        (center_x - width * 0.12, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_left_mid)

    wing_left_top = [
        (center_x - width * 0.12, y + height * 0.28),
        (x + width * 0.05, y + height * 0.42),
        (x + width * 0.15, y + height * 0.4),
        (center_x - width * 0.15, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, wing_left_top)

    # 右翼
    wing_right = [
        (center_x + width * 0.1, y + height * 0.08),
        (x + width + width * 0.5, y + height * 0.7),
        (x + width + width * 0.25, y + height * 0.78),
        (x + width + width * 0.08, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right)

    wing_right_mid = [
        (center_x + width * 0.1, y + height * 0.08),
        (x + width + width * 0.08, y + height * 0.55),
        (x + width - width * 0.05, y + height * 0.42),
        (center_x + width * 0.12, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_right_mid)

    wing_right_top = [
        (center_x + width * 0.12, y + height * 0.28),
        (x + width - width * 0.05, y + height * 0.42),
        (x + width - width * 0.15, y + height * 0.4),
        (center_x + width * 0.15, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, wing_right_top)

    # 机身主体
    body_base = [
        (center_x - width * 0.1, y + height * 0.32),
        (x + width * 0.1, y + height * 0.32),
        (x + width * 0.15, y + height * 0.68),
        (center_x, y + height * 0.88),
        (x + width * 0.85, y + height * 0.68),
        (x + width * 0.9, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_dark, body_base)

    body_mid = [
        (center_x - width * 0.06, y + height * 0.38),
        (x + width * 0.06, y + height * 0.38),
        (x + width * 0.1, y + height * 0.62),
        (center_x, y + height * 0.78),
        (x + width * 0.9, y + height * 0.62),
        (x + width * 0.94, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)

    body_top = [
        (center_x - width * 0.04, y + height * 0.4),
        (x + width * 0.04, y + height * 0.4),
        (x + width * 0.08, y + height * 0.58),
        (center_x, y + height * 0.68),
        (x + width * 0.92, y + height * 0.58),
        (x + width * 0.96, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)

    # 驾驶舱（金色高光）
    cockpit = [
        (center_x, y + height * 0.38),
        (center_x - width * 0.06, y + height * 0.48),
        (center_x, y + height * 0.55),
        (center_x + width * 0.06, y + height * 0.48),
    ]
    pygame.draw.polygon(surface, amber, cockpit)
    pygame.draw.polygon(surface, amber_glow, [
        (center_x, y + height * 0.4),
        (center_x - width * 0.03, y + height * 0.46),
        (center_x, y + height * 0.5),
        (center_x + width * 0.03, y + height * 0.46),
    ])

    # 引擎
    engine_left = [
        (center_x - width * 0.18, y + height * 0.7),
        (center_x - width * 0.25, y + height * 0.78),
        (center_x - width * 0.15, y + height * 0.82),
        (center_x - width * 0.1, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_left)

    engine_center_left = [
        (center_x - width * 0.1, y + height * 0.72),
        (center_x - width * 0.05, y + height * 0.82),
        (center_x, y + height * 0.78),
        (center_x + width * 0.02, y + height * 0.72),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_left)

    engine_center_right = [
        (center_x + width * 0.1, y + height * 0.72),
        (center_x + width * 0.05, y + height * 0.82),
        (center_x, y + height * 0.78),
        (center_x - width * 0.02, y + height * 0.72),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_right)

    engine_right = [
        (center_x + width * 0.18, y + height * 0.7),
        (center_x + width * 0.25, y + height * 0.78),
        (center_x + width * 0.15, y + height * 0.82),
        (center_x + width * 0.1, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_right)

    # 细节线条
    for i in range(3):
        line_y = y + height * 0.44 + i * height * 0.08
        pygame.draw.line(surface, hull_highlight, (center_x - width * 0.08, line_y), (center_x - width * 0.02, line_y), 1)
        pygame.draw.line(surface, hull_highlight, (center_x + width * 0.08, line_y), (center_x + width * 0.02, line_y), 1)

    # 机头
    nose = [
        (center_x, y),
        (center_x - width * 0.04, y + height * 0.12),
        (center_x + width * 0.04, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, hull_highlight, nose)


def get_enemy_sprite(width: float = 50, height: float = 50, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket)
    if cache_key not in _enemy_sprite_cache:
        extra = round(width * 0.3)
        surf = pygame.Surface((int(width) + extra * 2 + 4, int(height) + 4), pygame.SRCALPHA)
        _draw_enemy_ship(surf, extra + 2, 2, width, height, health_ratio)
        _enemy_sprite_cache[cache_key] = surf
    return _enemy_sprite_cache[cache_key]


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    extra = round(width * 0.3)
    sprite = get_enemy_sprite(width, height, health_ratio)
    surface.blit(sprite, (round(x) - extra - 2, round(y) - 2))


def _draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    """军事风格敌机 - 红色/橙色涂装"""
    center_x = x + width / 2

    if health_ratio > 0.6:
        # 正常状态：深红/橙
        body_dark = (80, 25, 25)
        body_mid = (140, 45, 35)
        body_light = (200, 80, 50)
        accent = (255, 100, 50)
        accent_glow = (255, 150, 80)
    elif health_ratio > 0.3:
        # 损伤状态：变暗
        body_dark = (70, 35, 30)
        body_mid = (120, 65, 45)
        body_light = (170, 110, 80)
        accent = (255, 140, 60)
        accent_glow = (255, 180, 100)
    else:
        # 重伤状态：变黄
        body_dark = (60, 45, 35)
        body_mid = (100, 80, 55)
        body_light = (150, 130, 90)
        accent = (255, 200, 50)
        accent_glow = (255, 230, 120)

    # 左翼（向下）
    wing_left = [
        (center_x - width * 0.1, y + height * 0.15),
        (x - width * 0.3, y + height * 0.65),
        (x - width * 0.1, y + height * 0.7),
        (x + width * 0.02, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_dark, wing_left)

    wing_left_top = [
        (center_x - width * 0.1, y + height * 0.15),
        (x + width * 0.02, y + height * 0.5),
        (x + width * 0.1, y + height * 0.45),
        (center_x - width * 0.08, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, body_mid, wing_left_top)

    # 右翼（向下）
    wing_right = [
        (center_x + width * 0.1, y + height * 0.15),
        (x + width + width * 0.3, y + height * 0.65),
        (x + width + width * 0.1, y + height * 0.7),
        (x + width - width * 0.02, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_dark, wing_right)

    wing_right_top = [
        (center_x + width * 0.1, y + height * 0.15),
        (x + width - width * 0.02, y + height * 0.5),
        (x + width - width * 0.1, y + height * 0.45),
        (center_x + width * 0.08, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, body_mid, wing_right_top)

    # 主机身（倒梯形，尖头向下）
    main_body = [
        (center_x, y + height + height * 0.08),
        (x + width * 0.88, y + height * 0.4),
        (x + width * 0.72, y + height * 0.1),
        (center_x, y + height * 0.02),
        (x + width * 0.28, y + height * 0.1),
        (x + width * 0.12, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, body_dark, main_body)

    body_upper = [
        (center_x, y + height * 0.72),
        (x + width * 0.78, y + height * 0.42),
        (x + width * 0.65, y + height * 0.18),
        (center_x, y + height * 0.12),
        (x + width * 0.35, y + height * 0.18),
        (x + width * 0.22, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, body_mid, body_upper)

    body_top = [
        (center_x, y + height * 0.48),
        (x + width * 0.62, y + height * 0.28),
        (x + width * 0.52, y + height * 0.12),
        (center_x, y + height * 0.18),
        (x + width * 0.48, y + height * 0.12),
        (x + width * 0.38, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, body_light, body_top)

    # 红色识别标记（驾驶舱区域）
    cockpit = [
        (center_x, y + height * 0.35),
        (center_x - width * 0.08, y + height * 0.45),
        (center_x, y + height * 0.52),
        (center_x + width * 0.08, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, accent, cockpit)

    # 机头（向上，攻击方向）
    nose = [
        (center_x, y),
        (center_x - width * 0.05, y + height * 0.12),
        (center_x, y + height * 0.08),
        (center_x + width * 0.05, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, body_light, nose)

    # 引擎（背部）
    engine_left = [
        (center_x - width * 0.15, y + height * 0.55),
        (center_x - width * 0.22, y + height * 0.62),
        (center_x - width * 0.12, y + height * 0.65),
        (center_x - width * 0.08, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, body_dark, engine_left)

    engine_right = [
        (center_x + width * 0.15, y + height * 0.55),
        (center_x + width * 0.22, y + height * 0.62),
        (center_x + width * 0.12, y + height * 0.65),
        (center_x + width * 0.08, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, body_dark, engine_right)

    # 发光核心
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 10, accent, 20)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 5, accent_glow, 12)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 2, (255, 255, 200), 6)

    # 细节线条
    for i in range(4):
        line_y = y + height * 0.55 + i * height * 0.06
        line_start = center_x - width * 0.15
        line_end = center_x - width * 0.05
        pygame.draw.line(surface, body_light, (line_start, line_y), (line_end, line_y), 1)
        pygame.draw.line(surface, body_light, (center_x + width * 0.15, line_y), (center_x + width * 0.05, line_y), 1)


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
            glow = _bytes_to_surface(data, 20, int(height) + 8)
        else:
            glow = pygame.Surface((20, int(height) + 8), pygame.SRCALPHA)
            for i in range(8, 0, -2):
                alpha = 50 * (8 - i) // 7
                pygame.draw.line(glow, (255, 50, 150, alpha), (10, 2), (10, int(height) + 6), i)
        _laser_bullet_glow_cache[cache_key] = glow
    else:
        glow = _laser_bullet_glow_cache[cache_key]
    surface.blit(glow, (int(center_x - 10), int(y - 2)))
    pygame.draw.line(surface, (255, 100, 200), (center_x, y), (center_x, y + height), 4)
    pygame.draw.line(surface, (255, 220, 240), (center_x, y), (center_x, y + height), 2)


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

    # Flame trail at top (since bullet travels upward)
    flame_h = int(height * 0.25)
    flame_w = int(width * 0.45)
    flame_y = ty
    flame_points = [
        (cx, flame_y - flame_h),
        (cx - flame_w, flame_y + flame_h),
        (cx + flame_w, flame_y + flame_h),
    ]
    pygame.draw.polygon(surface, (255, 200, 30), flame_points)
    pygame.draw.polygon(surface, (255, 255, 150), [(cx, flame_y - flame_h + 2), (cx - flame_w + 3, flame_y + flame_h - 1), (cx + flame_w - 3, flame_y + flame_h - 1)])

    # Body (cylinder)
    body_top = ty + flame_h
    body_rect = pygame.Rect(cx - bw_half, body_top, bw, bh)
    pygame.draw.rect(surface, (200, 80, 20), body_rect)
    pygame.draw.rect(surface, (255, 130, 40), pygame.Rect(cx - bw_half + 2, body_top + 2, bw - 4, bh - 4))

    # Nose cone at bottom (pointing forward = upward since bullet travels up)
    nose_base_y = body_top + bh
    nose_points = [
        (cx, nose_base_y + nh),                      # tip at bottom
        (cx - nw_half, nose_base_y),                 # top left
        (cx + nw_half, nose_base_y),                 # top right
    ]
    pygame.draw.polygon(surface, (255, 60, 10), nose_points)
    pygame.draw.polygon(surface, (255, 140, 60), [(cx, nose_base_y + nh - 2), (cx - nw_half + 3, nose_base_y + 1), (cx + nw_half - 3, nose_base_y + 1)])

    # Fins at the back (bottom of missile)
    fin_h = int(height * 0.2)
    fin_w = int(width * 0.35)
    fin_y = nose_base_y
    pygame.draw.polygon(surface, (180, 60, 10), [(cx - bw_half, fin_y), (cx - bw_half - fin_w, fin_y - fin_h), (cx - bw_half, fin_y - fin_h)])
    pygame.draw.polygon(surface, (180, 60, 10), [(cx + bw_half, fin_y), (cx + bw_half + fin_w, fin_y - fin_h), (cx + bw_half, fin_y - fin_h)])


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

            if i % 2 == 0:
                ring_color = (180, 220, 255, ring_alpha)
            else:
                ring_color = (220, 240, 255, ring_alpha)

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
                interference_thickness
            )

        _ripple_surface_cache[cache_key] = ripple_surface
    else:
        ripple_surface = _ripple_surface_cache[cache_key]

    surface.blit(ripple_surface, (x_pos, y_pos))


def get_boss_sprite(width: float = 120, height: float = 100, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket)
    if cache_key not in _boss_sprite_cache:
        extra = round(width * 0.15)
        surf = pygame.Surface((int(width) + extra * 2 + 4, int(height) + 20), pygame.SRCALPHA)
        _draw_boss_ship(surf, extra + 2, 2, width, height, health_ratio)
        _boss_sprite_cache[cache_key] = surf
    return _boss_sprite_cache[cache_key]


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    extra = round(width * 0.15)
    sprite = get_boss_sprite(width, height, health_ratio)
    surface.blit(sprite, (round(x) - extra - 2, round(y) - 2))


def _draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    """军事风格Boss - 大型红色/橙色战机"""
    center_x = x + width / 2

    if health_ratio > 0.6:
        # 正常状态
        hull_dark = (70, 20, 20)
        hull_mid = (130, 40, 30)
        hull_light = (190, 70, 45)
        accent = (255, 80, 40)
        accent_glow = (255, 130, 80)
        detail = (255, 180, 80)
    elif health_ratio > 0.3:
        # 损伤状态
        hull_dark = (65, 35, 25)
        hull_mid = (115, 65, 40)
        hull_light = (170, 110, 70)
        accent = (255, 130, 50)
        accent_glow = (255, 170, 100)
        detail = (255, 200, 100)
    else:
        # 重伤状态
        hull_dark = (60, 45, 30)
        hull_mid = (100, 80, 50)
        hull_light = (150, 130, 90)
        accent = (255, 190, 50)
        accent_glow = (255, 220, 120)
        detail = (255, 240, 150)

    # 大型左右翼
    wing_left_outer = [
        (center_x - width * 0.12, y + height * 0.2),
        (x - width * 0.25, y + height * 0.75),
        (x - width * 0.05, y + height * 0.85),
        (center_x - width * 0.08, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left_outer)

    wing_left_inner = [
        (center_x - width * 0.1, y + height * 0.25),
        (x - width * 0.12, y + height * 0.7),
        (x + width * 0.02, y + height * 0.65),
        (center_x - width * 0.06, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_left_inner)

    wing_right_outer = [
        (center_x + width * 0.12, y + height * 0.2),
        (x + width + width * 0.25, y + height * 0.75),
        (x + width + width * 0.05, y + height * 0.85),
        (center_x + width * 0.08, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right_outer)

    wing_right_inner = [
        (center_x + width * 0.1, y + height * 0.25),
        (x + width + width * 0.12, y + height * 0.7),
        (x + width - width * 0.02, y + height * 0.65),
        (center_x + width * 0.06, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_right_inner)

    # 主机身（菱形主体）
    main_body = [
        (center_x, y + height * 0.05),
        (x + width * 0.88, y + height * 0.38),
        (x + width * 0.92, y + height * 0.68),
        (center_x, y + height * 0.95),
        (x + width * 0.08, y + height * 0.68),
        (x + width * 0.12, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_dark, main_body)

    body_mid = [
        (center_x, y + height * 0.15),
        (x + width * 0.78, y + height * 0.4),
        (x + width * 0.82, y + height * 0.62),
        (center_x, y + height * 0.85),
        (x + width * 0.18, y + height * 0.62),
        (x + width * 0.22, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)

    body_top = [
        (center_x, y + height * 0.12),
        (x + width * 0.72, y + height * 0.32),
        (x + width * 0.78, y + height * 0.55),
        (center_x, y + height * 0.75),
        (x + width * 0.22, y + height * 0.55),
        (x + width * 0.28, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)

    # 驾驶舱/武器舱（琥珀色）
    cockpit = [
        (center_x, y + height * 0.28),
        (center_x - width * 0.12, y + height * 0.42),
        (center_x, y + height * 0.52),
        (center_x + width * 0.12, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, accent, cockpit)

    # 引擎组（背部）
    engine_1 = [
        (center_x - width * 0.25, y + height * 0.55),
        (center_x - width * 0.35, y + height * 0.68),
        (center_x - width * 0.22, y + height * 0.72),
        (center_x - width * 0.15, y + height * 0.62),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_1)

    engine_2 = [
        (center_x + width * 0.25, y + height * 0.55),
        (center_x + width * 0.35, y + height * 0.68),
        (center_x + width * 0.22, y + height * 0.72),
        (center_x + width * 0.15, y + height * 0.62),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_2)

    engine_3 = [
        (center_x - width * 0.08, y + height * 0.6),
        (center_x - width * 0.12, y + height * 0.72),
        (center_x, y + height * 0.75),
        (center_x + width * 0.08, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_3)

    # 机头（尖锐向上）
    nose = [
        (center_x, y - height * 0.08),
        (center_x - width * 0.08, y + height * 0.1),
        (center_x, y + height * 0.08),
        (center_x + width * 0.08, y + height * 0.1),
    ]
    pygame.draw.polygon(surface, hull_light, nose)

    # 侧翼尖刺
    spike_left = [
        (x - width * 0.2, y + height * 0.35),
        (x - width * 0.35, y + height * 0.25),
        (x - width * 0.1, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, spike_left)

    spike_right = [
        (x + width + width * 0.2, y + height * 0.35),
        (x + width + width * 0.35, y + height * 0.25),
        (x + width + width * 0.1, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, spike_right)

    # 发光核心
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.38)), 18, accent, 38)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.38)), 10, accent_glow, 24)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.38)), 4, detail, 14)

    # 细节线条
    for i in range(5):
        line_y = y + height * 0.42 + i * height * 0.08
        line_start = center_x - width * 0.2
        line_end = center_x + width * 0.2
        pygame.draw.line(surface, hull_light, (line_start, line_y), (line_end, line_y), 2)
