"""Ship sprite rendering — player, enemy, and boss ships with caching."""
import pygame
import hashlib
import inspect
from ._sprites_common import draw_glow_circle

# Sprite surface caches
_player_sprite_cache = {}
_enemy_sprite_cache = {}
_boss_sprite_cache = {}


def _code_hash(func) -> str:
    """Return a short hash of a function's source code for cache busting."""
    try:
        source = inspect.getsource(func)
        return hashlib.md5(source.encode()).hexdigest()[:8]
    except Exception:
        return "unknown"


def clear_ship_caches() -> None:
    """Clear all ship sprite caches. Useful when tweaking ship designs."""
    _player_sprite_cache.clear()
    _enemy_sprite_cache.clear()
    _boss_sprite_cache.clear()


# ─── Player (Forward-Swept Wing Attack Craft) ──────────────────────────────────

def get_player_sprite(width: float = 50, height: float = 60) -> pygame.Surface:
    cache_key = (int(width), int(height), _code_hash(_draw_player_ship))
    if cache_key not in _player_sprite_cache:
        size = max(int(width) * 4, int(height) * 3) + 40
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        draw_x = (size - int(width)) // 2
        draw_y = (size - int(height)) // 2
        _draw_player_ship(surf, draw_x, draw_y, width, height)
        _player_sprite_cache[cache_key] = surf
    return _player_sprite_cache[cache_key]


def draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    sprite = get_player_sprite(width, height)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    """Forward-swept wing attack craft — large refined fuselage, rear-mounted wings, twin tail."""
    center_x = x + width / 2

    hull_dark = (30, 36, 52)
    hull_mid = (58, 68, 90)
    hull_light = (76, 86, 108)
    hull_accent = (120, 130, 150)

    glass_dark = (28, 148, 190)
    glass_mid = (55, 188, 225)
    glass_bright = (150, 225, 246)

    engine_body = (42, 45, 55)
    engine_intake = (25, 28, 35)
    flame_orange = (255, 150, 40)

    # ── Rear-mounted forward-swept wings (wide chord, gradual taper) ──────────
    # Left wing
    wing_left_outer = [
        (center_x - width * 0.16, y + height * 0.86),
        (center_x - width * 0.19, y + height * 0.66),
        (center_x - width * 0.20, y + height * 0.46),
        (x - width * 0.64, y + height * 0.12),
        (x - width * 0.60, y + height * 0.28),
        (x - width * 0.36, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left_outer)
    wing_left_mid = [
        (center_x - width * 0.14, y + height * 0.80),
        (center_x - width * 0.17, y + height * 0.64),
        (center_x - width * 0.18, y + height * 0.50),
        (x - width * 0.52, y + height * 0.16),
        (x - width * 0.48, y + height * 0.28),
        (x - width * 0.28, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_left_mid)
    wing_left_top = [
        (center_x - width * 0.12, y + height * 0.74),
        (center_x - width * 0.15, y + height * 0.62),
        (center_x - width * 0.16, y + height * 0.54),
        (x - width * 0.42, y + height * 0.20),
        (x - width * 0.38, y + height * 0.28),
        (x - width * 0.22, y + height * 0.34),
    ]
    pygame.draw.polygon(surface, hull_light, wing_left_top)

    # Right wing
    wing_right_outer = [
        (center_x + width * 0.16, y + height * 0.86),
        (center_x + width * 0.19, y + height * 0.66),
        (center_x + width * 0.20, y + height * 0.46),
        (x + width + width * 0.64, y + height * 0.12),
        (x + width + width * 0.60, y + height * 0.28),
        (x + width + width * 0.36, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right_outer)
    wing_right_mid = [
        (center_x + width * 0.14, y + height * 0.80),
        (center_x + width * 0.17, y + height * 0.64),
        (center_x + width * 0.18, y + height * 0.50),
        (x + width + width * 0.52, y + height * 0.16),
        (x + width + width * 0.48, y + height * 0.28),
        (x + width + width * 0.28, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_right_mid)
    wing_right_top = [
        (center_x + width * 0.12, y + height * 0.74),
        (center_x + width * 0.15, y + height * 0.62),
        (center_x + width * 0.16, y + height * 0.54),
        (x + width + width * 0.42, y + height * 0.20),
        (x + width + width * 0.38, y + height * 0.28),
        (x + width + width * 0.22, y + height * 0.34),
    ]
    pygame.draw.polygon(surface, hull_light, wing_right_top)

    # ── Under-wing engine pods ────────────────────────────────────────────
    for eng_x in [center_x - width * 0.36, center_x + width * 0.36]:
        pygame.draw.polygon(surface, engine_body, [
            (eng_x - width * 0.06, y + height * 0.44),
            (eng_x + width * 0.06, y + height * 0.44),
            (eng_x + width * 0.05, y + height * 0.58),
            (eng_x - width * 0.05, y + height * 0.58),
        ])
        pygame.draw.polygon(surface, engine_intake, [
            (eng_x - width * 0.04, y + height * 0.42),
            (eng_x + width * 0.04, y + height * 0.42),
            (eng_x + width * 0.06, y + height * 0.44),
            (eng_x - width * 0.06, y + height * 0.44),
        ])
        # Engine detail line
        pygame.draw.line(surface, hull_dark,
                       (eng_x - width * 0.04, y + height * 0.51),
                       (eng_x + width * 0.04, y + height * 0.51), 1)

    # ── Twin vertical stabilizers ──────────────────────────────────────────
    for fin_x in [center_x - width * 0.18, center_x + width * 0.18]:
        pygame.draw.polygon(surface, hull_dark, [
            (fin_x - width * 0.02, y + height * 0.84),
            (fin_x - width * 0.01, y + height * 0.74),
            (fin_x + width * 0.01, y + height * 0.74),
            (fin_x + width * 0.02, y + height * 0.94),
        ])
        pygame.draw.polygon(surface, hull_mid, [
            (fin_x - width * 0.01, y + height * 0.82),
            (fin_x, y + height * 0.76),
            (fin_x + width * 0.01, y + height * 0.76),
            (fin_x + width * 0.01, y + height * 0.92),
        ])

    # ── Wide fuselage deck — cockpit sits on top, body visible on both sides ──
    fuselage = [
        (center_x, y - height * 0.38),                    # sharp nose (extended)
        (center_x + width * 0.08, y - height * 0.22),     # narrow upper (widened)
        (center_x + width * 0.12, y - height * 0.04),     # upper angular break
        (center_x + width * 0.16, y + height * 0.08),     # lower angular break
        (center_x + width * 0.20, y + height * 0.20),     # shoulder
        (center_x + width * 0.22, y + height * 0.38),     # mid (wide)
        (center_x + width * 0.22, y + height * 0.55),     # rear
        (center_x + width * 0.06, y + height * 1.04),     # tail tapered
        (center_x - width * 0.06, y + height * 1.04),     # tail left
        (center_x - width * 0.22, y + height * 0.55),     # rear left
        (center_x - width * 0.22, y + height * 0.38),     # mid left
        (center_x - width * 0.20, y + height * 0.20),     # shoulder left
        (center_x - width * 0.16, y + height * 0.08),     # lower angular break left
        (center_x - width * 0.12, y - height * 0.04),     # upper angular break left
        (center_x - width * 0.08, y - height * 0.22),     # narrow upper left
    ]
    pygame.draw.polygon(surface, hull_mid, fuselage)

    # Inner panel — darker, creates depth
    fuselage_inner = [
        (center_x, y - height * 0.28),
        (center_x + width * 0.06, y - height * 0.16),
        (center_x + width * 0.10, y - height * 0.02),
        (center_x + width * 0.13, y + height * 0.08),
        (center_x + width * 0.16, y + height * 0.20),
        (center_x + width * 0.17, y + height * 0.38),
        (center_x + width * 0.17, y + height * 0.52),
        (center_x + width * 0.04, y + height * 0.98),
        (center_x - width * 0.04, y + height * 0.98),
        (center_x - width * 0.17, y + height * 0.52),
        (center_x - width * 0.17, y + height * 0.38),
        (center_x - width * 0.16, y + height * 0.20),
        (center_x - width * 0.13, y + height * 0.08),
        (center_x - width * 0.10, y - height * 0.02),
        (center_x - width * 0.06, y - height * 0.16),
    ]
    pygame.draw.polygon(surface, hull_dark, fuselage_inner)

    # Upper highlight panel
    fuselage_hl = [
        (center_x, y - height * 0.22),
        (center_x + width * 0.05, y - height * 0.10),
        (center_x + width * 0.09, y + height * 0.04),
        (center_x + width * 0.14, y + height * 0.20),
        (center_x + width * 0.13, y + height * 0.38),
        (center_x + width * 0.13, y + height * 0.50),
        (center_x + width * 0.03, y + height * 0.97),
        (center_x - width * 0.03, y + height * 0.97),
        (center_x - width * 0.13, y + height * 0.50),
        (center_x - width * 0.13, y + height * 0.38),
        (center_x - width * 0.14, y + height * 0.20),
        (center_x - width * 0.09, y + height * 0.04),
        (center_x - width * 0.05, y - height * 0.10),
    ]
    pygame.draw.polygon(surface, hull_light, fuselage_hl)

    # ── Fuselage deck panel lines ─────────────────────────────────────────
    for i in range(3):
        line_y = y + height * (0.22 + i * 0.12)
        lw = width * (0.15 - i * 0.02)
        pygame.draw.line(surface, hull_accent,
                       (center_x - lw, line_y),
                       (center_x + lw, line_y), 1)

    # Deck side panels — cockpit flanked by fuselage body on both sides
    deck_color = (130, 142, 162)
    for side in [-1, 1]:
        pygame.draw.line(surface, hull_accent,
            (center_x + side * width * 0.15, y - height * 0.02),
            (center_x + side * width * 0.17, y + height * 0.18), 1)
        # Subtle deck surface hatch marks
        for i in range(2):
            dy = y - height * 0.02 + i * height * 0.10
            dx = center_x + side * width * (0.15 + i * 0.01)
            pygame.draw.line(surface, deck_color,
                (dx, int(dy)),
                (dx + side * width * 0.02, int(dy)), 1)

    # ── Cockpit structural frame — recessed bezel, glass sits inside ─────────
    frame_color = (18, 22, 34)
    cockpit_frame = [
        (center_x, y - height * 0.28),
        (center_x + width * 0.12, y - height * 0.10),
        (center_x + width * 0.14, y + height * 0.06),
        (center_x + width * 0.14, y + height * 0.23),
        (center_x + width * 0.06, y + height * 0.36),
        (center_x - width * 0.06, y + height * 0.36),
        (center_x - width * 0.14, y + height * 0.23),
        (center_x - width * 0.14, y + height * 0.06),
        (center_x - width * 0.12, y - height * 0.10),
    ]
    pygame.draw.polygon(surface, frame_color, cockpit_frame)
    # Frame top edge highlight
    pygame.draw.line(surface, hull_accent,
                   (center_x - width * 0.10, y - height * 0.13),
                   (center_x + width * 0.10, y - height * 0.13), 1)

    # ── Cockpit glass — set into the frame above ─────────────────────────────
    cockpit = [
        (center_x, y - height * 0.24),
        (center_x + width * 0.08, y - height * 0.08),
        (center_x + width * 0.10, y + height * 0.22),
        (center_x, y + height * 0.32),
        (center_x - width * 0.10, y + height * 0.22),
        (center_x - width * 0.08, y - height * 0.08),
    ]
    pygame.draw.polygon(surface, glass_dark, cockpit)
    cockpit_hl = [
        (center_x, y - height * 0.18),
        (center_x + width * 0.06, y - height * 0.02),
        (center_x + width * 0.07, y + height * 0.16),
        (center_x, y + height * 0.24),
        (center_x - width * 0.07, y + height * 0.16),
        (center_x - width * 0.06, y - height * 0.02),
    ]
    pygame.draw.polygon(surface, glass_mid, cockpit_hl)
    pygame.draw.polygon(surface, glass_bright, [
        (center_x, y - height * 0.12),
        (center_x + width * 0.04, y + height * 0.02),
        (center_x, y + height * 0.12),
        (center_x - width * 0.04, y + height * 0.02),
    ])

    # ── Engine exhaust flames ─────────────────────────────────────────────
    for ex in [center_x - width * 0.36, center_x + width * 0.36]:
        for i in range(3):
            flame_y = y + height * 0.58 + i * height * 0.04
            pygame.draw.ellipse(surface, (*flame_orange, 180 - i * 50),
                              (int(ex - width * 0.03), int(flame_y),
                               int(width * 0.06), int(height * 0.035)))

# ─── Enemy (Alien Mecha Combat Drone) ─────────────────────────────────────────

def _enemy_colors(health_ratio):
    """Alien mecha: dark steel plating with glowing red optical sensors."""
    if health_ratio > 0.6:
        return (28, 30, 38), (55, 58, 68), (90, 94, 108), (255, 35, 25), (255, 90, 50)
    elif health_ratio > 0.3:
        return (35, 30, 32), (65, 52, 55), (100, 80, 82), (255, 25, 18), (255, 70, 40)
    else:
        return (38, 28, 28), (70, 42, 40), (100, 65, 58), (255, 20, 12), (255, 55, 30)


def get_enemy_sprite(width: float = 50, height: float = 50, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket, _code_hash(_draw_enemy_ship))
    if cache_key not in _enemy_sprite_cache:
        size = max(int(width) * 3, int(height) * 2) + 40
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        draw_x = (size - int(width)) // 2
        draw_y = (size - int(height)) // 2
        _draw_enemy_ship(surf, draw_x, draw_y, width, height, health_ratio)
        _enemy_sprite_cache[cache_key] = surf
    return _enemy_sprite_cache[cache_key]


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    sprite = get_enemy_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    """Alien mecha combat drone — angular armor plating, red optical sensors, energy thrusters."""
    center_x = x + width / 2
    armor_dark, armor_mid, armor_light, sensor_red, sensor_glow = _enemy_colors(health_ratio)

    # ── Angular armor wings (stubby, mechanical, NOT forward-swept) ─────────
    # Left wing — angular blade sweeping slightly back
    wing_left = [
        (center_x - width * 0.08, y + height * 0.30),    # root upper
        (center_x - width * 0.12, y + height * 0.42),    # root mid
        (center_x - width * 0.08, y + height * 0.55),    # root lower
        (x - width * 0.40, y + height * 0.65),           # tip lower
        (x - width * 0.32, y + height * 0.48),           # tip mid
        (x - width * 0.36, y + height * 0.30),           # tip upper
    ]
    pygame.draw.polygon(surface, armor_dark, wing_left)
    wing_left_inner = [
        (center_x - width * 0.06, y + height * 0.34),
        (center_x - width * 0.09, y + height * 0.44),
        (center_x - width * 0.06, y + height * 0.50),
        (x - width * 0.30, y + height * 0.60),
        (x - width * 0.24, y + height * 0.48),
        (x - width * 0.28, y + height * 0.34),
    ]
    pygame.draw.polygon(surface, armor_mid, wing_left_inner)
    # Armor edge highlight
    pygame.draw.line(surface, armor_light,
                   (center_x - width * 0.08, y + height * 0.30),
                   (x - width * 0.36, y + height * 0.30), 2)

    # Right wing
    wing_right = [
        (center_x + width * 0.08, y + height * 0.30),
        (center_x + width * 0.12, y + height * 0.42),
        (center_x + width * 0.08, y + height * 0.55),
        (x + width + width * 0.40, y + height * 0.65),
        (x + width + width * 0.32, y + height * 0.48),
        (x + width + width * 0.36, y + height * 0.30),
    ]
    pygame.draw.polygon(surface, armor_dark, wing_right)
    wing_right_inner = [
        (center_x + width * 0.06, y + height * 0.34),
        (center_x + width * 0.09, y + height * 0.44),
        (center_x + width * 0.06, y + height * 0.50),
        (x + width + width * 0.30, y + height * 0.60),
        (x + width + width * 0.24, y + height * 0.48),
        (x + width + width * 0.28, y + height * 0.34),
    ]
    pygame.draw.polygon(surface, armor_mid, wing_right_inner)
    pygame.draw.line(surface, armor_light,
                   (center_x + width * 0.08, y + height * 0.30),
                   (x + width + width * 0.36, y + height * 0.30), 2)

    # ── Central armored body ────────────────────────────────────────────────
    body = [
        (center_x, y - height * 0.06),                    # top
        (center_x + width * 0.14, y + height * 0.08),     # shoulder right
        (center_x + width * 0.16, y + height * 0.32),     # mid right
        (center_x + width * 0.08, y + height * 0.60),     # lower right
        (center_x, y + height * 0.78),                     # bottom tip
        (center_x - width * 0.08, y + height * 0.60),     # lower left
        (center_x - width * 0.16, y + height * 0.32),     # mid left
        (center_x - width * 0.14, y + height * 0.08),     # shoulder left
    ]
    pygame.draw.polygon(surface, armor_dark, body)
    body_inner = [
        (center_x, y + height * 0.02),
        (center_x + width * 0.10, y + height * 0.12),
        (center_x + width * 0.12, y + height * 0.32),
        (center_x + width * 0.05, y + height * 0.55),
        (center_x, y + height * 0.70),
        (center_x - width * 0.05, y + height * 0.55),
        (center_x - width * 0.12, y + height * 0.32),
        (center_x - width * 0.10, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, armor_mid, body_inner)

    # ── Red optical sensor array (central "eye") ────────────────────────────
    eye_y = y + height * 0.22
    # Sensor housing (angular)
    housing = [
        (center_x - width * 0.08, eye_y - height * 0.04),
        (center_x + width * 0.08, eye_y - height * 0.04),
        (center_x + width * 0.06, eye_y + height * 0.06),
        (center_x - width * 0.06, eye_y + height * 0.06),
    ]
    pygame.draw.polygon(surface, (20, 18, 22), housing)
    # Glowing sensor core
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 8, sensor_red, 22)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 4, sensor_glow, 14)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 1, (255, 200, 180), 6)

    # Secondary sensor dots
    for sx, sy_f in [(center_x - width * 0.06, 0.12), (center_x + width * 0.06, 0.12)]:
        draw_glow_circle(surface, (int(sx), int(y + height * sy_f)), 2, sensor_red, 6)

    # ── Armor plate seams ───────────────────────────────────────────────────
    for i in range(3):
        line_y = y + height * (0.32 + i * 0.12)
        pygame.draw.line(surface, armor_light,
                       (center_x - width * 0.14, line_y),
                       (center_x + width * 0.14, line_y), 1)

    # ── Thruster nozzles (rear, angular) ────────────────────────────────────
    for tx, ty in [(center_x - width * 0.06, y + height * 0.62),
                     (center_x + width * 0.06, y + height * 0.62)]:
        pygame.draw.polygon(surface, (20, 18, 22), [
            (tx - width * 0.04, ty),
            (tx + width * 0.04, ty),
            (tx + width * 0.05, ty + height * 0.10),
            (tx - width * 0.05, ty + height * 0.10),
        ])
        # Blue energy exhaust
        for i in range(3):
            flame_y = ty + height * 0.08 + i * height * 0.04
            alpha = 160 - i * 45
            pygame.draw.ellipse(surface, (40, 160, 255, alpha),
                              (int(tx - width * 0.03), int(flame_y),
                               int(width * 0.06), int(height * 0.035)))

# ─── Boss (Alien Mothership — Organic-Mechanical Hybrid) ──────────────────────

def _boss_colors(health_ratio):
    """Alien mothership: dark purple/black organic armor with toxic green glow."""
    if health_ratio > 0.6:
        return (18, 6, 30), (50, 20, 55), (90, 45, 85), (160, 100, 140), (100, 255, 50), (200, 255, 150)
    elif health_ratio > 0.3:
        return (28, 10, 30), (62, 28, 52), (100, 50, 80), (155, 90, 120), (80, 230, 40), (170, 245, 120)
    else:
        return (35, 12, 25), (68, 30, 42), (100, 50, 60), (140, 75, 85), (60, 190, 30), (130, 220, 80)


def get_boss_sprite(width: float = 120, height: float = 100, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket, _code_hash(_draw_boss_ship))
    if cache_key not in _boss_sprite_cache:
        size = max(int(width) * 3, int(height) * 2) + 50
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        draw_x = (size - int(width)) // 2
        draw_y = (size - int(height)) // 2
        _draw_boss_ship(surf, draw_x, draw_y, width, height, health_ratio)
        _boss_sprite_cache[cache_key] = surf
    return _boss_sprite_cache[cache_key]


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    sprite = get_boss_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    """Alien mothership — organic-mechanical hybrid with multiple bioluminescent eyes and tentacle-like appendages."""
    center_x = x + width / 2
    hull_dark, hull_mid, hull_light, hull_highlight, bio_green, bio_bright = _boss_colors(health_ratio)

    # ── Tentacle-like organic appendages (outermost, drawn first) ────────────
    tentacle_positions = [
        (center_x - width * 0.38, y + height * 0.25, -1),
        (center_x + width * 0.38, y + height * 0.25, 1),
        (center_x - width * 0.32, y + height * 0.55, -1),
        (center_x + width * 0.32, y + height * 0.55, 1),
    ]
    for tx, ty, direction in tentacle_positions:
        tentacle = [
            (tx, ty),
            (tx + direction * width * 0.08, ty + height * 0.04),
            (tx + direction * width * 0.15, ty + height * 0.15),
            (tx + direction * width * 0.12, ty + height * 0.28),
            (tx + direction * width * 0.05, ty + height * 0.22),
            (tx - direction * width * 0.02, ty + height * 0.10),
        ]
        pygame.draw.polygon(surface, hull_dark, tentacle)
        pygame.draw.polygon(surface, hull_mid, [
            (tx, ty + height * 0.02),
            (tx + direction * width * 0.05, ty + height * 0.06),
            (tx + direction * width * 0.10, ty + height * 0.16),
            (tx + direction * width * 0.08, ty + height * 0.24),
            (tx + direction * width * 0.02, ty + height * 0.18),
        ])
        # Glowing tip
        tip_x = tx + direction * width * 0.14
        tip_y = ty + height * 0.22
        draw_glow_circle(surface, (int(tip_x), int(tip_y)), 3, bio_green, 10)

    # ── Massive organic wing membranes ──────────────────────────────────────
    # Left upper wing
    left_wing_outer = [
        (center_x - width * 0.18, y + height * 0.10),
        (center_x - width * 0.12, y + height * 0.22),
        (x - width * 0.55, y + height * 0.02),           # far forward tip
        (x - width * 0.48, y + height * 0.25),
        (x - width * 0.35, y + height * 0.48),
        (center_x - width * 0.10, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, left_wing_outer)

    left_wing_mid = [
        (center_x - width * 0.14, y + height * 0.14),
        (center_x - width * 0.10, y + height * 0.24),
        (x - width * 0.42, y + height * 0.06),
        (x - width * 0.38, y + height * 0.26),
        (x - width * 0.26, y + height * 0.42),
        (center_x - width * 0.08, y + height * 0.48),
    ]
    pygame.draw.polygon(surface, hull_mid, left_wing_mid)

    left_wing_inner = [
        (center_x - width * 0.10, y + height * 0.18),
        (center_x - width * 0.08, y + height * 0.26),
        (x - width * 0.30, y + height * 0.10),
        (x - width * 0.28, y + height * 0.28),
        (x - width * 0.18, y + height * 0.38),
        (center_x - width * 0.06, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_light, left_wing_inner)

    # Right upper wing
    right_wing_outer = [
        (center_x + width * 0.18, y + height * 0.10),
        (center_x + width * 0.12, y + height * 0.22),
        (x + width + width * 0.55, y + height * 0.02),
        (x + width + width * 0.48, y + height * 0.25),
        (x + width + width * 0.35, y + height * 0.48),
        (center_x + width * 0.10, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, right_wing_outer)

    right_wing_mid = [
        (center_x + width * 0.14, y + height * 0.14),
        (center_x + width * 0.10, y + height * 0.24),
        (x + width + width * 0.42, y + height * 0.06),
        (x + width + width * 0.38, y + height * 0.26),
        (x + width + width * 0.26, y + height * 0.42),
        (center_x + width * 0.08, y + height * 0.48),
    ]
    pygame.draw.polygon(surface, hull_mid, right_wing_mid)

    right_wing_inner = [
        (center_x + width * 0.10, y + height * 0.18),
        (center_x + width * 0.08, y + height * 0.26),
        (x + width + width * 0.30, y + height * 0.10),
        (x + width + width * 0.28, y + height * 0.28),
        (x + width + width * 0.18, y + height * 0.38),
        (center_x + width * 0.06, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_light, right_wing_inner)

    # Wing bioluminescent veins
    for wing_pts in [
        [(center_x - width * 0.08, y + height * 0.28), (x - width * 0.34, y + height * 0.12)],
        [(center_x - width * 0.07, y + height * 0.38), (x - width * 0.22, y + height * 0.36)],
        [(center_x + width * 0.08, y + height * 0.28), (x + width + width * 0.34, y + height * 0.12)],
        [(center_x + width * 0.07, y + height * 0.38), (x + width + width * 0.22, y + height * 0.36)],
    ]:
        pygame.draw.line(surface, bio_green, wing_pts[0], wing_pts[1], 1)

    # ── Lower secondary wings ───────────────────────────────────────────────
    for lw_outer, lw_inner in [
        ([(center_x - width * 0.12, y + height * 0.40),
          (x - width * 0.45, y + height * 0.50),
          (x - width * 0.35, y + height * 0.72),
          (center_x - width * 0.08, y + height * 0.65)],
         [(center_x - width * 0.10, y + height * 0.43),
          (x - width * 0.36, y + height * 0.52),
          (x - width * 0.28, y + height * 0.66),
          (center_x - width * 0.06, y + height * 0.60)]),
        ([(center_x + width * 0.12, y + height * 0.40),
          (x + width + width * 0.45, y + height * 0.50),
          (x + width + width * 0.35, y + height * 0.72),
          (center_x + width * 0.08, y + height * 0.65)],
         [(center_x + width * 0.10, y + height * 0.43),
          (x + width + width * 0.36, y + height * 0.52),
          (x + width + width * 0.28, y + height * 0.66),
          (center_x + width * 0.06, y + height * 0.60)]),
    ]:
        pygame.draw.polygon(surface, hull_dark, lw_outer)
        pygame.draw.polygon(surface, hull_mid, lw_inner)

    # ── Giant organic hull ──────────────────────────────────────────────────
    hull = [
        (center_x, y - height * 0.08),                    # nose
        (center_x + width * 0.16, y + height * 0.10),
        (center_x + width * 0.24, y + height * 0.35),     # widest
        (center_x + width * 0.14, y + height * 0.55),
        (center_x + width * 0.08, y + height * 0.78),
        (center_x, y + height * 0.90),                     # tail
        (center_x - width * 0.08, y + height * 0.78),
        (center_x - width * 0.14, y + height * 0.55),
        (center_x - width * 0.24, y + height * 0.35),     # widest
        (center_x - width * 0.16, y + height * 0.10),
    ]
    pygame.draw.polygon(surface, hull_dark, hull)

    # Inner organic armor plates
    hull_inner = [
        (center_x, y + height * 0.02),
        (center_x + width * 0.12, y + height * 0.14),
        (center_x + width * 0.18, y + height * 0.35),
        (center_x + width * 0.10, y + height * 0.55),
        (center_x + width * 0.05, y + height * 0.70),
        (center_x, y + height * 0.80),
        (center_x - width * 0.05, y + height * 0.70),
        (center_x - width * 0.10, y + height * 0.55),
        (center_x - width * 0.18, y + height * 0.35),
        (center_x - width * 0.12, y + height * 0.14),
    ]
    pygame.draw.polygon(surface, hull_mid, hull_inner)

    # Hull highlight ridge
    ridge = [
        (center_x, y + height * 0.08),
        (center_x - width * 0.06, y + height * 0.35),
        (center_x, y + height * 0.68),
        (center_x + width * 0.06, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, hull_light, ridge)

    # ── Central bioluminescent eye ───────────────────────────────────────────
    eye_y = y + height * 0.32
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 16, bio_green, 42)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 10, bio_bright, 28)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 5, (220, 255, 180), 16)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 2, (255, 255, 240), 8)

    # ── Secondary eyes (pairs flanking the central eye) ─────────────────────
    for sx, sy_frac in [
        (center_x - width * 0.14, 0.24),
        (center_x + width * 0.14, 0.24),
        (center_x - width * 0.08, 0.44),
        (center_x + width * 0.08, 0.44),
    ]:
        draw_glow_circle(surface, (int(sx), int(y + height * sy_frac)), 4, bio_green, 14)
        draw_glow_circle(surface, (int(sx), int(y + height * sy_frac)), 2, bio_bright, 7)

    # ── Organic exhaust orifices (rear) ─────────────────────────────────────
    exhaust_positions = [
        (center_x - width * 0.16, y + height * 0.65),
        (center_x + width * 0.16, y + height * 0.65),
        (center_x - width * 0.10, y + height * 0.78),
        (center_x + width * 0.10, y + height * 0.78),
    ]
    for ex, ey_pos in exhaust_positions:
        draw_glow_circle(surface, (int(ex), int(ey_pos)), 5, bio_green, 16)
        for i in range(4):
            flame_y = ey_pos + height * 0.03 + i * height * 0.04
            alpha = 160 - i * 35
            pygame.draw.ellipse(surface, (*bio_green, alpha),
                              (int(ex - width * 0.03), int(flame_y),
                               int(width * 0.06), int(height * 0.05)))

    # ── Organic armor texture — horizontal chitin ridges ────────────────────
    for i in range(5):
        line_y = y + height * (0.15 + i * 0.10)
        line_w = width * (0.18 - i * 0.02)
        pygame.draw.line(surface, hull_highlight,
                       (center_x - line_w, line_y),
                       (center_x + line_w, line_y), 1)
        # Small bioluminescent dots along ridges
        dot_y = int(line_y)
        for dot_x in [int(center_x - line_w * 0.7), int(center_x + line_w * 0.7)]:
            pygame.draw.circle(surface, (*bio_green, 80), (dot_x, dot_y), 1)

    # Wing edge highlights
    for edge_pts in [
        [(center_x - width * 0.18, y + height * 0.12), (x - width * 0.52, y + height * 0.04)],
        [(center_x + width * 0.18, y + height * 0.12), (x + width + width * 0.52, y + height * 0.04)],
    ]:
        pygame.draw.line(surface, hull_highlight, edge_pts[0], edge_pts[1], 2)
