"""Ship sprite rendering — player, enemy, and boss ships with caching."""
import functools
import hashlib
import inspect
import pygame
from ._sprites_common import draw_glow_circle
from .generated_asset_cache import load_or_build_generated_surface

# Sprite surface caches
_player_sprite_cache = {}
_enemy_sprite_cache = {}
_boss_sprite_cache = {}
_elite_sprite_cache = {}
_ship_sprite_caches_prewarmed = False

PLAYER_SPRITE_STYLE_VERSION = 5
PLAYER_SPRITE_CANVAS_PADDING = 20
PLAYER_SPRITE_MIN_BORDER = 4
PLAYER_SPRITE_CACHE_MAX = 8
BOSS_SPRITE_STYLE_VERSION = 4
ENEMY_SPRITE_STYLE_VERSION = 3
ELITE_SPRITE_STYLE_VERSION = 2


@functools.lru_cache(maxsize=4)
def _code_hash(func) -> str:
    """Return a short hash of a function's source code for cache busting.
    Results are cached so expensive MD5 is only computed once per function.
    """
    try:
        source = inspect.getsource(func)
        return hashlib.md5(source.encode()).hexdigest()[:8]
    except (OSError, TypeError, ValueError):
        return "unknown"


# ─── Player (Forward-Swept Wing Attack Craft) ──────────────────────────────────

def _player_sprite_cache_key(width: float, height: float) -> tuple:
    return (
        int(width),
        int(height),
        PLAYER_SPRITE_STYLE_VERSION,
        _code_hash(_draw_player_ship),
    )


def _player_sprite_canvas_size(width: float, height: float) -> int:
    visual_width = int(width * 3.15)
    visual_height = int(height * 2.25)
    return max(visual_width, visual_height) + PLAYER_SPRITE_CANVAS_PADDING * 2


def get_player_sprite(width: float = 50, height: float = 60) -> pygame.Surface:
    cache_key = _player_sprite_cache_key(width, height)
    if cache_key not in _player_sprite_cache:
        if len(_player_sprite_cache) >= PLAYER_SPRITE_CACHE_MAX:
            _player_sprite_cache.pop(next(iter(_player_sprite_cache)))
        _player_sprite_cache[cache_key] = load_or_build_generated_surface(
            "player_ship",
            cache_key,
            lambda: _build_player_sprite(width, height),
        )
    return _player_sprite_cache[cache_key]


def _build_player_sprite(width: float = 50, height: float = 60) -> pygame.Surface:
    size = _player_sprite_canvas_size(width, height)
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_x = (size - int(width)) // 2
    draw_y = (size - int(height)) // 2
    _draw_player_ship(surf, draw_x, draw_y, width, height)
    return surf


def draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    sprite = get_player_sprite(width, height)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    """Draw a fast interceptor with broad wings and layered armor."""
    center_x = x + width / 2

    hull_shadow = (22, 26, 36)
    hull_dark = (42, 50, 66)
    hull_mid = (82, 90, 106)
    hull_light = (126, 136, 150)
    hull_edge = (190, 198, 208)

    glass_dark = (18, 92, 126)
    glass_mid = (38, 186, 220)
    glass_bright = (170, 246, 255)

    panel_accent = (122, 98, 74)
    panel_accent_light = (176, 150, 110)
    flame_core = (245, 178, 74)
    flame_hot = (176, 76, 42)
    exhaust_blue = (58, 88, 132)

    # Main delta wings with forward-swept tips.
    for side in (-1, 1):
        wing_outer = [
            (center_x + side * width * 0.10, y + height * 0.82),
            (center_x + side * width * 0.20, y + height * 0.54),
            (center_x + side * width * 0.30, y + height * 0.25),
            (center_x + side * width * 1.08, y + height * 0.06),
            (center_x + side * width * 0.96, y + height * 0.26),
            (center_x + side * width * 0.55, y + height * 0.52),
            (center_x + side * width * 0.34, y + height * 0.93),
        ]
        pygame.draw.polygon(surface, hull_shadow, wing_outer)

        wing_mid = [
            (center_x + side * width * 0.13, y + height * 0.76),
            (center_x + side * width * 0.24, y + height * 0.50),
            (center_x + side * width * 0.36, y + height * 0.29),
            (center_x + side * width * 0.92, y + height * 0.12),
            (center_x + side * width * 0.82, y + height * 0.26),
            (center_x + side * width * 0.50, y + height * 0.48),
            (center_x + side * width * 0.32, y + height * 0.82),
        ]
        pygame.draw.polygon(surface, hull_dark, wing_mid)

        wing_plate = [
            (center_x + side * width * 0.20, y + height * 0.63),
            (center_x + side * width * 0.33, y + height * 0.41),
            (center_x + side * width * 0.72, y + height * 0.20),
            (center_x + side * width * 0.64, y + height * 0.31),
            (center_x + side * width * 0.42, y + height * 0.48),
            (center_x + side * width * 0.30, y + height * 0.70),
        ]
        pygame.draw.polygon(surface, hull_mid, wing_plate)

        leading_edge = [
            (center_x + side * width * 0.40, y + height * 0.27),
            (center_x + side * width * 0.94, y + height * 0.10),
            (center_x + side * width * 0.88, y + height * 0.17),
            (center_x + side * width * 0.46, y + height * 0.34),
        ]
        pygame.draw.polygon(surface, hull_light, leading_edge)

        wing_insert = [
            (center_x + side * width * 0.43, y + height * 0.36),
            (center_x + side * width * 0.82, y + height * 0.20),
            (center_x + side * width * 0.78, y + height * 0.25),
            (center_x + side * width * 0.48, y + height * 0.40),
        ]
        pygame.draw.polygon(surface, panel_accent, wing_insert)
        pygame.draw.line(
            surface,
            panel_accent_light,
            (center_x + side * width * 0.36, y + height * 0.38),
            (center_x + side * width * 0.88, y + height * 0.17),
            1,
        )

        # Small canards near the nose give the silhouette more speed.
        canard = [
            (center_x + side * width * 0.13, y + height * 0.08),
            (center_x + side * width * 0.62, y - height * 0.10),
            (center_x + side * width * 0.54, y + height * 0.02),
            (center_x + side * width * 0.18, y + height * 0.20),
        ]
        pygame.draw.polygon(surface, hull_dark, canard)
        pygame.draw.line(
            surface,
            hull_edge,
            (center_x + side * width * 0.22, y + height * 0.10),
            (center_x + side * width * 0.56, y - height * 0.03),
            1,
        )

    # Under-wing engine pods and bright rear exhaust.
    for side in (-1, 1):
        pod_x = center_x + side * width * 0.42
        pod = [
            (pod_x - side * width * 0.10, y + height * 0.50),
            (pod_x + side * width * 0.10, y + height * 0.50),
            (pod_x + side * width * 0.13, y + height * 0.82),
            (pod_x + side * width * 0.07, y + height * 1.02),
            (pod_x - side * width * 0.07, y + height * 1.02),
            (pod_x - side * width * 0.13, y + height * 0.82),
        ]
        pygame.draw.polygon(surface, hull_shadow, pod)
        nozzle = pygame.Rect(
            int(pod_x - width * 0.055),
            int(y + height * 0.94),
            max(4, int(width * 0.11)),
            max(5, int(height * 0.09)),
        )
        pygame.draw.ellipse(surface, (9, 12, 20), nozzle)
        for i, color in enumerate((flame_core, flame_hot, exhaust_blue)):
            flame_y = y + height * (0.98 + i * 0.055)
            pygame.draw.ellipse(
                surface,
                (*color, 155 - i * 38),
                (
                    int(pod_x - width * (0.055 + i * 0.012)),
                    int(flame_y),
                    max(4, int(width * (0.11 + i * 0.024))),
                    max(4, int(height * 0.055)),
                ),
            )

    center_flame = [
        (center_x, y + height * 1.24),
        (center_x + width * 0.08, y + height * 1.06),
        (center_x + width * 0.04, y + height * 0.92),
        (center_x - width * 0.04, y + height * 0.92),
        (center_x - width * 0.08, y + height * 1.06),
    ]
    pygame.draw.polygon(surface, (*exhaust_blue, 110), center_flame)
    pygame.draw.polygon(surface, (*flame_core, 165), [
        (center_x, y + height * 1.16),
        (center_x + width * 0.04, y + height * 1.02),
        (center_x - width * 0.04, y + height * 1.02),
    ])

    # Twin tail fins sit on top of the rear fuselage.
    for side in (-1, 1):
        fin = [
            (center_x + side * width * 0.13, y + height * 0.78),
            (center_x + side * width * 0.32, y + height * 0.62),
            (center_x + side * width * 0.27, y + height * 1.03),
            (center_x + side * width * 0.08, y + height * 0.98),
        ]
        pygame.draw.polygon(surface, hull_shadow, fin)
        pygame.draw.line(
            surface,
            panel_accent_light,
            (center_x + side * width * 0.24, y + height * 0.69),
            (center_x + side * width * 0.21, y + height * 0.96),
            1,
        )

    # Central fuselage: long sharp nose, broad armored deck, narrow tail.
    fuselage_outer = [
        (center_x, y - height * 0.54),
        (center_x + width * 0.09, y - height * 0.36),
        (center_x + width * 0.16, y - height * 0.10),
        (center_x + width * 0.25, y + height * 0.18),
        (center_x + width * 0.28, y + height * 0.52),
        (center_x + width * 0.18, y + height * 0.86),
        (center_x + width * 0.07, y + height * 1.10),
        (center_x, y + height * 1.18),
        (center_x - width * 0.07, y + height * 1.10),
        (center_x - width * 0.18, y + height * 0.86),
        (center_x - width * 0.28, y + height * 0.52),
        (center_x - width * 0.25, y + height * 0.18),
        (center_x - width * 0.16, y - height * 0.10),
        (center_x - width * 0.09, y - height * 0.36),
    ]
    pygame.draw.polygon(surface, hull_shadow, fuselage_outer)

    fuselage_mid = [
        (center_x, y - height * 0.45),
        (center_x + width * 0.07, y - height * 0.30),
        (center_x + width * 0.12, y - height * 0.07),
        (center_x + width * 0.20, y + height * 0.18),
        (center_x + width * 0.22, y + height * 0.50),
        (center_x + width * 0.14, y + height * 0.82),
        (center_x + width * 0.04, y + height * 1.05),
        (center_x, y + height * 1.11),
        (center_x - width * 0.04, y + height * 1.05),
        (center_x - width * 0.14, y + height * 0.82),
        (center_x - width * 0.22, y + height * 0.50),
        (center_x - width * 0.20, y + height * 0.18),
        (center_x - width * 0.12, y - height * 0.07),
        (center_x - width * 0.07, y - height * 0.30),
    ]
    pygame.draw.polygon(surface, hull_mid, fuselage_mid)

    dorsal_plate = [
        (center_x, y - height * 0.34),
        (center_x + width * 0.07, y - height * 0.16),
        (center_x + width * 0.12, y + height * 0.17),
        (center_x + width * 0.11, y + height * 0.54),
        (center_x + width * 0.04, y + height * 0.92),
        (center_x, y + height * 1.02),
        (center_x - width * 0.04, y + height * 0.92),
        (center_x - width * 0.11, y + height * 0.54),
        (center_x - width * 0.12, y + height * 0.17),
        (center_x - width * 0.07, y - height * 0.16),
    ]
    pygame.draw.polygon(surface, hull_light, dorsal_plate)

    spine = [
        (center_x, y - height * 0.28),
        (center_x + width * 0.035, y - height * 0.08),
        (center_x + width * 0.045, y + height * 0.76),
        (center_x, y + height * 0.98),
        (center_x - width * 0.045, y + height * 0.76),
        (center_x - width * 0.035, y - height * 0.08),
    ]
    pygame.draw.polygon(surface, hull_dark, spine)
    pygame.draw.line(surface, panel_accent_light, (center_x, y - height * 0.24), (center_x, y + height * 0.88), 1)

    # Cockpit has a dark recessed frame and bright glass facets.
    cockpit_frame = [
        (center_x, y - height * 0.27),
        (center_x + width * 0.105, y - height * 0.08),
        (center_x + width * 0.12, y + height * 0.20),
        (center_x + width * 0.05, y + height * 0.40),
        (center_x - width * 0.05, y + height * 0.40),
        (center_x - width * 0.12, y + height * 0.20),
        (center_x - width * 0.105, y - height * 0.08),
    ]
    pygame.draw.polygon(surface, (9, 13, 24), cockpit_frame)

    cockpit = [
        (center_x, y - height * 0.21),
        (center_x + width * 0.075, y - height * 0.04),
        (center_x + width * 0.080, y + height * 0.18),
        (center_x, y + height * 0.31),
        (center_x - width * 0.080, y + height * 0.18),
        (center_x - width * 0.075, y - height * 0.04),
    ]
    pygame.draw.polygon(surface, glass_dark, cockpit)
    pygame.draw.polygon(surface, glass_mid, [
        (center_x, y - height * 0.16),
        (center_x + width * 0.050, y + height * 0.00),
        (center_x + width * 0.045, y + height * 0.14),
        (center_x, y + height * 0.23),
        (center_x - width * 0.045, y + height * 0.14),
        (center_x - width * 0.050, y + height * 0.00),
    ])
    pygame.draw.polygon(surface, glass_bright, [
        (center_x, y - height * 0.09),
        (center_x + width * 0.026, y + height * 0.03),
        (center_x, y + height * 0.10),
        (center_x - width * 0.026, y + height * 0.03),
    ])

    # Armor seams, side intakes, and weapon mounts add readable mechanical detail.
    for i, frac in enumerate((0.22, 0.38, 0.55, 0.71)):
        line_w = width * (0.16 - i * 0.022)
        line_y = y + height * frac
        pygame.draw.line(surface, hull_edge, (center_x - line_w, line_y), (center_x + line_w, line_y), 1)

    for side in (-1, 1):
        intake = [
            (center_x + side * width * 0.17, y + height * 0.20),
            (center_x + side * width * 0.28, y + height * 0.26),
            (center_x + side * width * 0.22, y + height * 0.42),
            (center_x + side * width * 0.14, y + height * 0.37),
        ]
        pygame.draw.polygon(surface, (8, 12, 22), intake)
        pygame.draw.line(
            surface,
            panel_accent_light,
            (center_x + side * width * 0.18, y + height * 0.38),
            (center_x + side * width * 0.25, y + height * 0.28),
            1,
        )

        mount_x = center_x + side * width * 0.56
        pygame.draw.circle(surface, hull_shadow, (int(mount_x), int(y + height * 0.43)), max(2, int(width * 0.045)))
        pygame.draw.circle(surface, hull_edge, (int(mount_x), int(y + height * 0.43)), max(1, int(width * 0.018)))

