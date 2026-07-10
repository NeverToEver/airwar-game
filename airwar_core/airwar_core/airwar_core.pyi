"""Type stubs for the ``airwar_core`` native extension module.

These signatures mirror the Rust ``pyfunction`` exports in
``airwar_core/src/lib.rs``. They are consumed by mypy when the compiled
extension is not available and document the FFI boundary for callers in
``airwar.core_bindings``.
"""

from __future__ import annotations

# ---- Vector2 -----------------------------------------------------------------

def vec2_length(x: float, y: float) -> float: ...
def vec2_normalize(x: float, y: float) -> tuple[float, float]: ...
def vec2_add(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]: ...
def vec2_sub(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]: ...
def vec2_dot(x1: float, y1: float, x2: float, y2: float) -> float: ...
def vec2_scale(x: float, y: float, scalar: float) -> tuple[float, float]: ...
def vec2_distance(x1: float, y1: float, x2: float, y2: float) -> float: ...
def vec2_angle(x: float, y: float) -> float: ...
def vec2_from_angle(angle: float, length: float) -> tuple[float, float]: ...
def vec2_lerp(x1: float, y1: float, x2: float, y2: float, t: float) -> tuple[float, float]: ...
def vec2_clamp_length(x: float, y: float, max_length: float) -> tuple[float, float]: ...

# ---- Collision ---------------------------------------------------------------

def batch_collide_bullets_vs_entities(
    bullets: list[tuple[int, float, float, float, float]],
    enemies: list[tuple[int, float, float, float, float]],
    cell_size: int,
) -> list[tuple[int, int]]: ...

# ---- Movement ----------------------------------------------------------------

def update_movement(
    move_type: int,
    timer: float,
    active_x: float,
    active_y: float,
    move_range_x: float,
    move_range_y: float,
    offset: float,
    amplitude: float,
    frequency: float,
    speed: float,
    direction: float,
    zigzag_interval: float,
    spiral_radius: float,
    current_x: float,
    current_y: float,
    noise_scale_x: float,
    noise_scale_y: float,
    noise_amplitude_x: float,
    noise_amplitude_y: float,
    noise_seed: int,
) -> tuple[float, float, float]: ...

def batch_update_movements(
    base_params: list[
        tuple[int, float, float, float, float, float, float, float, float, float, float, float]
    ],
    extra_params: list[tuple[float, float, float, float, float, float, float, int]],
) -> list[tuple[float, float, float]]: ...

def batch_update_movements_buf(
    base_buf: bytes,
    extra_buf: bytes,
) -> list[tuple[float, float, float]]: ...

def batch_hallucinated_enemy_centers(
    enemies: list[tuple[float, float, int]],
    player_center: tuple[float, float] | None,
    frame: int,
    strength: float,
    lunge_scale: float,
) -> list[tuple[float, float]]: ...

def find_nearest_target(
    candidates: list[tuple[int, float, float]],
    query_x: float,
    query_y: float,
) -> int | None: ...

def find_target_in_direction(
    candidates: list[tuple[int, float, float]],
    origin_x: float,
    origin_y: float,
    move_x: float,
    move_y: float,
    direction_cone_dot: float,
    exclude_id: int | None,
) -> int | None: ...

# ---- Particles ---------------------------------------------------------------

def batch_update_particles(
    particles: list[tuple[float, float, float, float, int, int, float]],
    dt: float,
) -> list[tuple[float, float, float, float, int, float, bool]]: ...

def generate_explosion_particles(
    center_x: float,
    center_y: float,
    particle_count: int,
    life_min: int,
    life_max: int,
    speed_min: float,
    speed_max: float,
    size_min: float,
    size_max: float,
) -> list[tuple[float, float, float, float, int, int, float]]: ...

def batch_render_particles(
    particles: list[tuple[float, float, float, float, float, int, int, int]],
    screen_width: int,
    screen_height: int,
) -> bytes: ...

# ---- Sprites -----------------------------------------------------------------

def create_single_bullet_glow(width: float, height: float) -> bytes: ...
def create_spread_bullet_glow(radius: float) -> bytes: ...
def create_laser_bullet_glow(height: float) -> bytes: ...
def create_explosive_missile_glow(width: float, height: float) -> bytes: ...
def create_glow_circle(
    radius: int,
    r: int,
    g: int,
    b: int,
    glow_radius: int,
) -> bytes: ...

# ---- Starfield ---------------------------------------------------------------

def compute_starfield_positions(
    stars: list[tuple[float, float, float, float, float, float]],
    scroll_offset: float,
    screen_w: float,
    screen_h: float,
    time: float,
    sin_table: list[float],
    sin_table_size: int,
    sin_table_mask: int,
    glow_threshold: int,
    glow_alpha_divisor: int,
    glow_alpha_cap: int,
) -> list[tuple[int, int, int, int, bool, int]]: ...

# ---- Bullets -----------------------------------------------------------------

def batch_update_bullets(
    bullets: list[tuple[int, float, float, float, float, int, bool, float]],
) -> list[tuple[int, float, float, bool]]: ...

def batch_update_bullets_buf(buf: bytes) -> list[tuple[int, float, float, bool]]: ...

__all__ = [
    "batch_collide_bullets_vs_entities",
    "batch_hallucinated_enemy_centers",
    "batch_render_particles",
    "batch_update_bullets",
    "batch_update_bullets_buf",
    "batch_update_movements",
    "batch_update_movements_buf",
    "batch_update_particles",
    "compute_starfield_positions",
    "create_explosive_missile_glow",
    "create_glow_circle",
    "create_laser_bullet_glow",
    "create_single_bullet_glow",
    "create_spread_bullet_glow",
    "find_nearest_target",
    "find_target_in_direction",
    "generate_explosion_particles",
    "update_movement",
    "vec2_add",
    "vec2_angle",
    "vec2_clamp_length",
    "vec2_distance",
    "vec2_dot",
    "vec2_from_angle",
    "vec2_length",
    "vec2_lerp",
    "vec2_normalize",
    "vec2_scale",
    "vec2_sub",
]
