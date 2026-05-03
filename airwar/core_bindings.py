"""Rust 核心模块的 Python 绑定"""
import logging
import os

# 静默模式：检查 RUST_AVAILABLE 环境变量
_RUST_SILENT = os.environ.get("RUST_SILENT", "0") == "1"

try:
    from airwar_core import (
        # Vector2 functions
        vec2_length,
        vec2_normalize,
        vec2_add,
        vec2_sub,
        vec2_dot,
        vec2_scale,
        vec2_distance,
        vec2_angle,
        vec2_from_angle,
        vec2_lerp,
        vec2_clamp_length,
        # Collision functions
        batch_collide_bullets_vs_entities,
        PersistentSpatialHash,
        # Movement functions
        update_movement,
        batch_update_movements,
        compute_boss_attack,
        # Particle functions
        batch_update_particles,
        generate_explosion_particles,
        # Sprite functions
        create_single_bullet_glow,
        create_spread_bullet_glow,
        create_laser_bullet_glow,
        create_explosive_missile_glow,
        create_glow_circle,
        # Bullet functions
        batch_update_bullets,
    )
    RUST_AVAILABLE = True
except ImportError as e:
    if not _RUST_SILENT:
        logging.warning(f"Rust核心模块不可用，将使用纯Python实现: {e}")
    RUST_AVAILABLE = False
    # Fallback imports handled by caller

__all__ = [
    # Vector2 functions
    'vec2_length',
    'vec2_normalize',
    'vec2_add',
    'vec2_sub',
    'vec2_dot',
    'vec2_scale',
    'vec2_distance',
    'vec2_angle',
    'vec2_from_angle',
    'vec2_lerp',
    'vec2_clamp_length',
    # Collision functions
    'batch_collide_bullets_vs_entities',
    'PersistentSpatialHash',
    # Movement functions
    'update_movement',
    'batch_update_movements',
    'compute_boss_attack',
    # Particle functions
    'batch_update_particles',
    'generate_explosion_particles',
    # Sprite functions
    'create_single_bullet_glow',
    'create_spread_bullet_glow',
    'create_laser_bullet_glow',
    'create_explosive_missile_glow',
    'create_glow_circle',
    # Bullet functions
    'batch_update_bullets',
    'RUST_AVAILABLE',
]