# ─── Enemy (Alien Mecha Combat Drone) ─────────────────────────────────────────

def _enemy_colors(health_ratio):
    """Alien mecha: dark steel plating with glowing red optical sensors."""
    if health_ratio > 0.6:
        return (32, 30, 38), (70, 58, 60), (126, 106, 96), (255, 44, 30), (255, 120, 70)
    elif health_ratio > 0.3:
        return (44, 30, 32), (84, 50, 48), (136, 84, 72), (255, 32, 22), (255, 90, 54)
    else:
        return (50, 26, 26), (92, 42, 36), (132, 66, 52), (255, 20, 12), (245, 70, 40)


def get_enemy_sprite(width: float = 50, height: float = 50, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket, ENEMY_SPRITE_STYLE_VERSION, _code_hash(_draw_enemy_ship))
    if cache_key not in _enemy_sprite_cache:
        _enemy_sprite_cache[cache_key] = load_or_build_generated_surface(
            "enemy_ship",
            cache_key,
            lambda: _build_enemy_sprite(width, height, health_ratio),
        )
    return _enemy_sprite_cache[cache_key]


def _build_enemy_sprite(width: float = 50, height: float = 50, health_ratio: float = 1.0) -> pygame.Surface:
    size = max(int(width) * 3, int(height) * 2) + 40
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_x = (size - int(width)) // 2
    draw_y = (size - int(height)) // 2
    _draw_enemy_ship(surf, draw_x, draw_y, width, height, health_ratio)
    return surf


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    sprite = get_enemy_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0) -> None:
    """Alien mecha combat drone — angular armor plating, red optical sensors, energy thrusters."""
    center_x = x + width / 2
    armor_dark, armor_mid, armor_light, sensor_red, sensor_glow = _enemy_colors(health_ratio)
    dread_shadow = (14, 12, 18)
    gunmetal = (28, 26, 32)

    # Outer horn armor gives regular drones a more threatening silhouette.
    for side in (-1, 1):
        horn = [
            (center_x + side * width * 0.10, y + height * 0.24),
            (center_x + side * width * 0.34, y + height * 0.08),
            (center_x + side * width * 0.56, y + height * 0.15),
            (center_x + side * width * 0.42, y + height * 0.30),
            (center_x + side * width * 0.18, y + height * 0.34),
        ]
        pygame.draw.polygon(surface, dread_shadow, horn)
        pygame.draw.polygon(surface, armor_mid, [
            (center_x + side * width * 0.18, y + height * 0.25),
            (center_x + side * width * 0.36, y + height * 0.15),
            (center_x + side * width * 0.48, y + height * 0.17),
            (center_x + side * width * 0.36, y + height * 0.25),
            (center_x + side * width * 0.21, y + height * 0.30),
        ])
        pygame.draw.line(
            surface,
            armor_light,
            (center_x + side * width * 0.22, y + height * 0.27),
            (center_x + side * width * 0.42, y + height * 0.18),
            1,
        )

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
    pygame.draw.polygon(surface, (12, 10, 16), [
        (center_x, y - height * 0.12),
        (center_x + width * 0.06, y + height * 0.02),
        (center_x, y + height * 0.20),
        (center_x - width * 0.06, y + height * 0.02),
    ])
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
    pygame.draw.polygon(surface, armor_light, [
        (center_x, y + height * 0.08),
        (center_x + width * 0.06, y + height * 0.18),
        (center_x + width * 0.04, y + height * 0.48),
        (center_x, y + height * 0.62),
        (center_x - width * 0.04, y + height * 0.48),
        (center_x - width * 0.06, y + height * 0.18),
    ])

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

    # Side weapon pods widen the readable threat profile without adding glow clutter.
    for side in (-1, 1):
        pod_x = center_x + side * width * 0.34
        pygame.draw.polygon(surface, gunmetal, [
            (pod_x - side * width * 0.05, y + height * 0.38),
            (pod_x + side * width * 0.10, y + height * 0.42),
            (pod_x + side * width * 0.12, y + height * 0.56),
            (pod_x - side * width * 0.02, y + height * 0.55),
        ])
        pygame.draw.line(
            surface,
            sensor_red,
            (pod_x + side * width * 0.03, y + height * 0.48),
            (pod_x + side * width * 0.12, y + height * 0.50),
            1,
        )

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

