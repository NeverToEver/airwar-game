"""Ship sprite rendering — player, enemy, and boss ships with caching."""

import functools
import hashlib
import inspect

import pygame

from ._sprites_common import draw_glow_circle
from .generated_asset_cache import load_or_build_generated_surface

# Sprite surface caches
_player_sprite_cache: dict[tuple[int, int, int, str], pygame.Surface] = {}
_enemy_sprite_cache: dict[tuple[int, int, int, int, str], pygame.Surface] = {}
_boss_sprite_cache: dict[tuple[int, int, int, int, str], pygame.Surface] = {}
_elite_sprite_cache: dict[tuple[int, int, int, int, str], pygame.Surface] = {}
_ship_sprite_caches_prewarmed = False

PLAYER_SPRITE_STYLE_VERSION = 6
PLAYER_SPRITE_CANVAS_PADDING = 20
PLAYER_SPRITE_MIN_BORDER = 4
PLAYER_SPRITE_CACHE_MAX = 8
BOSS_SPRITE_STYLE_VERSION = 5
ENEMY_SPRITE_STYLE_VERSION = 4
ELITE_SPRITE_STYLE_VERSION = 3


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

    panel_accent = (34, 64, 88)
    panel_accent_light = (96, 186, 214)
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

    # Wingtip navigation lights (teal, matches HUD accent).
    for side in (-1, 1):
        draw_glow_circle(
            surface,
            (int(center_x + side * width * 1.02), int(y + height * 0.12)),
            2,
            glass_mid,
            6,
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
        # White-hot core at the nozzle throat.
        pygame.draw.ellipse(
            surface,
            (255, 240, 200, 220),
            (
                int(pod_x - width * 0.028),
                int(y + height * 0.99),
                max(3, int(width * 0.056)),
                max(3, int(height * 0.04)),
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
    pygame.draw.polygon(
        surface,
        (*flame_core, 165),
        [
            (center_x, y + height * 1.16),
            (center_x + width * 0.04, y + height * 1.02),
            (center_x - width * 0.04, y + height * 1.02),
        ],
    )
    pygame.draw.polygon(
        surface,
        (255, 244, 210, 220),
        [
            (center_x, y + height * 1.09),
            (center_x + width * 0.02, y + height * 1.01),
            (center_x - width * 0.02, y + height * 1.01),
        ],
    )

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
    # Bright glint along the nose spine catches the light from above.
    pygame.draw.line(surface, hull_edge, (center_x, y - height * 0.50), (center_x, y - height * 0.32), 1)

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
    pygame.draw.polygon(
        surface,
        glass_mid,
        [
            (center_x, y - height * 0.16),
            (center_x + width * 0.050, y + height * 0.00),
            (center_x + width * 0.045, y + height * 0.14),
            (center_x, y + height * 0.23),
            (center_x - width * 0.045, y + height * 0.14),
            (center_x - width * 0.050, y + height * 0.00),
        ],
    )
    pygame.draw.polygon(
        surface,
        glass_bright,
        [
            (center_x, y - height * 0.09),
            (center_x + width * 0.026, y + height * 0.03),
            (center_x, y + height * 0.10),
            (center_x - width * 0.026, y + height * 0.03),
        ],
    )

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


def draw_enemy_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0
) -> None:
    sprite = get_enemy_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_enemy_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 50, health_ratio: float = 1.0
) -> None:
    """Alien mecha stingray — swept crescent wings, armored diamond hull, red sensor slit.

    The drone faces down-screen toward the player: sensor head and gun pods at
    the bottom, engine plumes trailing at the top.
    """
    center_x = x + width / 2
    armor_dark, armor_mid, armor_light, sensor_red, sensor_glow = _enemy_colors(health_ratio)
    void = (14, 12, 18)
    gunmetal = (30, 28, 34)

    # ── Rear thruster plumes (top, trailing upward; bells drawn later) ────
    for side in (-1, 1):
        tx = center_x + side * width * 0.11
        for i in range(3):
            flame_y = y + height * (0.055 - i * 0.05)
            flame_w = max(3, int(width * (0.085 - i * 0.018)))
            pygame.draw.ellipse(
                surface,
                (140 - i * 45, 220 - i * 40, 255, 150 - i * 45),
                (int(tx - flame_w // 2), int(flame_y), flame_w, max(2, int(height * 0.045))),
            )

    # ── Crescent wings (tips swept back, layered plating) ─────────────────
    for side in (-1, 1):
        wing_outer = [
            (center_x + side * width * 0.12, y + height * 0.30),
            (center_x + side * width * 0.16, y + height * 0.52),
            (center_x + side * width * 0.44, y + height * 0.57),
            (center_x + side * width * 0.92, y + height * 0.46),
            (center_x + side * width * 0.88, y + height * 0.27),
            (center_x + side * width * 0.56, y + height * 0.21),
            (center_x + side * width * 0.28, y + height * 0.19),
        ]
        pygame.draw.polygon(surface, void, wing_outer)
        wing_mid = [
            (center_x + side * width * 0.16, y + height * 0.31),
            (center_x + side * width * 0.19, y + height * 0.48),
            (center_x + side * width * 0.42, y + height * 0.52),
            (center_x + side * width * 0.80, y + height * 0.43),
            (center_x + side * width * 0.77, y + height * 0.29),
            (center_x + side * width * 0.53, y + height * 0.25),
            (center_x + side * width * 0.29, y + height * 0.23),
        ]
        pygame.draw.polygon(surface, armor_dark, wing_mid)
        wing_plate = [
            (center_x + side * width * 0.21, y + height * 0.33),
            (center_x + side * width * 0.23, y + height * 0.45),
            (center_x + side * width * 0.40, y + height * 0.48),
            (center_x + side * width * 0.68, y + height * 0.41),
            (center_x + side * width * 0.66, y + height * 0.31),
            (center_x + side * width * 0.49, y + height * 0.28),
            (center_x + side * width * 0.30, y + height * 0.26),
        ]
        pygame.draw.polygon(surface, armor_mid, wing_plate)
        # Leading-edge rim light and a recessed panel seam below it.
        pygame.draw.line(
            surface,
            armor_light,
            (center_x + side * width * 0.28, y + height * 0.22),
            (center_x + side * width * 0.84, y + height * 0.29),
            2,
        )
        pygame.draw.line(
            surface,
            void,
            (center_x + side * width * 0.24, y + height * 0.38),
            (center_x + side * width * 0.62, y + height * 0.42),
            1,
        )
        # Wingtip sensor strobe.
        draw_glow_circle(
            surface,
            (int(center_x + side * width * 0.84), int(y + height * 0.35)),
            2,
            sensor_red,
            6,
        )

    # ── Under-wing gun pods (muzzles point down at the player) ────────────
    for side in (-1, 1):
        pod_x = center_x + side * width * 0.40
        pygame.draw.polygon(
            surface,
            gunmetal,
            [
                (pod_x - side * width * 0.045, y + height * 0.52),
                (pod_x + side * width * 0.055, y + height * 0.53),
                (pod_x + side * width * 0.06, y + height * 0.72),
                (pod_x - side * width * 0.03, y + height * 0.71),
            ],
        )
        pygame.draw.line(
            surface,
            armor_light,
            (pod_x + side * width * 0.01, y + height * 0.54),
            (pod_x + side * width * 0.03, y + height * 0.70),
            1,
        )
        draw_glow_circle(
            surface,
            (int(pod_x + side * width * 0.02), int(y + height * 0.73)),
            1,
            sensor_red,
            5,
        )

    # ── Armored diamond hull ──────────────────────────────────────────────
    hull_outer = [
        (center_x, y + height * 0.12),
        (center_x + width * 0.14, y + height * 0.26),
        (center_x + width * 0.17, y + height * 0.50),
        (center_x + width * 0.11, y + height * 0.72),
        (center_x, y + height * 0.86),
        (center_x - width * 0.11, y + height * 0.72),
        (center_x - width * 0.17, y + height * 0.50),
        (center_x - width * 0.14, y + height * 0.26),
    ]
    pygame.draw.polygon(surface, armor_dark, hull_outer)
    hull_mid = [
        (center_x, y + height * 0.18),
        (center_x + width * 0.10, y + height * 0.30),
        (center_x + width * 0.12, y + height * 0.50),
        (center_x + width * 0.08, y + height * 0.66),
        (center_x, y + height * 0.78),
        (center_x - width * 0.08, y + height * 0.66),
        (center_x - width * 0.12, y + height * 0.50),
        (center_x - width * 0.10, y + height * 0.30),
    ]
    pygame.draw.polygon(surface, armor_mid, hull_mid)
    # Top armor plate catches the light; dark spine groove adds depth.
    pygame.draw.polygon(
        surface,
        armor_light,
        [
            (center_x, y + height * 0.24),
            (center_x + width * 0.055, y + height * 0.33),
            (center_x + width * 0.045, y + height * 0.52),
            (center_x, y + height * 0.62),
            (center_x - width * 0.045, y + height * 0.52),
            (center_x - width * 0.055, y + height * 0.33),
        ],
    )
    pygame.draw.line(surface, void, (center_x, y + height * 0.28), (center_x, y + height * 0.58), 1)
    for frac, half_w in ((0.36, 0.11), (0.48, 0.115)):
        pygame.draw.line(
            surface,
            void,
            (center_x - width * half_w, y + height * frac),
            (center_x + width * half_w, y + height * frac),
            1,
        )

    # ── Engine bells capping the hull's top edge ──────────────────────────
    for side in (-1, 1):
        tx = center_x + side * width * 0.11
        pygame.draw.polygon(
            surface,
            gunmetal,
            [
                (tx - width * 0.05, y + height * 0.06),
                (tx + width * 0.05, y + height * 0.06),
                (tx + width * 0.04, y + height * 0.18),
                (tx - width * 0.04, y + height * 0.18),
            ],
        )
        pygame.draw.line(
            surface, armor_light, (tx - width * 0.05, y + height * 0.06), (tx + width * 0.05, y + height * 0.06), 1
        )

    # ── Sensor head — armored brow over a glowing red slit ────────────────
    eye_y = y + height * 0.735
    pygame.draw.polygon(
        surface,
        void,
        [
            (center_x - width * 0.13, y + height * 0.60),
            (center_x + width * 0.13, y + height * 0.60),
            (center_x + width * 0.095, y + height * 0.70),
            (center_x - width * 0.095, y + height * 0.70),
        ],
    )
    for i, (color, alpha) in enumerate(((sensor_red, 60), (sensor_red, 140), (sensor_glow, 255))):
        shrink = i * 0.30
        pygame.draw.ellipse(
            surface,
            (*color, alpha),
            (
                int(center_x - width * 0.085 * (1 - shrink)),
                int(eye_y - height * 0.025 * (1 - shrink)),
                max(2, int(width * 0.17 * (1 - shrink))),
                max(1, int(height * 0.05 * (1 - shrink))),
            ),
        )
    pygame.draw.circle(surface, (255, 215, 200), (int(center_x), int(eye_y)), 1)
    # Chin plate under the sensor completes the nose.
    pygame.draw.polygon(
        surface,
        armor_mid,
        [
            (center_x - width * 0.08, y + height * 0.76),
            (center_x + width * 0.08, y + height * 0.76),
            (center_x + width * 0.04, y + height * 0.84),
            (center_x - width * 0.04, y + height * 0.84),
        ],
    )


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


def draw_elite_enemy_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 65, height: float = 65, health_ratio: float = 1.0
) -> None:
    sprite = get_elite_enemy_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_elite_enemy_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 65, height: float = 65, health_ratio: float = 1.0
) -> None:
    """Elite Commander — heavy crescent armor, gold leading edges, amber reactor core.

    Faces down-screen like the regular drone, but bulkier: swept-back command
    horns, shoulder plates, and forward gun prongs flanking the chin.
    """
    center_x = x + width / 2
    armor_dark, armor_mid, _armor_light, gold_trim, amber_core, amber_glow = _elite_colors(health_ratio)
    obsidian = (12, 10, 14)
    deep_red = (92, 24, 20)

    # ── Heavy thruster plumes (top, trailing upward; bells drawn later) ───
    for side in (-1, 1):
        tx = center_x + side * width * 0.09
        for i in range(4):
            flame_y = y + height * (0.05 - i * 0.05)
            flame_w = max(3, int(width * (0.10 - i * 0.017)))
            pygame.draw.ellipse(
                surface,
                (255 - i * 18, 150 - i * 28, 30, 180 - i * 40),
                (int(tx - flame_w // 2), int(flame_y), flame_w, max(2, int(height * 0.05))),
            )

    # ── Swept-back command horns (elite silhouette marker) ────────────────
    for side in (-1, 1):
        pygame.draw.polygon(
            surface,
            obsidian,
            [
                (center_x + side * width * 0.04, y + height * 0.18),
                (center_x + side * width * 0.10, y + height * 0.04),
                (center_x + side * width * 0.22, y - height * 0.02),
                (center_x + side * width * 0.16, y + height * 0.10),
                (center_x + side * width * 0.08, y + height * 0.16),
            ],
        )
        pygame.draw.line(
            surface,
            gold_trim,
            (center_x + side * width * 0.10, y + height * 0.06),
            (center_x + side * width * 0.20, y + height * 0.00),
            2,
        )

    # ── Heavy crescent wings with gold leading edges ──────────────────────
    for side in (-1, 1):
        wing_outer = [
            (center_x + side * width * 0.10, y + height * 0.26),
            (center_x + side * width * 0.15, y + height * 0.50),
            (center_x + side * width * 0.12, y + height * 0.64),
            (center_x + side * width * 0.48, y + height * 0.62),
            (center_x + side * width * 0.98, y + height * 0.50),
            (center_x + side * width * 0.94, y + height * 0.24),
            (center_x + side * width * 0.60, y + height * 0.18),
            (center_x + side * width * 0.30, y + height * 0.15),
        ]
        pygame.draw.polygon(surface, obsidian, wing_outer)
        wing_mid = [
            (center_x + side * width * 0.15, y + height * 0.29),
            (center_x + side * width * 0.19, y + height * 0.48),
            (center_x + side * width * 0.17, y + height * 0.58),
            (center_x + side * width * 0.47, y + height * 0.56),
            (center_x + side * width * 0.87, y + height * 0.46),
            (center_x + side * width * 0.83, y + height * 0.27),
            (center_x + side * width * 0.57, y + height * 0.23),
            (center_x + side * width * 0.31, y + height * 0.20),
        ]
        pygame.draw.polygon(surface, armor_dark, wing_mid)
        wing_plate = [
            (center_x + side * width * 0.21, y + height * 0.32),
            (center_x + side * width * 0.24, y + height * 0.46),
            (center_x + side * width * 0.22, y + height * 0.53),
            (center_x + side * width * 0.45, y + height * 0.51),
            (center_x + side * width * 0.74, y + height * 0.43),
            (center_x + side * width * 0.71, y + height * 0.30),
            (center_x + side * width * 0.52, y + height * 0.27),
            (center_x + side * width * 0.32, y + height * 0.24),
        ]
        pygame.draw.polygon(surface, armor_mid, wing_plate)
        # Gold leading edge — the elite signature.
        pygame.draw.line(
            surface,
            gold_trim,
            (center_x + side * width * 0.30, y + height * 0.17),
            (center_x + side * width * 0.92, y + height * 0.27),
            3,
        )
        pygame.draw.line(
            surface,
            obsidian,
            (center_x + side * width * 0.26, y + height * 0.38),
            (center_x + side * width * 0.70, y + height * 0.43),
            1,
        )
        draw_glow_circle(
            surface,
            (int(center_x + side * width * 0.90), int(y + height * 0.36)),
            2,
            amber_core,
            6,
        )

    # ── Shoulder plates at the wing roots ─────────────────────────────────
    for side in (-1, 1):
        pygame.draw.polygon(
            surface,
            obsidian,
            [
                (center_x + side * width * 0.16, y + height * 0.24),
                (center_x + side * width * 0.34, y + height * 0.20),
                (center_x + side * width * 0.40, y + height * 0.32),
                (center_x + side * width * 0.22, y + height * 0.36),
            ],
        )
        pygame.draw.polygon(
            surface,
            deep_red,
            [
                (center_x + side * width * 0.21, y + height * 0.26),
                (center_x + side * width * 0.32, y + height * 0.24),
                (center_x + side * width * 0.35, y + height * 0.30),
                (center_x + side * width * 0.24, y + height * 0.32),
            ],
        )
        pygame.draw.line(
            surface,
            gold_trim,
            (center_x + side * width * 0.20, y + height * 0.26),
            (center_x + side * width * 0.35, y + height * 0.23),
            2,
        )

    # ── Bulky armored hull ────────────────────────────────────────────────
    hull_outer = [
        (center_x, y + height * 0.14),
        (center_x + width * 0.18, y + height * 0.26),
        (center_x + width * 0.20, y + height * 0.52),
        (center_x + width * 0.12, y + height * 0.76),
        (center_x, y + height * 0.90),
        (center_x - width * 0.12, y + height * 0.76),
        (center_x - width * 0.20, y + height * 0.52),
        (center_x - width * 0.18, y + height * 0.26),
    ]
    pygame.draw.polygon(surface, armor_dark, hull_outer)
    hull_mid = [
        (center_x, y + height * 0.20),
        (center_x + width * 0.13, y + height * 0.30),
        (center_x + width * 0.145, y + height * 0.52),
        (center_x + width * 0.085, y + height * 0.70),
        (center_x, y + height * 0.82),
        (center_x - width * 0.085, y + height * 0.70),
        (center_x - width * 0.145, y + height * 0.52),
        (center_x - width * 0.13, y + height * 0.30),
    ]
    pygame.draw.polygon(surface, armor_mid, hull_mid)
    # Central black armor spine for depth.
    pygame.draw.polygon(
        surface,
        obsidian,
        [
            (center_x, y + height * 0.26),
            (center_x + width * 0.05, y + height * 0.36),
            (center_x + width * 0.04, y + height * 0.60),
            (center_x, y + height * 0.72),
            (center_x - width * 0.04, y + height * 0.60),
            (center_x - width * 0.05, y + height * 0.36),
        ],
    )
    # ── Engine bells capping the hull's top edge ──────────────────────────
    for side in (-1, 1):
        tx = center_x + side * width * 0.09
        pygame.draw.polygon(
            surface,
            obsidian,
            [
                (tx - width * 0.065, y + height * 0.07),
                (tx + width * 0.065, y + height * 0.07),
                (tx + width * 0.05, y + height * 0.20),
                (tx - width * 0.05, y + height * 0.20),
            ],
        )
        pygame.draw.line(
            surface, gold_trim, (tx - width * 0.065, y + height * 0.07), (tx + width * 0.065, y + height * 0.07), 1
        )
    # Gold chevron insignia above the core.
    pygame.draw.polygon(
        surface,
        gold_trim,
        [
            (center_x, y + height * 0.30),
            (center_x + width * 0.10, y + height * 0.38),
            (center_x, y + height * 0.345),
            (center_x - width * 0.10, y + height * 0.38),
        ],
    )
    # Gold-lined panel seams.
    for frac, half_w in ((0.44, 0.15), (0.72, 0.09)):
        pygame.draw.line(
            surface,
            gold_trim,
            (center_x - width * half_w, y + height * frac),
            (center_x + width * half_w, y + height * frac),
            1,
        )

    # ── Amber reactor core (chest, gold-ringed housing) ───────────────────
    core_y = y + height * 0.58
    housing = [
        (center_x - width * 0.10, core_y - height * 0.05),
        (center_x + width * 0.10, core_y - height * 0.05),
        (center_x + width * 0.12, core_y + height * 0.02),
        (center_x + width * 0.08, core_y + height * 0.09),
        (center_x - width * 0.08, core_y + height * 0.09),
        (center_x - width * 0.12, core_y + height * 0.02),
    ]
    pygame.draw.polygon(surface, obsidian, housing)
    pygame.draw.polygon(surface, gold_trim, housing, 1)
    draw_glow_circle(surface, (int(center_x), int(core_y + height * 0.02)), 7, amber_core, 22)
    draw_glow_circle(surface, (int(center_x), int(core_y + height * 0.02)), 4, amber_glow, 14)
    draw_glow_circle(surface, (int(center_x), int(core_y + height * 0.02)), 2, (255, 240, 180), 8)

    # ── Forward gun prongs flanking the chin ──────────────────────────────
    for side in (-1, 1):
        prong_x = center_x + side * width * 0.28
        pygame.draw.polygon(
            surface,
            obsidian,
            [
                (prong_x - side * width * 0.045, y + height * 0.66),
                (prong_x + side * width * 0.055, y + height * 0.67),
                (prong_x + side * width * 0.035, y + height * 0.86),
                (prong_x - side * width * 0.03, y + height * 0.85),
            ],
        )
        pygame.draw.line(
            surface,
            gold_trim,
            (prong_x - side * width * 0.03, y + height * 0.82),
            (prong_x + side * width * 0.035, y + height * 0.83),
            1,
        )
        draw_glow_circle(
            surface,
            (int(prong_x + side * width * 0.005), int(y + height * 0.86)),
            1,
            amber_core,
            5,
        )


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


def draw_boss_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0
) -> None:
    sprite = get_boss_sprite(width, height, health_ratio)
    size = sprite.get_width()
    surface.blit(sprite, (round(x) - size // 2, round(y) - size // 2))


def _draw_boss_ship(
    surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0
) -> None:
    """Armored alien dreadnought — domed carapace, siege-cannon wings, bioluminescent eye.

    The boss faces down-screen toward the player (matching its facing-vector
    math): engine plumes trail at the top, the eye glares from the lower hull,
    and the mandible gun pylons align with the muzzle-flash anchor points.
    """
    center_x = x + width / 2
    hull_dark, hull_mid, hull_light, hull_highlight, bio_green, bio_bright = _boss_colors(health_ratio)
    void = (24, 12, 30)
    rib_dark = (34, 12, 36)

    # ── Rear engine plumes (top, trailing upward; bells drawn later) ──────
    for ex_frac, ey_frac in ((-0.20, 0.06), (0.20, 0.06), (0.0, -0.02)):
        ex = center_x + width * ex_frac
        ey = y + height * ey_frac
        for i in range(3):
            flame_y = ey + height * (0.05 - i * 0.05)
            flame_w = max(3, int(width * (0.11 - i * 0.025)))
            pygame.draw.ellipse(
                surface,
                (*bio_green, 130 - i * 40),
                (int(ex - flame_w // 2), int(flame_y), flame_w, max(2, int(height * 0.055))),
            )

    # ── Domed carapace (top armor shell) ──────────────────────────────────
    carapace_outer = [
        (center_x, y + height * 0.06),
        (center_x + width * 0.22, y + height * 0.10),
        (center_x + width * 0.42, y + height * 0.20),
        (center_x + width * 0.52, y + height * 0.34),
        (center_x + width * 0.44, y + height * 0.44),
        (center_x, y + height * 0.38),
        (center_x - width * 0.44, y + height * 0.44),
        (center_x - width * 0.52, y + height * 0.34),
        (center_x - width * 0.42, y + height * 0.20),
        (center_x - width * 0.22, y + height * 0.10),
    ]
    pygame.draw.polygon(surface, void, carapace_outer)
    carapace_mid = [
        (center_x, y + height * 0.11),
        (center_x + width * 0.19, y + height * 0.15),
        (center_x + width * 0.35, y + height * 0.23),
        (center_x + width * 0.43, y + height * 0.33),
        (center_x + width * 0.37, y + height * 0.40),
        (center_x, y + height * 0.35),
        (center_x - width * 0.37, y + height * 0.40),
        (center_x - width * 0.43, y + height * 0.33),
        (center_x - width * 0.35, y + height * 0.23),
        (center_x - width * 0.19, y + height * 0.15),
    ]
    pygame.draw.polygon(surface, hull_dark, carapace_mid)
    carapace_top = [
        (center_x, y + height * 0.16),
        (center_x + width * 0.14, y + height * 0.19),
        (center_x + width * 0.24, y + height * 0.25),
        (center_x + width * 0.28, y + height * 0.31),
        (center_x + width * 0.20, y + height * 0.35),
        (center_x, y + height * 0.32),
        (center_x - width * 0.20, y + height * 0.35),
        (center_x - width * 0.28, y + height * 0.31),
        (center_x - width * 0.24, y + height * 0.25),
        (center_x - width * 0.14, y + height * 0.19),
    ]
    pygame.draw.polygon(surface, hull_mid, carapace_top)
    # Rim light along the dome apex and plate seams radiating downward.
    for side in (-1, 1):
        pygame.draw.line(
            surface,
            hull_highlight,
            (center_x, y + height * 0.065),
            (center_x + side * width * 0.30, y + height * 0.14),
            2,
        )
        pygame.draw.line(
            surface,
            rib_dark,
            (center_x, y + height * 0.12),
            (center_x + side * width * 0.25, y + height * 0.28),
            1,
        )
        # Bioluminescent dots trace the carapace seams.
        pygame.draw.circle(
            surface,
            (*bio_green, 90),
            (int(center_x + side * width * 0.13), int(y + height * 0.20)),
            1,
        )

    # ── Engine bells capping the carapace ─────────────────────────────────
    for ex_frac, ey_frac in ((-0.20, 0.06), (0.20, 0.06), (0.0, -0.02)):
        ex = center_x + width * ex_frac
        ey = y + height * ey_frac
        pygame.draw.polygon(
            surface,
            void,
            [
                (ex - width * 0.06, ey + height * 0.08),
                (ex + width * 0.06, ey + height * 0.08),
                (ex + width * 0.045, ey + height * 0.16),
                (ex - width * 0.045, ey + height * 0.16),
            ],
        )
        draw_glow_circle(surface, (int(ex), int(ey + height * 0.09)), 3, bio_green, 8)

    # ── Siege wings with downward-angled cannons ──────────────────────────
    for side in (-1, 1):
        wing_outer = [
            (center_x + side * width * 0.34, y + height * 0.22),
            (center_x + side * width * 0.58, y + height * 0.24),
            (center_x + side * width * 0.95, y + height * 0.18),
            (center_x + side * width * 1.02, y + height * 0.34),
            (center_x + side * width * 0.90, y + height * 0.54),
            (center_x + side * width * 0.48, y + height * 0.60),
            (center_x + side * width * 0.30, y + height * 0.46),
        ]
        pygame.draw.polygon(surface, void, wing_outer)
        wing_mid = [
            (center_x + side * width * 0.38, y + height * 0.27),
            (center_x + side * width * 0.57, y + height * 0.29),
            (center_x + side * width * 0.86, y + height * 0.24),
            (center_x + side * width * 0.92, y + height * 0.35),
            (center_x + side * width * 0.82, y + height * 0.49),
            (center_x + side * width * 0.48, y + height * 0.54),
            (center_x + side * width * 0.35, y + height * 0.43),
        ]
        pygame.draw.polygon(surface, hull_dark, wing_mid)
        wing_plate = [
            (center_x + side * width * 0.42, y + height * 0.32),
            (center_x + side * width * 0.56, y + height * 0.33),
            (center_x + side * width * 0.76, y + height * 0.30),
            (center_x + side * width * 0.81, y + height * 0.37),
            (center_x + side * width * 0.74, y + height * 0.45),
            (center_x + side * width * 0.50, y + height * 0.48),
            (center_x + side * width * 0.40, y + height * 0.41),
        ]
        pygame.draw.polygon(surface, hull_mid, wing_plate)
        # Rim light on the wing's upper edge, plus a bio-lume strip.
        pygame.draw.line(
            surface,
            hull_highlight,
            (center_x + side * width * 0.56, y + height * 0.27),
            (center_x + side * width * 0.90, y + height * 0.22),
            2,
        )
        pygame.draw.line(
            surface,
            bio_green,
            (center_x + side * width * 0.48, y + height * 0.42),
            (center_x + side * width * 0.72, y + height * 0.38),
            1,
        )
        # Siege cannon barrel angled down toward the player.
        barrel_x = center_x + side * width * 0.70
        pygame.draw.polygon(
            surface,
            rib_dark,
            [
                (barrel_x - side * width * 0.05, y + height * 0.50),
                (barrel_x + side * width * 0.06, y + height * 0.49),
                (barrel_x + side * width * 0.08, y + height * 0.74),
                (barrel_x - side * width * 0.03, y + height * 0.75),
            ],
        )
        pygame.draw.line(
            surface,
            hull_highlight,
            (barrel_x - side * width * 0.03, y + height * 0.71),
            (barrel_x + side * width * 0.075, y + height * 0.70),
            1,
        )
        draw_glow_circle(
            surface,
            (int(barrel_x + side * width * 0.025), int(y + height * 0.76)),
            2,
            bio_green,
            8,
        )

    # ── Main hull teardrop with ribbed armor ──────────────────────────────
    hull = [
        (center_x, y + height * 0.34),
        (center_x + width * 0.22, y + height * 0.42),
        (center_x + width * 0.30, y + height * 0.58),
        (center_x + width * 0.22, y + height * 0.78),
        (center_x + width * 0.10, y + height * 0.94),
        (center_x, y + height * 1.00),
        (center_x - width * 0.10, y + height * 0.94),
        (center_x - width * 0.22, y + height * 0.78),
        (center_x - width * 0.30, y + height * 0.58),
        (center_x - width * 0.22, y + height * 0.42),
    ]
    pygame.draw.polygon(surface, hull_dark, hull)
    hull_inner = [
        (center_x, y + height * 0.40),
        (center_x + width * 0.16, y + height * 0.47),
        (center_x + width * 0.21, y + height * 0.60),
        (center_x + width * 0.15, y + height * 0.76),
        (center_x + width * 0.065, y + height * 0.88),
        (center_x, y + height * 0.93),
        (center_x - width * 0.065, y + height * 0.88),
        (center_x - width * 0.15, y + height * 0.76),
        (center_x - width * 0.21, y + height * 0.60),
        (center_x - width * 0.16, y + height * 0.47),
    ]
    pygame.draw.polygon(surface, hull_mid, hull_inner)
    # Dark chitin spine and rib seams across the lower hull.
    pygame.draw.polygon(
        surface,
        rib_dark,
        [
            (center_x, y + height * 0.44),
            (center_x + width * 0.07, y + height * 0.58),
            (center_x + width * 0.05, y + height * 0.80),
            (center_x, y + height * 0.90),
            (center_x - width * 0.05, y + height * 0.80),
            (center_x - width * 0.07, y + height * 0.58),
        ],
    )
    for i in range(3):
        line_y = y + height * (0.80 + i * 0.065)
        half = width * (0.16 - i * 0.045)
        pygame.draw.line(surface, rib_dark, (center_x - half, line_y), (center_x + half, line_y), 1)
    # Flank highlight ridge (light from above-left).
    pygame.draw.line(
        surface,
        hull_light,
        (center_x - width * 0.10, y + height * 0.46),
        (center_x - width * 0.14, y + height * 0.70),
        2,
    )

    # ── Armored brow and the great bioluminescent eye ─────────────────────
    brow = [
        (center_x - width * 0.26, y + height * 0.52),
        (center_x - width * 0.09, y + height * 0.46),
        (center_x + width * 0.09, y + height * 0.46),
        (center_x + width * 0.26, y + height * 0.52),
        (center_x + width * 0.16, y + height * 0.60),
        (center_x - width * 0.16, y + height * 0.60),
    ]
    pygame.draw.polygon(surface, void, brow)
    pygame.draw.line(surface, hull_highlight, brow[0], brow[1], 2)
    pygame.draw.line(surface, hull_highlight, brow[2], brow[3], 2)

    eye_y = y + height * 0.66
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 13, bio_green, 36)
    draw_glow_circle(surface, (int(center_x), int(eye_y)), 8, bio_bright, 22)
    # Vertical slit pupil gives the eye a predatory, reptilian read.
    pygame.draw.ellipse(
        surface,
        (8, 18, 6),
        (int(center_x - width * 0.022), int(eye_y - height * 0.05), max(2, int(width * 0.044)), int(height * 0.10)),
    )
    pygame.draw.circle(surface, (240, 255, 230), (int(center_x - width * 0.03), int(eye_y - height * 0.04)), 2)

    # ── Secondary eyes flanking the great eye ─────────────────────────────
    for sx, sy_frac in [
        (center_x - width * 0.17, 0.60),
        (center_x + width * 0.17, 0.60),
        (center_x - width * 0.10, 0.78),
        (center_x + width * 0.10, 0.78),
    ]:
        draw_glow_circle(surface, (int(sx), int(y + height * sy_frac)), 3, bio_green, 10)
        draw_glow_circle(surface, (int(sx), int(y + height * sy_frac)), 1, bio_bright, 5)

    # ── Mandible gun pylons (tips align with muzzle-flash anchors) ────────
    for side in (-1, 1):
        muzzle_x = center_x + side * width * 0.34
        pygame.draw.polygon(
            surface,
            void,
            [
                (muzzle_x - side * width * 0.055, y + height * 0.70),
                (muzzle_x + side * width * 0.055, y + height * 0.70),
                (muzzle_x + side * width * 0.035, y + height * 1.04),
                (muzzle_x - side * width * 0.035, y + height * 1.04),
            ],
        )
        pygame.draw.polygon(
            surface,
            hull_mid,
            [
                (muzzle_x - side * width * 0.030, y + height * 0.74),
                (muzzle_x + side * width * 0.030, y + height * 0.74),
                (muzzle_x + side * width * 0.018, y + height * 0.98),
                (muzzle_x - side * width * 0.018, y + height * 0.98),
            ],
        )
        pygame.draw.line(
            surface,
            hull_highlight,
            (muzzle_x - side * width * 0.033, y + height * 1.00),
            (muzzle_x + side * width * 0.033, y + height * 1.00),
            1,
        )
        draw_glow_circle(surface, (int(muzzle_x), int(y + height * 1.05)), 3, bio_green, 10)


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
