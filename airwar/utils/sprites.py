"""Sprites — rendering helpers for ships, bullets, glow effects, and ripples.

This module re-exports from the sub-modules for backward compatibility:
- _sprites_common: caches, glow circles, gradients, ripples, prewarm
- _sprites_ships: player, enemy, boss ship sprites
- _sprites_bullets: single, spread, laser, explosive missile bullets
"""
from ._sprites_common import (
    RUST_AVAILABLE,
    _bytes_to_surface,
    _glow_circle_cache,
    _single_bullet_glow_cache,
    _spread_bullet_glow_cache,
    _laser_bullet_glow_cache,
    _ripple_surface_cache,
    _explosive_missile_cache,
    prewarm_glow_caches,
    create_gradient_surface,
    draw_glow_circle,
    draw_ripple,
)
from ._sprites_ships import (
    _player_sprite_cache,
    _enemy_sprite_cache,
    _boss_sprite_cache,
    _elite_sprite_cache,
    get_player_sprite,
    draw_player_ship,
    get_enemy_sprite,
    draw_enemy_ship,
    get_elite_enemy_sprite,
    draw_elite_enemy_ship,
    get_boss_sprite,
    draw_boss_ship,
    prewarm_ship_sprite_caches,
)
from ._sprites_bullets import (
    draw_bullet,
    draw_single_bullet,
    draw_spread_bullet,
    draw_laser_bullet,
    draw_explosive_missile,
)

__all__ = [
    'RUST_AVAILABLE',
    '_bytes_to_surface',
    '_glow_circle_cache',
    '_single_bullet_glow_cache',
    '_spread_bullet_glow_cache',
    '_laser_bullet_glow_cache',
    '_ripple_surface_cache',
    '_explosive_missile_cache',
    '_player_sprite_cache',
    '_enemy_sprite_cache',
    '_boss_sprite_cache',
    'prewarm_glow_caches',
    'create_gradient_surface',
    'draw_glow_circle',
    'draw_ripple',
    'get_player_sprite',
    'draw_player_ship',
    'get_enemy_sprite',
    'draw_enemy_ship',
    'get_boss_sprite',
    'draw_boss_ship',
    'prewarm_ship_sprite_caches',
    'draw_bullet',
    'draw_single_bullet',
    'draw_spread_bullet',
    'draw_laser_bullet',
    'draw_explosive_missile',
]