# ─── Elite Enemy (Golden Armored Commander) ─────────────────────────────

def _elite_colors(health_ratio):
    """Elite commander: gold-trimmed dark armor with amber energy glow."""
    if health_ratio > 0.6:
        return (24, 22, 28), (76, 60, 34), (150, 116, 48), (235, 188, 70), (255, 174, 28), (255, 224, 110)
    elif health_ratio > 0.3:
        return (34, 26, 28), (82, 56, 36), (140, 96, 44), (215, 160, 56), (245, 142, 24), (245, 196, 82)
    else:
        return (40, 24, 24), (84, 46, 34), (128, 72, 40), (184, 112, 42), (225, 105, 20), (215, 150, 58)


def get_elite_enemy_sprite(width: float = 65, height: float = 65, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket, ELITE_SPRITE_STYLE_VERSION, _code_hash(_draw_elite_enemy_ship))
    if cache_key not in _elite_sprite_cache:
        _elite_sprite_cache[cache_key] = load_or_build_generated_surface(
            "elite_enemy_ship",
            cache_key,
            lambda: _build_elite_enemy_sprite(width, height, health_ratio),
        )
    return _elite_sprite_cache[cache_key]


def _build_elite_enemy_sprite(width: float = 65, height: float = 65, health_ratio: float = 1.0) -> pygame.Surface:
    size = max(int(width) * 3, int(height) * 2) + 50
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_x = (size - int(width)) // 2
    draw_y = (size - int(height)) // 2
    _draw_elite_enemy_ship(surf, draw_x, draw_y, width, height, health_ratio)
    return surf


