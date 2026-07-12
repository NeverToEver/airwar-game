"""Python bindings for the optional Rust core module."""

from __future__ import annotations

import inspect
import logging
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Mypy cannot inspect the compiled ``airwar_core`` extension, so we
    # re-declare the exported surface here. At runtime the functions are
    # imported from the native module (or replaced by the pure-Python
    # fallbacks below).
    from airwar_core import (
        batch_collide_bullets_vs_entities,
        batch_hallucinated_enemy_centers,
        batch_render_particles,
        batch_update_bullets,
        batch_update_bullets_buf,
        batch_update_movements,
        batch_update_movements_buf,
        batch_update_particles,
        compute_starfield_positions,
        create_explosive_missile_glow,
        create_glow_circle,
        create_laser_bullet_glow,
        create_single_bullet_glow,
        create_spread_bullet_glow,
        find_nearest_target,
        find_target_in_direction,
        generate_explosion_particles,
        update_movement,
        vec2_add,
        vec2_angle,
        vec2_clamp_length,
        vec2_distance,
        vec2_dot,
        vec2_from_angle,
        vec2_length,
        vec2_lerp,
        vec2_normalize,
        vec2_scale,
        vec2_sub,
    )

_logger = logging.getLogger(__name__)

_RUST_NAMES = (
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
)

# Expected Python-visible parameter counts for the Rust exports. Used to
# detect ABI/signature mismatches beyond mere function existence.
_RUST_SIGNATURES: dict[str, int] = {
    "batch_collide_bullets_vs_entities": 3,
    "batch_hallucinated_enemy_centers": 5,
    "batch_render_particles": 3,
    "batch_update_bullets": 1,
    "batch_update_bullets_buf": 1,
    "batch_update_movements": 2,
    "batch_update_movements_buf": 2,
    "batch_update_particles": 2,
    "compute_starfield_positions": 11,
    "create_explosive_missile_glow": 2,
    "create_glow_circle": 5,
    "create_laser_bullet_glow": 1,
    "create_single_bullet_glow": 2,
    "create_spread_bullet_glow": 1,
    "find_nearest_target": 3,
    "find_target_in_direction": 7,
    "generate_explosion_particles": 9,
    "update_movement": 20,
    "vec2_add": 4,
    "vec2_angle": 2,
    "vec2_clamp_length": 3,
    "vec2_distance": 4,
    "vec2_dot": 4,
    "vec2_from_angle": 2,
    "vec2_length": 2,
    "vec2_lerp": 5,
    "vec2_normalize": 2,
    "vec2_scale": 3,
    "vec2_sub": 4,
}

