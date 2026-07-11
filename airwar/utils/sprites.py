"""Sprites — rendering helpers for ships, bullets, glow effects, and ripples.

This module re-exports from the sub-modules for backward compatibility:
- _sprites_common: caches, glow circles, gradients, ripples, prewarm
- _sprites_ships: player, enemy, boss ship sprites
- _sprites_bullets: single, spread, laser, explosive missile bullets
"""

from ._sprites_bullets import (
    draw_bullet,
    draw_explosive_missile,
    draw_laser_bullet,
    draw_single_bullet,
    draw_spread_bullet,
)
from ._sprites_common import (
    create_gradient_surface,
    draw_glow_circle,
    draw_ripple,
    prewarm_glow_caches,
)
from ._sprites_ships import (
    draw_boss_ship,
    draw_elite_enemy_ship,
    draw_enemy_ship,
    draw_player_ship,
    get_boss_sprite,
    get_elite_enemy_sprite,
    get_enemy_sprite,
    get_player_sprite,
    prewarm_ship_sprite_caches,
)

__all__ = [
    "create_gradient_surface",
    "draw_boss_ship",
    "draw_bullet",
    "draw_elite_enemy_ship",
    "draw_enemy_ship",
    "draw_explosive_missile",
    "draw_glow_circle",
    "draw_laser_bullet",
    "draw_player_ship",
    "draw_ripple",
    "draw_single_bullet",
    "draw_spread_bullet",
    "get_boss_sprite",
    "get_elite_enemy_sprite",
    "get_enemy_sprite",
    "get_player_sprite",
    "prewarm_glow_caches",
    "prewarm_ship_sprite_caches",
]