def draw_elite_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 65, height: float = 65, health_ratio: float = 1.0) -> None:
    sprite = get_elite_enemy_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_elite_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 65, height: float = 65, health_ratio: float = 1.0) -> None:
    """Elite Commander — reinforced angular armor with golden trim and amber energy core."""
    center_x = x + width / 2
    armor_dark, armor_mid, armor_light, gold_trim, amber_core, amber_glow = _elite_colors(health_ratio)
    obsidian = (12, 10, 14)
    deep_red = (92, 24, 20)

    # ── Energy shield aura (subtle outer glow) ──────────────────────────
    shield_points = [
        (center_x, y - height * 0.15),
        (center_x + width * 0.45, y + height * 0.05),
        (center_x + width * 0.50, y + height * 0.40),
        (center_x + width * 0.20, y + height * 0.78),
        (center_x, y + height * 0.88),
        (center_x - width * 0.20, y + height * 0.78),
        (center_x - width * 0.50, y + height * 0.40),
        (center_x - width * 0.45, y + height * 0.05),
    ]
    pygame.draw.polygon(surface, (*amber_glow, 25), shield_points)

    # Command crown and heavy shoulder plates make elites read as a higher tier.
    crown = [
        (center_x, y - height * 0.22),
        (center_x + width * 0.18, y - height * 0.02),
        (center_x + width * 0.10, y + height * 0.12),
        (center_x, y + height * 0.04),
        (center_x - width * 0.10, y + height * 0.12),
        (center_x - width * 0.18, y - height * 0.02),
    ]
    pygame.draw.polygon(surface, obsidian, crown)
    pygame.draw.line(surface, gold_trim, crown[0], crown[1], 2)
    pygame.draw.line(surface, gold_trim, crown[0], crown[-1], 2)

    for side in (-1, 1):
        shoulder = [
            (center_x + side * width * 0.20, y + height * 0.16),
            (center_x + side * width * 0.58, y + height * 0.08),
            (center_x + side * width * 0.72, y + height * 0.25),
            (center_x + side * width * 0.34, y + height * 0.34),
        ]
        pygame.draw.polygon(surface, obsidian, shoulder)
        pygame.draw.polygon(surface, deep_red, [
            (center_x + side * width * 0.28, y + height * 0.18),
            (center_x + side * width * 0.56, y + height * 0.13),
            (center_x + side * width * 0.62, y + height * 0.24),
            (center_x + side * width * 0.36, y + height * 0.29),
        ])
        pygame.draw.line(
            surface,
            gold_trim,
            (center_x + side * width * 0.30, y + height * 0.18),
            (center_x + side * width * 0.62, y + height * 0.15),
            2,
        )

    # ── Reinforced angular wings (wider, heavier than regular) ──────────
    # Left wing — broad angular blade
    wing_left = [
        (center_x - width * 0.06, y + height * 0.28),
        (center_x - width * 0.12, y + height * 0.44),
        (center_x - width * 0.08, y + height * 0.58),
        (x - width * 0.48, y + height * 0.68),
        (x - width * 0.38, y + height * 0.46),
        (x - width * 0.42, y + height * 0.26),
    ]
    pygame.draw.polygon(surface, armor_dark, wing_left)
    wing_left_inner = [
        (center_x - width * 0.04, y + height * 0.32),
        (center_x - width * 0.09, y + height * 0.46),
        (center_x - width * 0.06, y + height * 0.54),
        (x - width * 0.36, y + height * 0.63),
        (x - width * 0.28, y + height * 0.46),
        (x - width * 0.32, y + height * 0.30),
    ]
    pygame.draw.polygon(surface, armor_mid, wing_left_inner)
    # Gold trim on wing edge
    pygame.draw.line(surface, gold_trim,
                   (center_x - width * 0.06, y + height * 0.28),
                   (x - width * 0.42, y + height * 0.26), 3)

    # Right wing
    wing_right = [
        (center_x + width * 0.06, y + height * 0.28),
        (center_x + width * 0.12, y + height * 0.44),
        (center_x + width * 0.08, y + height * 0.58),
        (x + width + width * 0.48, y + height * 0.68),
        (x + width + width * 0.38, y + height * 0.46),
        (x + width + width * 0.42, y + height * 0.26),
    ]
    pygame.draw.polygon(surface, armor_dark, wing_right)
    wing_right_inner = [
        (center_x + width * 0.04, y + height * 0.32),
        (center_x + width * 0.09, y + height * 0.46),
        (center_x + width * 0.06, y + height * 0.54),
        (x + width + width * 0.36, y + height * 0.63),
        (x + width + width * 0.28, y + height * 0.46),
        (x + width + width * 0.32, y + height * 0.30),
    ]
    pygame.draw.polygon(surface, armor_mid, wing_right_inner)
    pygame.draw.line(surface, gold_trim,
                   (center_x + width * 0.06, y + height * 0.28),
                   (x + width + width * 0.42, y + height * 0.26), 3)

    # ── Central reinforced body (bulkier than regular) ──────────────────
    body = [
        (center_x, y - height * 0.08),
        (center_x + width * 0.18, y + height * 0.06),
        (center_x + width * 0.20, y + height * 0.34),
        (center_x + width * 0.10, y + height * 0.62),
        (center_x, y + height * 0.80),
        (center_x - width * 0.10, y + height * 0.62),
        (center_x - width * 0.20, y + height * 0.34),
        (center_x - width * 0.18, y + height * 0.06),
    ]
    pygame.draw.polygon(surface, armor_dark, body)
    body_inner = [
        (center_x, y + height * 0.00),
        (center_x + width * 0.13, y + height * 0.10),
        (center_x + width * 0.15, y + height * 0.34),
        (center_x + width * 0.07, y + height * 0.58),
        (center_x, y + height * 0.72),
        (center_x - width * 0.07, y + height * 0.58),
        (center_x - width * 0.15, y + height * 0.34),
        (center_x - width * 0.13, y + height * 0.10),
    ]
    pygame.draw.polygon(surface, armor_mid, body_inner)

    # Central black armor spine for depth.
    pygame.draw.polygon(surface, obsidian, [
        (center_x, y + height * 0.02),
        (center_x + width * 0.05, y + height * 0.18),
        (center_x + width * 0.04, y + height * 0.60),
        (center_x, y + height * 0.76),
        (center_x - width * 0.04, y + height * 0.60),
        (center_x - width * 0.05, y + height * 0.18),
    ])

    # ── Gold chevron insignia (elite rank mark) ─────────────────────────
    chevron_y = y + height * 0.40
    chevron = [
        (center_x, chevron_y - height * 0.08),
        (center_x + width * 0.10, chevron_y + height * 0.04),
        (center_x, chevron_y),
        (center_x - width * 0.10, chevron_y + height * 0.04),
    ]
    pygame.draw.polygon(surface, gold_trim, chevron)
    pygame.draw.polygon(surface, amber_core, chevron, 1)

    # ── Amber energy core (replaces red sensor) ─────────────────────────
    core_y = y + height * 0.20
    # Core housing
    housing = [
        (center_x - width * 0.10, core_y - height * 0.06),
        (center_x + width * 0.10, core_y - height * 0.06),
        (center_x + width * 0.08, core_y + height * 0.08),
        (center_x - width * 0.08, core_y + height * 0.08),
    ]
    pygame.draw.polygon(surface, (18, 18, 20), housing)
    pygame.draw.polygon(surface, gold_trim, housing, 1)
    # Glowing amber core
    draw_glow_circle(surface, (int(center_x), int(core_y)), 9, amber_core, 26)
    draw_glow_circle(surface, (int(center_x), int(core_y)), 5, amber_glow, 18)
    draw_glow_circle(surface, (int(center_x), int(core_y)), 2, (255, 240, 180), 8)

    # ── Secondary sensor nodes (golden) ─────────────────────────────────
    for sx, sy_f in [(center_x - width * 0.07, 0.10), (center_x + width * 0.07, 0.10)]:
        draw_glow_circle(surface, (int(sx), int(y + height * sy_f)), 2, amber_core, 6)

    # Heavy side cannons.
    for side in (-1, 1):
        cannon_x = center_x + side * width * 0.30
        pygame.draw.polygon(surface, obsidian, [
            (cannon_x - side * width * 0.04, y + height * 0.43),
            (cannon_x + side * width * 0.12, y + height * 0.47),
            (cannon_x + side * width * 0.12, y + height * 0.62),
            (cannon_x - side * width * 0.02, y + height * 0.60),
        ])
        pygame.draw.line(
            surface,
            gold_trim,
            (cannon_x + side * width * 0.02, y + height * 0.52),
            (cannon_x + side * width * 0.12, y + height * 0.54),
            2,
        )

    # ── Armor plate seams (gold-lined) ──────────────────────────────────
    for i in range(3):
        line_y = y + height * (0.30 + i * 0.13)
        pygame.draw.line(surface, gold_trim,
                       (center_x - width * 0.16, line_y),
                       (center_x + width * 0.16, line_y), 1)

    # ── Twin heavy thrusters (orange exhaust) ───────────────────────────
    for tx, ty in [(center_x - width * 0.08, y + height * 0.64),
                     (center_x + width * 0.08, y + height * 0.64)]:
        # Thruster housing
        pygame.draw.polygon(surface, (18, 18, 20), [
            (tx - width * 0.06, ty),
            (tx + width * 0.06, ty),
            (tx + width * 0.07, ty + height * 0.12),
            (tx - width * 0.07, ty + height * 0.12),
        ])
        # Gold thruster trim
        pygame.draw.line(surface, gold_trim,
                       (tx - width * 0.06, ty),
                       (tx + width * 0.06, ty), 1)
        # Orange/amber exhaust flames
        for i in range(4):
            flame_y = ty + height * 0.10 + i * height * 0.05
            alpha = 180 - i * 40
            r = 255 - i * 20
            g = 140 - i * 25
            pygame.draw.ellipse(surface, (r, g, 20, alpha),
                              (int(tx - width * 0.04), int(flame_y),
                               int(width * 0.08), int(height * 0.04)))


