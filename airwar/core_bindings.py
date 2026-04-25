"""Rust 核心模块的 Python 绑定"""
try:
    from airwar_core import (
        # Vector2 functions
        vec2_length,
        vec2_normalize,
        vec2_add,
        vec2_sub,
        vec2_dot,
        vec2_cross,
        vec2_scale,
        vec2_distance,
        vec2_length_squared,
        vec2_distance_squared,
        vec2_angle,
        vec2_from_angle,
        vec2_lerp,
        vec2_clamp_length,
        # Collision functions
        spatial_hash_collide,
        spatial_hash_collide_single,
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Fallback imports handled by caller

__all__ = [
    # Vector2 functions
    'vec2_length',
    'vec2_normalize',
    'vec2_add',
    'vec2_sub',
    'vec2_dot',
    'vec2_cross',
    'vec2_scale',
    'vec2_distance',
    'vec2_length_squared',
    'vec2_distance_squared',
    'vec2_angle',
    'vec2_from_angle',
    'vec2_lerp',
    'vec2_clamp_length',
    # Collision functions
    'spatial_hash_collide',
    'spatial_hash_collide_single',
    'RUST_AVAILABLE',
]