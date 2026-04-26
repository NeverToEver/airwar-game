"""Ship sprite rendering — player, enemy, and boss ships with caching."""
import pygame
from ._sprites_common import draw_glow_circle

# Sprite surface caches
_player_sprite_cache = {}
_enemy_sprite_cache = {}
_boss_sprite_cache = {}


# ─── Player ───────────────────────────────────────────────────────────────────

def get_player_sprite(width: float = 50, height: float = 60) -> pygame.Surface:
    cache_key = (int(width), int(height))
    if cache_key not in _player_sprite_cache:
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
    """Military-style player fighter — silver/grey with amber gold accents."""
    center_x = x + width / 2

    hull_dark = (45, 50, 60)
    hull_mid = (80, 90, 110)
    hull_light = (120, 135, 160)
    hull_highlight = (180, 195, 220)
    amber = (255, 180, 50)
    amber_glow = (255, 200, 80)

    # Left wing
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

    # Right wing
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

    # Body
    body_base = [
        (center_x - width * 0.1, y + height * 0.32), (x + width * 0.1, y + height * 0.32),
        (x + width * 0.15, y + height * 0.68), (center_x, y + height * 0.88),
        (x + width * 0.85, y + height * 0.68), (x + width * 0.9, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_dark, body_base)
    body_mid = [
        (center_x - width * 0.06, y + height * 0.38), (x + width * 0.06, y + height * 0.38),
        (x + width * 0.1, y + height * 0.62), (center_x, y + height * 0.78),
        (x + width * 0.9, y + height * 0.62), (x + width * 0.94, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)
    body_top = [
        (center_x - width * 0.04, y + height * 0.4), (x + width * 0.04, y + height * 0.4),
        (x + width * 0.08, y + height * 0.58), (center_x, y + height * 0.68),
        (x + width * 0.92, y + height * 0.58), (x + width * 0.96, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)

    # Cockpit
    cockpit = [
        (center_x, y + height * 0.38), (center_x - width * 0.06, y + height * 0.48),
        (center_x, y + height * 0.55), (center_x + width * 0.06, y + height * 0.48),
    ]
    pygame.draw.polygon(surface, amber, cockpit)
    pygame.draw.polygon(surface, amber_glow, [
        (center_x, y + height * 0.4), (center_x - width * 0.03, y + height * 0.46),
        (center_x, y + height * 0.5), (center_x + width * 0.03, y + height * 0.46),
    ])

    # Engines
    engine_left = [
        (center_x - width * 0.18, y + height * 0.7), (center_x - width * 0.25, y + height * 0.78),
        (center_x - width * 0.15, y + height * 0.82), (center_x - width * 0.1, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_left)
    engine_center_left = [
        (center_x - width * 0.1, y + height * 0.72), (center_x - width * 0.05, y + height * 0.82),
        (center_x, y + height * 0.78), (center_x + width * 0.02, y + height * 0.72),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_left)
    engine_center_right = [
        (center_x + width * 0.1, y + height * 0.72), (center_x + width * 0.05, y + height * 0.82),
        (center_x, y + height * 0.78), (center_x - width * 0.02, y + height * 0.72),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_right)
    engine_right = [
        (center_x + width * 0.18, y + height * 0.7), (center_x + width * 0.25, y + height * 0.78),
        (center_x + width * 0.15, y + height * 0.82), (center_x + width * 0.1, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_right)

    # Detail lines
    for i in range(3):
        line_y = y + height * 0.44 + i * height * 0.08
        pygame.draw.line(surface, hull_highlight, (center_x - width * 0.08, line_y), (center_x - width * 0.02, line_y), 1)
        pygame.draw.line(surface, hull_highlight, (center_x + width * 0.08, line_y), (center_x + width * 0.02, line_y), 1)

    # Nose
    nose = [
        (center_x, y), (center_x - width * 0.04, y + height * 0.12), (center_x + width * 0.04, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, hull_highlight, nose)


# ─── Enemy ────────────────────────────────────────────────────────────────────

def _enemy_colors(health_ratio):
    if health_ratio > 0.6:
        return (80, 25, 25), (140, 45, 35), (200, 80, 50), (255, 100, 50), (255, 150, 80)
    elif health_ratio > 0.3:
        return (70, 35, 30), (120, 65, 45), (170, 110, 80), (255, 140, 60), (255, 180, 100)
    else:
        return (60, 45, 35), (100, 80, 55), (150, 130, 90), (255, 200, 50), (255, 230, 120)


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
    """Military-style enemy — red/orange with health-based color shifts."""
    center_x = x + width / 2
    body_dark, body_mid, body_light, accent, accent_glow = _enemy_colors(health_ratio)

    # Left wing
    wing_left = [
        (center_x - width * 0.1, y + height * 0.15), (x - width * 0.3, y + height * 0.65),
        (x - width * 0.1, y + height * 0.7), (x + width * 0.02, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_dark, wing_left)
    wing_left_top = [
        (center_x - width * 0.1, y + height * 0.15), (x + width * 0.02, y + height * 0.5),
        (x + width * 0.1, y + height * 0.45), (center_x - width * 0.08, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, body_mid, wing_left_top)

    # Right wing
    wing_right = [
        (center_x + width * 0.1, y + height * 0.15), (x + width + width * 0.3, y + height * 0.65),
        (x + width + width * 0.1, y + height * 0.7), (x + width - width * 0.02, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_dark, wing_right)
    wing_right_top = [
        (center_x + width * 0.1, y + height * 0.15), (x + width - width * 0.02, y + height * 0.5),
        (x + width - width * 0.1, y + height * 0.45), (center_x + width * 0.08, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, body_mid, wing_right_top)

    # Main body
    main_body = [
        (center_x, y + height + height * 0.08), (x + width * 0.88, y + height * 0.4),
        (x + width * 0.72, y + height * 0.1), (center_x, y + height * 0.02),
        (x + width * 0.28, y + height * 0.1), (x + width * 0.12, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, body_dark, main_body)
    body_upper = [
        (center_x, y + height * 0.72), (x + width * 0.78, y + height * 0.42),
        (x + width * 0.65, y + height * 0.18), (center_x, y + height * 0.12),
        (x + width * 0.35, y + height * 0.18), (x + width * 0.22, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, body_mid, body_upper)
    body_top = [
        (center_x, y + height * 0.48), (x + width * 0.62, y + height * 0.28),
        (x + width * 0.52, y + height * 0.12), (center_x, y + height * 0.18),
        (x + width * 0.48, y + height * 0.12), (x + width * 0.38, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, body_light, body_top)

    # Cockpit
    cockpit = [
        (center_x, y + height * 0.35), (center_x - width * 0.08, y + height * 0.45),
        (center_x, y + height * 0.52), (center_x + width * 0.08, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, accent, cockpit)

    # Nose
    nose = [
        (center_x, y), (center_x - width * 0.05, y + height * 0.12),
        (center_x, y + height * 0.08), (center_x + width * 0.05, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, body_light, nose)

    # Engines
    engine_left = [
        (center_x - width * 0.15, y + height * 0.55), (center_x - width * 0.22, y + height * 0.62),
        (center_x - width * 0.12, y + height * 0.65), (center_x - width * 0.08, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, body_dark, engine_left)
    engine_right = [
        (center_x + width * 0.15, y + height * 0.55), (center_x + width * 0.22, y + height * 0.62),
        (center_x + width * 0.12, y + height * 0.65), (center_x + width * 0.08, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, body_dark, engine_right)

    # Glow core
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 10, accent, 20)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 5, accent_glow, 12)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 2, (255, 255, 200), 6)

    # Detail lines
    for i in range(4):
        line_y = y + height * 0.55 + i * height * 0.06
        line_start = center_x - width * 0.15
        line_end = center_x - width * 0.05
        pygame.draw.line(surface, body_light, (line_start, line_y), (line_end, line_y), 1)
        pygame.draw.line(surface, body_light, (center_x + width * 0.15, line_y), (center_x + width * 0.05, line_y), 1)


# ─── Boss ─────────────────────────────────────────────────────────────────────

def _boss_colors(health_ratio):
    if health_ratio > 0.6:
        return (30, 32, 40), (55, 60, 75), (90, 100, 125), (130, 145, 175), (255, 160, 40), (255, 190, 80), (255, 210, 120)
    elif health_ratio > 0.3:
        return (40, 38, 35), (70, 68, 60), (110, 105, 90), (150, 145, 130), (255, 140, 40), (255, 170, 80), (255, 200, 120)
    else:
        return (50, 40, 35), (85, 70, 55), (130, 110, 85), (170, 150, 120), (255, 120, 40), (255, 160, 80), (255, 200, 120)


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
    """Military-style Boss — heavy armored warship with amber/gold accents."""
    center_x = x + width / 2
    hull_dark, hull_mid, hull_light, hull_highlight, accent, accent_glow, detail = _boss_colors(health_ratio)

    # Left wings
    wing_left_outer = [
        (center_x - width * 0.08, y + height * 0.25), (x - width * 0.35, y + height * 0.7),
        (x - width * 0.15, y + height * 0.82), (center_x - width * 0.05, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left_outer)
    wing_left_mid = [
        (center_x - width * 0.06, y + height * 0.28), (x - width * 0.2, y + height * 0.65),
        (x - width * 0.08, y + height * 0.72), (center_x - width * 0.04, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_left_mid)
    wing_left_inner = [
        (center_x - width * 0.04, y + height * 0.32), (x - width * 0.1, y + height * 0.58),
        (x, y + height * 0.62), (center_x - width * 0.02, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_light, wing_left_inner)

    # Right wings
    wing_right_outer = [
        (center_x + width * 0.08, y + height * 0.25), (x + width + width * 0.35, y + height * 0.7),
        (x + width + width * 0.15, y + height * 0.82), (center_x + width * 0.05, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right_outer)
    wing_right_mid = [
        (center_x + width * 0.06, y + height * 0.28), (x + width + width * 0.2, y + height * 0.65),
        (x + width + width * 0.08, y + height * 0.72), (center_x + width * 0.04, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_right_mid)
    wing_right_inner = [
        (center_x + width * 0.04, y + height * 0.32), (x + width + width * 0.1, y + height * 0.58),
        (x + width, y + height * 0.62), (center_x + width * 0.02, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_light, wing_right_inner)

    # Main body
    main_body = [
        (center_x, y + height * 0.08), (x + width * 0.85, y + height * 0.32),
        (x + width * 0.88, y + height * 0.65), (center_x, y + height * 0.92),
        (x + width * 0.12, y + height * 0.65), (x + width * 0.15, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_dark, main_body)
    body_mid = [
        (center_x, y + height * 0.15), (x + width * 0.75, y + height * 0.35),
        (x + width * 0.78, y + height * 0.58), (center_x, y + height * 0.8),
        (x + width * 0.22, y + height * 0.58), (x + width * 0.25, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)
    body_top = [
        (center_x, y + height * 0.2), (x + width * 0.65, y + height * 0.38),
        (x + width * 0.68, y + height * 0.52), (center_x, y + height * 0.7),
        (x + width * 0.32, y + height * 0.52), (x + width * 0.35, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)

    # Cockpit
    cockpit = [
        (center_x, y + height * 0.3), (center_x - width * 0.1, y + height * 0.42),
        (center_x, y + height * 0.5), (center_x + width * 0.1, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, accent, cockpit)

    # Engines
    engine_left = [
        (center_x - width * 0.22, y + height * 0.55), (center_x - width * 0.32, y + height * 0.72),
        (center_x - width * 0.18, y + height * 0.78), (center_x - width * 0.1, y + height * 0.65),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_left)
    engine_right = [
        (center_x + width * 0.22, y + height * 0.55), (center_x + width * 0.32, y + height * 0.72),
        (center_x + width * 0.18, y + height * 0.78), (center_x + width * 0.1, y + height * 0.65),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_right)
    engine_center = [
        (center_x - width * 0.06, y + height * 0.6), (center_x - width * 0.08, y + height * 0.75),
        (center_x, y + height * 0.8), (center_x + width * 0.08, y + height * 0.75),
        (center_x + width * 0.06, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center)

    # Nose
    nose_base = [
        (center_x - width * 0.08, y + height * 0.15), (center_x + width * 0.08, y + height * 0.15),
        (center_x, y - height * 0.05),
    ]
    pygame.draw.polygon(surface, hull_highlight, nose_base)

    # Armor plates
    plate_left = [
        (x + width * 0.05, y + height * 0.45), (x + width * 0.15, y + height * 0.42),
        (x + width * 0.12, y + height * 0.55), (x + width * 0.02, y + height * 0.58),
    ]
    pygame.draw.polygon(surface, hull_highlight, plate_left)
    plate_right = [
        (x + width * 0.95, y + height * 0.45), (x + width * 0.85, y + height * 0.42),
        (x + width * 0.88, y + height * 0.55), (x + width * 0.98, y + height * 0.58),
    ]
    pygame.draw.polygon(surface, hull_highlight, plate_right)

    # Glow reactor core
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.45)), 16, accent, 36)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.45)), 9, accent_glow, 22)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.45)), 4, detail, 12)

    # Armor seams
    for i in range(4):
        line_y = y + height * 0.35 + i * height * 0.12
        pygame.draw.line(surface, hull_highlight, (center_x - width * 0.25, line_y), (center_x + width * 0.25, line_y), 1)

    # Wing edge highlights
    pygame.draw.line(surface, hull_highlight, (x - width * 0.25, y + height * 0.65), (x - width * 0.1, y + height * 0.75), 2)
    pygame.draw.line(surface, hull_highlight, (x + width + width * 0.25, y + height * 0.65), (x + width + width * 0.1, y + height * 0.75), 2)