# ─── Boss (Armored Alien Dreadnought) ─────────────────────────────────────────

def _boss_colors(health_ratio):
    """Armored alien dreadnought: near-black armor with toxic green energy."""
    if health_ratio > 0.6:
        return (20, 8, 30), (62, 24, 58), (116, 58, 96), (184, 108, 154), (118, 255, 62), (210, 255, 150)
    elif health_ratio > 0.3:
        return (34, 10, 30), (76, 28, 50), (126, 54, 78), (176, 92, 116), (86, 230, 42), (176, 245, 120)
    else:
        return (44, 12, 24), (86, 30, 40), (130, 52, 58), (160, 76, 78), (66, 190, 30), (136, 220, 80)


def get_boss_sprite(width: float = 120, height: float = 100, health_ratio: float = 1.0) -> pygame.Surface:
    health_bucket = int(health_ratio * 10)
    cache_key = (int(width), int(height), health_bucket, BOSS_SPRITE_STYLE_VERSION, _code_hash(_draw_boss_ship))
    if cache_key not in _boss_sprite_cache:
        _boss_sprite_cache[cache_key] = load_or_build_generated_surface(
            "boss_ship",
            cache_key,
            lambda: _build_boss_sprite(width, height, health_ratio),
        )
    return _boss_sprite_cache[cache_key]