try:
    import airwar_core

    _missing = [n for n in _RUST_NAMES if not hasattr(airwar_core, n)]
    if _missing:
        _logger.error("airwar_core missing functions: %s; falling back to pure Python", _missing)
        raise ImportError(f"airwar_core missing: {_missing}")

    _abi_mismatches: list[str] = []
    for _name, _expected_count in _RUST_SIGNATURES.items():
        try:
            _sig = inspect.signature(getattr(airwar_core, _name))
        except ValueError:
            # Some native modules do not expose inspectable signatures.
            continue
        _params = [p for p in _sig.parameters.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        if len(_params) != _expected_count:
            _abi_mismatches.append(f"{_name}(expected {_expected_count}, got {len(_params)})")
    if _abi_mismatches:
        _logger.error("airwar_core ABI mismatch: %s; falling back to pure Python", _abi_mismatches)
        raise ImportError(f"airwar_core ABI mismatch: {_abi_mismatches}")

    from airwar_core import (
        batch_collide_bullets_vs_entities,
        batch_hallucinated_enemy_centers,
        batch_render_particles,
        batch_update_bullets,
        batch_update_bullets_buf,
        batch_update_movements,
        batch_update_movements_buf,
        batch_update_particles,
        compute_starfield_positions,
        create_explosive_missile_glow,
        create_glow_circle,
        create_laser_bullet_glow,
        create_single_bullet_glow,
        create_spread_bullet_glow,
        find_nearest_target,
        find_target_in_direction,
        generate_explosion_particles,
        update_movement,
        vec2_add,
        vec2_angle,
        vec2_clamp_length,
        vec2_distance,
        vec2_dot,
        vec2_from_angle,
        vec2_length,
        vec2_lerp,
        vec2_normalize,
        vec2_scale,
        vec2_sub,
    )

    RUST_AVAILABLE = True
except (ImportError, OSError):
    RUST_AVAILABLE = False

    def vec2_length(x: float, y: float) -> float:
        return math.sqrt(x * x + y * y)

    def vec2_normalize(x: float, y: float) -> tuple[float, float]:
        length = vec2_length(x, y)
        if length > 0:
            return x / length, y / length
        return 0.0, 0.0

    def vec2_add(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
        return x1 + x2, y1 + y2

    def vec2_sub(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
        return x1 - x2, y1 - y2

    def vec2_dot(x1: float, y1: float, x2: float, y2: float) -> float:
        return x1 * x2 + y1 * y2

    def vec2_scale(x: float, y: float, scalar: float) -> tuple[float, float]:
        return x * scalar, y * scalar

    def vec2_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1))

    def vec2_angle(x: float, y: float) -> float:
        return math.atan2(y, x)

    def vec2_from_angle(angle: float, length: float) -> tuple[float, float]:
        return math.cos(angle) * length, math.sin(angle) * length

    def vec2_lerp(x1: float, y1: float, x2: float, y2: float, t: float) -> tuple[float, float]:
        return x1 + (x2 - x1) * t, y1 + (y2 - y1) * t

    def vec2_clamp_length(x: float, y: float, max_length: float) -> tuple[float, float]:
        max_length = abs(max_length)
        length_sq = x * x + y * y
        max_sq = max_length * max_length
        if length_sq > max_sq and length_sq > 0:
            length = math.sqrt(length_sq)
            return x / length * max_length, y / length * max_length
        return x, y

    class _AABB:
        __slots__ = ("max_x", "max_y", "min_x", "min_y")

        def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
            self.min_x = min_x
            self.min_y = min_y
            self.max_x = max_x
            self.max_y = max_y

        @classmethod
        def from_xy_size(cls, x: float, y: float, width: float, height: float) -> _AABB:
            return cls(x, y, x + width, y + height)

        @classmethod
        def from_xy_half_size(cls, x: float, y: float, half_size: float) -> _AABB:
            return cls(x - half_size, y - half_size, x + half_size, y + half_size)

        def intersects(self, other: _AABB) -> bool:
            return (
                self.min_x < other.max_x
                and self.max_x > other.min_x
                and self.min_y < other.max_y
                and self.max_y > other.min_y
            )

    def batch_collide_bullets_vs_entities(
        bullets: list[tuple[int, float, float, float, float]],
        enemies: list[tuple[int, float, float, float, float]],
        cell_size: int,
    ) -> list[tuple[int, int]]:
        if not bullets or not enemies or cell_size <= 0:
            return []

        enemy_bounds = [
            (enemy_id, _AABB.from_xy_size(x, y, width, height)) for enemy_id, x, y, width, height in enemies
        ]
        hits: list[tuple[int, int]] = []
        for bullet_id, bx, by, bwidth, bheight in bullets:
            bullet_bounds = _AABB.from_xy_size(bx, by, bwidth, bheight)
            for enemy_id, bounds in enemy_bounds:
                if bullet_bounds.intersects(bounds):
                    hits.append((bullet_id, enemy_id))
        return hits

    def _smooth_noise(x: float, seed: int) -> float:
        int_x = int(x)
        frac_x = x - int_x

        v1 = math.sin(int_x * 1.0 + seed * 0.1) * 0.5
        v2 = math.sin(int_x * 2.3 + seed * 0.2) * 0.3
        v3 = math.sin(int_x * 4.7 + seed * 0.3) * 0.2
        v4 = math.sin((int_x + 1) * 1.0 + seed * 0.1) * 0.5
        v5 = math.sin((int_x + 1) * 2.3 + seed * 0.2) * 0.3
        v6 = math.sin((int_x + 1) * 4.7 + seed * 0.3) * 0.2

        blend = 0.5 - 0.5 * math.cos(frac_x * math.pi)
        value = (v1 + v2 + v3) + ((v4 + v5 + v6) - (v1 + v2 + v3)) * blend
        return max(-1.0, min(1.0, value * 1.2))

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
    ) -> list[tuple[int, int, int, int, bool, int]]:
        """Python fallback for `compute_starfield_positions`.

        Mirrors the Rust implementation exactly so visual output is
        identical regardless of which path runs.
        """
        if not sin_table or glow_alpha_divisor == 0:
            return []
        scale = sin_table_size / math.tau
        results: list[tuple[int, int, int, int, bool, int]] = []
        for x_frac, y_frac, size, brightness, twinkle_speed, twinkle_offset in stars:
            y_norm = (y_frac + scroll_offset) % 1.0
            x = int(x_frac * screen_w)
            y_pos = int(y_norm * screen_h)
            phase = (time * twinkle_speed + twinkle_offset) * scale
            idx = int(phase) % len(sin_table)
            twinkle = sin_table[idx]
            b = int(brightness * (0.5 + 0.5 * twinkle) * 255.0)
            core_b = max(0, min(255, b))
            size_int = max(1, int(size))
            has_glow = b > glow_threshold
            glow_alpha = (b // glow_alpha_divisor) if has_glow else 0
            if glow_alpha > glow_alpha_cap:
                glow_alpha = glow_alpha_cap
            results.append((x, y_pos, core_b, size_int, has_glow, glow_alpha))
        return results

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
    ) -> tuple[float, float, float]:
        del amplitude, spiral_radius
        if (
            not math.isfinite(active_x)
            or not math.isfinite(active_y)
            or not math.isfinite(current_x)
            or not math.isfinite(current_y)
        ):
            return (current_x, current_y, timer)
        if move_type == 1:
            new_timer = timer + 1.0
            return (
                active_x + math.sin(new_timer * frequency + offset) * move_range_x,
                active_y + math.sin(new_timer * frequency * 0.5) * move_range_y,
                new_timer,
            )
        if move_type == 2:
            new_timer = timer + 1.0
            interval = int(zigzag_interval) or 1
            actual_direction = -direction if int(new_timer) % interval == 0 and new_timer > 0.0 else direction
            return (
                active_x + actual_direction * speed,
                active_y + math.sin(new_timer * 0.1) * (move_range_y * 0.5),
                new_timer,
            )
        if move_type == 3:
            new_timer = timer + 1.0
            return (
                active_x + math.sin(new_timer * 0.05) * (move_range_x * 0.3),
                active_y + math.sin(new_timer * 0.03) * (move_range_y * 0.3),
                new_timer,
            )
        if move_type == 4:
            new_timer = timer + 1.0
            value = new_timer * 0.08
            return (
                active_x + math.sin(value) * move_range_x,
                active_y + math.sin(value * 0.7) * (move_range_y * 0.5),
                new_timer,
            )
        if move_type == 5:
            new_timer = timer + 1.0
            return (
                active_x + math.cos(new_timer * frequency) * (move_range_x * 0.5),
                active_y + math.sin(new_timer * 2.0 * frequency) * (move_range_y * 0.3),
                new_timer,
            )
        if move_type in (6, 7):
            increment = max(speed, 0.001)
            new_timer = timer + increment
            noise_x = _smooth_noise(new_timer * noise_scale_x, noise_seed) * noise_amplitude_x
            noise_y = _smooth_noise(new_timer * noise_scale_y, noise_seed + 500) * noise_amplitude_y
            if move_type == 7:
                noise_y += 0.15
                target_x = active_x + noise_x * 96.0
                target_y = active_y + noise_y * 60.0
                max_delta = 8.0
            else:
                target_x = active_x + noise_x * 80.0
                target_y = active_y + noise_y * 50.0
                max_delta = 6.0
            dx = target_x - current_x
            dy = target_y - current_y
            x = current_x + max_delta * math.copysign(1.0, dx) if abs(dx) > max_delta else target_x
            y = current_y + max_delta * math.copysign(1.0, dy) if abs(dy) > max_delta else target_y
            return x, y, new_timer

        new_timer = timer + 1.0
        return active_x, active_y + math.sin(new_timer * 0.05) * (move_range_y * 0.3), new_timer

    def batch_update_movements(
        base_params: list[tuple[int, float, float, float, float, float, float, float, float, float, float, float]],
        extra_params: list[tuple[float, float, float, float, float, float, float, int]],
    ) -> list[tuple[float, float, float]]:
        if len(base_params) != len(extra_params):
            raise ValueError("base_params and extra_params must have same length")
        return [
            update_movement(
                move_type,
                timer,
                active_x,
                active_y,
                move_range_x,
                move_range_y,
                offset,
                amplitude,
                frequency,
                speed,
                direction,
                zigzag_interval,
                spiral_radius,
                current_x,
                current_y,
                noise_scale_x,
                noise_scale_y,
                noise_amplitude_x,
                noise_amplitude_y,
                noise_seed,
            )
            for (
                (
                    move_type,
                    timer,
                    active_x,
                    active_y,
                    move_range_x,
                    move_range_y,
                    offset,
                    amplitude,
                    frequency,
                    speed,
                    direction,
                    zigzag_interval,
                ),
                (
                    spiral_radius,
                    current_x,
                    current_y,
                    noise_scale_x,
                    noise_scale_y,
                    noise_amplitude_x,
                    noise_amplitude_y,
                    noise_seed,
                ),
            ) in zip(base_params, extra_params, strict=False)
        ]

    def batch_update_movements_buf(base_buf: bytes, extra_buf: bytes) -> list[tuple[float, float, float]]:
        import struct

        if len(base_buf) % 48 != 0 or len(extra_buf) < (len(base_buf) // 48) * 32:
            raise ValueError("movement buffers length mismatch")
        count = len(base_buf) // 48
        base_fmt = "<Bxxxfffffffffff"  # u8 + pad3 + 11*f32 = 48 bytes
        extra_fmt = "<fffffffI"  # 7*f32 + i32 = 32 bytes
        base_list = []
        extra_list = []
        for i in range(count):
            base_list.append(struct.unpack_from(base_fmt, base_buf, i * 48))
            extra_list.append(struct.unpack_from(extra_fmt, extra_buf, i * 32))
        return batch_update_movements(base_list, extra_list)

    def batch_update_particles(
        particles: list[tuple[float, float, float, float, int, int, float]],
        dt: float,
    ) -> list[tuple[float, float, float, float, int, float, bool]]:
        return [
            (x + vx * dt, y + vy * dt, vx * 0.98, vy * 0.98, life - 1, size, life - 1 > 0)
            for x, y, vx, vy, life, _max_life, size in particles
        ]

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
    ) -> list[tuple[float, float, float, float, int, int, float]]:
        particles = []
        for _ in range(particle_count):
            angle = random.random() * math.tau
            speed = speed_min + random.random() * (speed_max - speed_min)
            life = life_min + int(random.random() * max(0, life_max - life_min))
            size = size_min + random.random() * (size_max - size_min)
            particles.append((center_x, center_y, math.cos(angle) * speed, math.sin(angle) * speed, life, life, size))
        return particles

    def batch_render_particles(
        particles: list[tuple[float, float, float, float, float, int, int, int]],
        screen_width: int,
        screen_height: int,
    ) -> bytes:
        w, h = screen_width, screen_height
        data = bytearray(w * h * 4)
        for px, py, size, glow_radius, alpha, r, g, b in particles:
            cx, cy = int(px), int(py)
            total_radius = int(size + glow_radius)
            a_base = max(0.0, min(1.0, alpha))
            r = max(0, min(255, int(r)))
            g = max(0, min(255, int(g)))
            b = max(0, min(255, int(b)))
            for dy in range(-total_radius, total_radius + 1):
                for dx in range(-total_radius, total_radius + 1):
                    x, y = cx + dx, cy + dy
                    if x < 0 or x >= w or y < 0 or y >= h:
                        continue
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist <= size:
                        a = a_base
                    elif dist <= size + glow_radius:
                        t = 1.0 - (dist - size) / glow_radius
                        a = a_base * t * t
                    else:
                        continue
                    if a < 0.01:
                        continue
                    sa = int(a * 255)
                    idx = (y * w + x) * 4
                    data[idx] = min(255, data[idx] + int(r) * sa // 255)
                    data[idx + 1] = min(255, data[idx + 1] + int(g) * sa // 255)
                    data[idx + 2] = min(255, data[idx + 2] + int(b) * sa // 255)
                    data[idx + 3] = min(255, data[idx + 3] + sa)
        return bytes(data)

    def _set_pixel(data: bytearray, width: int, x: int, y: int, color: tuple[int, int, int], alpha: int) -> None:
        idx = (y * width + x) * 4
        data[idx] = max(0, min(255, color[0]))
        data[idx + 1] = max(0, min(255, color[1]))
        data[idx + 2] = max(0, min(255, color[2]))
        data[idx + 3] = max(0, min(255, alpha))

    def _fill_glow_circle(
        data: bytearray,
        width: int,
        height: int,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[int, int, int],
        glow_radius: float,
    ) -> None:
        min_x = max(0, int(cx - glow_radius - radius - 2.0))
        max_x = min(width, int(cx + glow_radius + radius + 2.0))
        min_y = max(0, int(cy - glow_radius - radius - 2.0))
        max_y = min(height, int(cy + glow_radius + radius + 2.0))
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                dist = math.sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy))
                if dist <= radius:
                    _set_pixel(data, width, x, y, color, 255)
                elif glow_radius > 0 and dist <= radius + glow_radius:
                    _set_pixel(data, width, x, y, color, int(80.0 * (1.0 - (dist - radius) / glow_radius)))

    def _fill_glow_ellipse(
        data: bytearray,
        width: int,
        height: int,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        color: tuple[int, int, int],
        alpha: int,
    ) -> None:
        if rx <= 0 or ry <= 0:
            return
        min_x = max(0, int(cx - rx - 1.0))
        max_x = min(width, int(cx + rx + 1.0))
        min_y = max(0, int(cy - ry - 1.0))
        max_y = min(height, int(cy + ry + 1.0))
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if ((x - cx) * (x - cx)) / (rx * rx) + ((y - cy) * (y - cy)) / (ry * ry) <= 1.0:
                    _set_pixel(data, width, x, y, color, alpha)

    def create_single_bullet_glow(width: float, height: float) -> bytes:
        if width <= 0.0 or height <= 0.0:
            return b""
        surf_w = int(width + 16.0)
        surf_h = int(height + 12.0)
        data = bytearray(surf_w * surf_h * 4)
        for i in range(6, 0, -1):
            _fill_glow_ellipse(
                data,
                surf_w,
                surf_h,
                surf_w / 2.0,
                surf_h / 2.0 + 2.0,
                width / 2.0 + i - 3.0,
                height / 2.0 + i * 0.5 - 1.0,
                (255, 200, 50),
                int((6 - i) * 30 / 5),
            )
        return bytes(data)

    def create_spread_bullet_glow(radius: float) -> bytes:
        if radius <= 0.0:
            return b""
        surf_size = int(radius * 4.0 + 8.0)
        data = bytearray(surf_size * surf_size * 4)
        cx = surf_size / 2.0
        cy = surf_size / 2.0
        steps = int(radius + 4.0)
        for i in range(steps, 0, -2):
            alpha = int((steps - i) * 40 / max(1, steps))
            r = float(i)
            _fill_glow_circle(data, surf_size, surf_size, cx, cy, r + 2.0, (255, 150, 50), 0.0)
            for y in range(max(0, int(cy - r - 2.0)), min(surf_size, int(cy + r + 2.0))):
                for x in range(max(0, int(cx - r - 2.0)), min(surf_size, int(cx + r + 2.0))):
                    dist = math.sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy))
                    if r < dist <= r + 2.0:
                        _set_pixel(data, surf_size, x, y, (255, 150, 50), alpha)
        return bytes(data)

    def create_laser_bullet_glow(height: float) -> bytes:
        if height <= 0.0:
            return b""
        surf_w = 24
        surf_h = int(height + 12.0)
        data = bytearray(surf_w * surf_h * 4)
        for i in range(10, 0, -2):
            alpha = int((10 - i) * 70 / 9)
            min_x = int(12.0 - i / 2.0)
            max_x = int(12.0 + i / 2.0)
            for x in range(max(0, min_x), min(surf_w, max_x)):
                for y in range(4, max(4, surf_h - 4)):
                    _set_pixel(data, surf_w, x, y, (255, 20, 40), alpha)
        return bytes(data)

    def create_explosive_missile_glow(width: float, height: float) -> bytes:
        if width <= 0.0 or height <= 0.0:
            return b""
        body_width = width * 0.8
        surf_w = int(body_width * 3.0 + 12.0)
        surf_h = int(height + 10.0)
        data = bytearray(surf_w * surf_h * 4)
        for i in range(6, 0, -1):
            _fill_glow_ellipse(
                data,
                surf_w,
                surf_h,
                surf_w / 2.0,
                height / 2.0 + 5.0,
                body_width / 2.0 + (6 - i) * 2.0,
                height / 2.0 + (6 - i) * 2.0,
                (255, 80, 20),
                int((6 - i) * 35 / 5),
            )
        return bytes(data)

    def create_glow_circle(radius: int, r: int, g: int, b: int, glow_radius: int) -> bytes:
        if radius <= 0 or glow_radius < 0:
            return b""
        surf_size = int((radius + glow_radius) * 2 + 4)
        data = bytearray(surf_size * surf_size * 4)
        _fill_glow_circle(
            data,
            surf_size,
            surf_size,
            surf_size / 2.0,
            surf_size / 2.0,
            float(radius),
            (int(r), int(g), int(b)),
            float(glow_radius),
        )
        return bytes(data)

    def batch_update_bullets(
        bullets: list[tuple[int, float, float, float, float, int, bool, float]],
    ) -> list[tuple[int, float, float, bool]]:
        results = []
        for bullet_id, x, y, vx, vy, _bullet_type, is_laser, screen_height in bullets:
            new_x = x + vx
            new_y = y + vy
            active = True if is_laser else -10.0 <= new_y <= screen_height + 10.0
            results.append((bullet_id, new_x, new_y, active))
        return results

    def batch_update_bullets_buf(buf: bytes) -> list[tuple[int, float, float, bool]]:
        import struct

        if len(buf) % 32 != 0:
            raise ValueError("bullet buffer length must be multiple of 32")
        count = len(buf) // 32
        fmt = "<qffffBxxxf"
        results = []
        for i in range(count):
            bullet_id, x, y, vx, vy, is_laser, screen_height = struct.unpack_from(fmt, buf, i * 32)
            new_x = x + vx
            new_y = y + vy
            active = True if is_laser else -10.0 <= new_y <= screen_height + 10.0
            results.append((bullet_id, new_x, new_y, active))
        return results

    def find_nearest_target(
        candidates: list[tuple[int, float, float]],
        query_x: float,
        query_y: float,
    ) -> int | None:
        best_id = None
        best_dist_sq = float("inf")
        for cid, cx, cy in candidates:
            d = (cx - query_x) ** 2 + (cy - query_y) ** 2
            if d < best_dist_sq:
                best_dist_sq = d
                best_id = cid
        return best_id

    def find_target_in_direction(
        candidates: list[tuple[int, float, float]],
        origin_x: float,
        origin_y: float,
        move_x: float,
        move_y: float,
        direction_cone_dot: float,
        exclude_id: int | None,
    ) -> int | None:
        movement_len = math.hypot(move_x, move_y)
        if movement_len <= 0:
            return None
        mx = move_x / movement_len
        my = move_y / movement_len
        best_id = None
        best_score = 0.0
        for cid, cx, cy in candidates:
            if exclude_id == cid:
                continue
            tx = cx - origin_x
            ty = cy - origin_y
            dist = math.hypot(tx, ty)
            if dist <= 0:
                continue
            dot = (tx / dist) * mx + (ty / dist) * my
            if dot > best_score and dot >= direction_cone_dot:
                best_score = dot
                best_id = cid
        return best_id

    def batch_hallucinated_enemy_centers(
        enemies: list[tuple[float, float, int]],
        player_center: tuple[float, float] | None,
        frame: int,
        strength: float,
        lunge_scale: float,
    ) -> list[tuple[float, float]]:
        f = float(frame)
        results = []
        for cx, cy, entity_id in enemies:
            pulse = max(0.0, math.sin(f * 0.13 + (entity_id % 31)))
            jx = math.sin(f * 0.21 + (entity_id % 17)) * 8.0 * strength
            jy = math.cos(f * 0.18 + (entity_id % 23)) * 6.0 * strength
            lx = ly = 0.0
            if player_center is not None:
                px, py = player_center
                dx = px - cx
                dy = py - cy
                length = math.hypot(dx, dy)
                if length > 0.001:
                    lunge = pulse * (12.0 + 36.0 * strength) * lunge_scale
                    lx = dx / length * lunge
                    ly = dy / length * lunge
            results.append((cx + jx + lx, cy + jy + ly))
        return results


__all__ = [
    "RUST_AVAILABLE",
    # Collision functions
    "batch_collide_bullets_vs_entities",
    "batch_hallucinated_enemy_centers",
    # Bullet functions
    "batch_update_bullets",
    "batch_update_bullets_buf",
    "batch_update_movements",
    "batch_update_movements_buf",
    # Particle functions
    "batch_update_particles",
    "compute_starfield_positions",
    "create_explosive_missile_glow",
    "create_glow_circle",
    "create_laser_bullet_glow",
    # Sprite functions
    "create_single_bullet_glow",
    "create_spread_bullet_glow",
    "find_nearest_target",
    "find_target_in_direction",
    "generate_explosion_particles",
    # Movement functions
    "update_movement",
    "vec2_add",
    "vec2_angle",
    "vec2_clamp_length",
    "vec2_distance",
    "vec2_dot",
    "vec2_from_angle",
    # Vector2 functions
    "vec2_length",
    "vec2_lerp",
    "vec2_normalize",
    "vec2_scale",
    "vec2_sub",
]