def _build_boss_sprite(width: float = 120, height: float = 100, health_ratio: float = 1.0) -> pygame.Surface:
    size = max(int(width) * 3, int(height) * 2) + 50
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    draw_x = (size - int(width)) // 2
    draw_y = (size - int(height)) // 2
    _draw_boss_ship(surf, draw_x, draw_y, width, height, health_ratio)
    return surf


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    sprite = get_boss_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    """Armored alien dreadnought with a heavy hull, siege wings, and toxic energy cores."""
    center_x = x + width / 2
    hull_dark, hull_mid, hull_light, hull_highlight, bio_green, bio_bright = _boss_colors(health_ratio)
    void = (10, 5, 14)
    rib_dark = (34, 12, 36)

    # Broad upper carapace establishes a heavy silhouette before details are layered in.
    crown_outer = [
        (center_x, y - height * 0.20),
        (center_x + width * 0.26, y - height * 0.02),
        (center_x + width * 0.50, y + height * 0.18),
        (center_x + width * 0.34, y + height * 0.38),
        (center_x, y + height * 0.30),
        (center_x - width * 0.34, y + height * 0.38),
        (center_x - width * 0.50, y + height * 0.18),
        (center_x - width * 0.26, y - height * 0.02),
    ]
    pygame.draw.polygon(surface, void, crown_outer)
    crown_inner = [
        (center_x, y - height * 0.10),
        (center_x + width * 0.22, y + height * 0.04),
        (center_x + width * 0.36, y + height * 0.18),
        (center_x + width * 0.22, y + height * 0.28),
        (center_x, y + height * 0.22),
        (center_x - width * 0.22, y + height * 0.28),
        (center_x - width * 0.36, y + height * 0.18),
        (center_x - width * 0.22, y + height * 0.04),
    ]
    pygame.draw.polygon(surface, hull_dark, crown_inner)
    pygame.draw.line(surface, hull_highlight, crown_outer[0], crown_outer[1], 2)
    pygame.draw.line(surface, hull_highlight, crown_outer[0], crown_outer[-1], 2)

    # Lower mandible pylons replace loose appendages with a compact armored mass.
    for side in (-1, 1):
        mandible_outer = [
            (center_x + side * width * 0.18, y + height * 0.50),
            (center_x + side * width * 0.48, y + height * 0.54),
            (center_x + side * width * 0.56, y + height * 0.72),
            (center_x + side * width * 0.34, y + height * 0.88),
            (center_x + side * width * 0.16, y + height * 0.70),
        ]
        mandible_inner = [
            (center_x + side * width * 0.23, y + height * 0.56),
            (center_x + side * width * 0.42, y + height * 0.59),
            (center_x + side * width * 0.46, y + height * 0.70),
            (center_x + side * width * 0.32, y + height * 0.80),
            (center_x + side * width * 0.22, y + height * 0.68),
        ]
        pygame.draw.polygon(surface, void, mandible_outer)
        pygame.draw.polygon(surface, hull_mid, mandible_inner)
        pygame.draw.line(
            surface,
            hull_highlight,
            (center_x + side * width * 0.26, y + height * 0.60),
            (center_x + side * width * 0.46, y + height * 0.68),
            1,
        )

    # Side siege cannons fill the boss silhouette and clarify its dangerous width.
    for side in (-1, 1):
        cannon_root_x = center_x + side * width * 0.30
        cannon = [
            (cannon_root_x, y + height * 0.31),
            (cannon_root_x + side * width * 0.34, y + height * 0.25),
            (cannon_root_x + side * width * 0.42, y + height * 0.40),
            (cannon_root_x + side * width * 0.12, y + height * 0.52),
        ]
        pygame.draw.polygon(surface, void, cannon)
        pygame.draw.polygon(surface, hull_mid, [
            (cannon_root_x + side * width * 0.04, y + height * 0.35),
            (cannon_root_x + side * width * 0.26, y + height * 0.31),
            (cannon_root_x + side * width * 0.32, y + height * 0.39),
            (cannon_root_x + side * width * 0.10, y + height * 0.46),
        ])
        draw_glow_circle(
            surface,
            (int(cannon_root_x + side * width * 0.35), int(y + height * 0.39)),
            3,
            bio_green,
            12,
        )

    # ── Heavy siege wings ───────────────────────────────────────────────────
    for side in (-1, 1):
        wing_outer = [
            (center_x + side * width * 0.28, y + height * 0.16),
            (center_x + side * width * 0.52, y + height * 0.22),
            (center_x + side * width * 0.93, y + height * 0.16),
            (center_x + side * width * 1.02, y + height * 0.34),
            (center_x + side * width * 0.84, y + height * 0.58),
            (center_x + side * width * 0.36, y + height * 0.64),
            (center_x + side * width * 0.22, y + height * 0.42),
        ]
        wing_mid = [
            (center_x + side * width * 0.32, y + height * 0.24),
            (center_x + side * width * 0.56, y + height * 0.28),
            (center_x + side * width * 0.80, y + height * 0.25),
            (center_x + side * width * 0.88, y + height * 0.37),
            (center_x + side * width * 0.70, y + height * 0.50),
            (center_x + side * width * 0.38, y + height * 0.55),
            (center_x + side * width * 0.28, y + height * 0.40),
        ]
        wing_plate = [
            (center_x + side * width * 0.40, y + height * 0.31),
            (center_x + side * width * 0.72, y + height * 0.30),
            (center_x + side * width * 0.79, y + height * 0.38),
            (center_x + side * width * 0.62, y + height * 0.46),
            (center_x + side * width * 0.40, y + height * 0.48),
            (center_x + side * width * 0.33, y + height * 0.39),
        ]
        rear_fin = [
            (center_x + side * width * 0.34, y + height * 0.56),
            (center_x + side * width * 0.72, y + height * 0.62),
            (center_x + side * width * 0.62, y + height * 0.80),
            (center_x + side * width * 0.28, y + height * 0.70),
        ]
        pygame.draw.polygon(surface, void, wing_outer)
        pygame.draw.polygon(surface, hull_dark, wing_mid)
        pygame.draw.polygon(surface, hull_mid, wing_plate)
        pygame.draw.polygon(surface, hull_dark, rear_fin)
        pygame.draw.line(
            surface,
            hull_highlight,
            (center_x + side * width * 0.50, y + height * 0.25),
            (center_x + side * width * 0.90, y + height * 0.22),
            2,
        )
        pygame.draw.line(
            surface,
            bio_green,
            (center_x + side * width * 0.46, y + height * 0.40),
            (center_x + side * width * 0.73, y + height * 0.37),
            1,
        )

        battery = [
            (center_x + side * width * 0.62, y + height * 0.36),
            (center_x + side * width * 0.82, y + height * 0.35),
            (center_x + side * width * 0.86, y + height * 0.44),
            (center_x + side * width * 0.66, y + height * 0.48),
        ]
        pygame.draw.polygon(surface, rib_dark, battery)
        draw_glow_circle(
            surface,
            (int(center_x + side * width * 0.82), int(y + height * 0.42)),
            3,
            bio_green,
            10,
        )

    # ── Giant organic hull ──────────────────────────────────────────────────
    hull = [
        (center_x, y - height * 0.16),
        (center_x + width * 0.24, y + height * 0.02),
        (center_x + width * 0.36, y + height * 0.24),
        (center_x + width * 0.34, y + height * 0.48),
        (center_x + width * 0.22, y + height * 0.74),
        (center_x + width * 0.10, y + height * 0.94),
        (center_x, y + height * 1.04),
        (center_x - width * 0.10, y + height * 0.94),
        (center_x - width * 0.22, y + height * 0.74),
        (center_x - width * 0.34, y + height * 0.48),
        (center_x - width * 0.36, y + height * 0.24),
        (center_x - width * 0.24, y + height * 0.02),
    ]
    pygame.draw.polygon(surface, hull_dark, hull)

    # Inner organic armor plates
    hull_inner = [
        (center_x, y - height * 0.03),
        (center_x + width * 0.18, y + height * 0.12),
        (center_x + width * 0.24, y + height * 0.34),
        (center_x + width * 0.18, y + height * 0.58),
        (center_x + width * 0.08, y + height * 0.78),
        (center_x, y + height * 0.88),
        (center_x - width * 0.08, y + height * 0.78),
        (center_x - width * 0.18, y + height * 0.58),
        (center_x - width * 0.24, y + height * 0.34),
        (center_x - width * 0.18, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, hull_mid, hull_inner)
    pygame.draw.polygon(surface, rib_dark, [
        (center_x, y + height * 0.00),
        (center_x + width * 0.10, y + height * 0.22),
        (center_x + width * 0.09, y + height * 0.64),
        (center_x, y + height * 0.88),
        (center_x - width * 0.09, y + height * 0.64),
        (center_x - width * 0.10, y + height * 0.22),
    ])

    # Hull highlight ridge
    ridge = [
        (center_x, y + height * 0.02),
        (center_x - width * 0.08, y + height * 0.36),
        (center_x, y + height * 0.76),
        (center_x + width * 0.08, y + height * 0.36),
    ]
    pygame.draw.polygon(surface, hull_light, ridge)

    # Armored brow over the core eye.
    brow = [
        (center_x - width * 0.28, y + height * 0.21),
        (center_x - width * 0.10, y + height * 0.12),
        (center_x + width * 0.10, y + height * 0.12),
        (center_x + width * 0.28, y + height * 0.21),
        (center_x + width * 0.18, y + height * 0.31),
        (center_x - width * 0.18, y + height * 0.31),
    ]
    pygame.draw.polygon(surface, void, brow)
    pygame.draw.line(surface, hull_highlight, brow[0], brow[1], 2)
    pygame.draw.line(surface, hull_highlight, brow[2], brow[3], 2)

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
        (center_x - width * 0.20, y + height * 0.68),
        (center_x + width * 0.20, y + height * 0.68),
        (center_x - width * 0.10, y + height * 0.84),
        (center_x + width * 0.10, y + height * 0.84),
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
        line_w = width * (0.26 - i * 0.035)
        pygame.draw.line(surface, hull_highlight,
                       (center_x - line_w, line_y),
                       (center_x + line_w, line_y), 1)
        # Small bioluminescent dots along ridges
        dot_y = int(line_y)
        for dot_x in [int(center_x - line_w * 0.7), int(center_x + line_w * 0.7)]:
            pygame.draw.circle(surface, (*bio_green, 80), (dot_x, dot_y), 1)


def prewarm_ship_sprite_caches(force: bool = False) -> None:
    """Generate common ship sprites once so gameplay mostly hits memory cache."""
    global _ship_sprite_caches_prewarmed
    if _ship_sprite_caches_prewarmed and not force:
        return

    get_player_sprite(68, 82)

    for health_ratio in (1.0, 0.5, 0.25):
        get_enemy_sprite(50, 50, health_ratio)
        get_elite_enemy_sprite(65, 65, health_ratio)
        get_boss_sprite(120, 100, health_ratio)

    _ship_sprite_caches_prewarmed = True
