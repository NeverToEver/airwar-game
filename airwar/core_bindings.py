"""Python bindings for the optional Rust core module."""

from __future__ import annotations

import math
import random

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
        length_sq = x * x + y * y
        max_sq = max_length * max_length
        if length_sq > max_sq:
            length = math.sqrt(length_sq)
            return x / length * max_length, y / length * max_length
        return x, y

    class _AABB:
        __slots__ = ("min_x", "min_y", "max_x", "max_y")

        def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
            self.min_x = min_x
            self.min_y = min_y
            self.max_x = max_x
            self.max_y = max_y

        @classmethod
        def from_xy_size(cls, x: float, y: float, width: float, height: float) -> "_AABB":
            return cls(x, y, x + width, y + height)

        @classmethod
        def from_xy_half_size(cls, x: float, y: float, half_size: float) -> "_AABB":
            return cls(x - half_size, y - half_size, x + half_size, y + half_size)

        def intersects(self, other: "_AABB") -> bool:
            return (
                self.min_x < other.max_x
                and self.max_x > other.min_x
                and self.min_y < other.max_y
                and self.max_y > other.min_y
            )

    class PersistentSpatialHash:
        """Pure-Python fallback for the Rust persistent spatial hash."""

        def __init__(self, cell_size: int) -> None:
            self.cell_size = int(cell_size)
            self._entities: dict[int, _AABB] = {}

        def clear(self) -> None:
            self._entities.clear()

        def update_entity(self, entity_id: int, x: float, y: float, half_size: float) -> None:
            self._entities[int(entity_id)] = _AABB.from_xy_half_size(x, y, half_size)

        def update_entities(self, entities: list[tuple[int, float, float, float]]) -> None:
            for entity_id, x, y, half_size in entities:
                self.update_entity(entity_id, x, y, half_size)

        def remove_entity(self, entity_id: int) -> None:
            self._entities.pop(int(entity_id), None)

        def get_collisions(self) -> list[tuple[int, int]]:
            items = list(self._entities.items())
            pairs: list[tuple[int, int]] = []
            for i, (left_id, left_bounds) in enumerate(items):
                for right_id, right_bounds in items[i + 1:]:
                    if left_bounds.intersects(right_bounds):
                        pairs.append((min(left_id, right_id), max(left_id, right_id)))
            return pairs

        def query(self, x: float, y: float, half_size: float) -> list[int]:
            query_bounds = _AABB.from_xy_half_size(x, y, half_size)
            return [entity_id for entity_id, bounds in self._entities.items() if query_bounds.intersects(bounds)]

    def batch_collide_bullets_vs_entities(
        bullets: list[tuple[int, float, float, float, float]],
        enemies: list[tuple[int, float, float, float, float]],
        cell_size: int,
    ) -> list[tuple[int, int]]:
        del cell_size
        if not bullets or not enemies:
            return []

        enemy_bounds = [
            (enemy_id, _AABB.from_xy_size(x, y, width, height))
            for enemy_id, x, y, width, height in enemies
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

    def compute_boss_attack(
        pattern: int,
        phase: int,
        attack_dir: int,
        center_x: float,
        center_y: float,
        rect_bottom: float,
        rect_left: float,
        rect_right: float,
        rect_top: float,
    ) -> list[tuple[float, float, float, float, float, int, int]]:
        del center_y
        base_angle, y_base = {
            0: (-90.0, rect_bottom),
            1: (180.0, (rect_top + rect_bottom) / 2.0),
            2: (0.0, (rect_top + rect_bottom) / 2.0),
        }.get(attack_dir, (90.0, rect_top))

        if pattern == 0:
            count = 5 + int(phase)
            spread_angle = 45.0 if attack_dir in (1, 2) else 180.0
            offset = 22.5 if attack_dir in (1, 2) else 0.0
            speed = 5.0
            damage = 12 + int(phase) * 2
            return [
                (
                    center_x,
                    y_base,
                    math.cos(math.radians(base_angle + spread_angle * (i / max(1, count - 1)) - offset)) * speed,
                    math.sin(math.radians(base_angle + spread_angle * (i / max(1, count - 1)) - offset)) * speed,
                    speed,
                    0,
                    damage,
                )
                for i in range(count)
            ]

        source_x, source_y = {
            0: (center_x, rect_bottom),
            1: (rect_left, (rect_top + rect_bottom) / 2.0),
            2: (rect_right, (rect_top + rect_bottom) / 2.0),
        }.get(attack_dir, (center_x, rect_top))

        if pattern == 1:
            speed = 7.0
            damage = 18 + int(phase) * 3
            dx = -500.0 if attack_dir == 1 else 500.0 if attack_dir == 2 else 0.0
            dy = 500.0 if attack_dir == 0 else -500.0 if attack_dir == 3 else 0.0
            length = max(math.sqrt(dx * dx + dy * dy), 0.001)
            return [(source_x + offset, source_y, dx / length * speed, dy / length * speed, speed, 1, damage)
                    for offset in (-30.0, 0.0, 30.0)]

        speed = 4.0
        damage = 12
        return [
            (
                source_x,
                source_y,
                math.cos(math.radians(base_angle + 22.5 * i)) * speed,
                math.sin(math.radians(base_angle + 22.5 * i)) * speed,
                speed,
                2,
                damage,
            )
            for i in range(8)
        ]

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

    def _set_pixel(data: bytearray, width: int, x: int, y: int, color: tuple[int, int, int], alpha: int) -> None:
        idx = (y * width + x) * 4
        data[idx] = color[0]
        data[idx + 1] = color[1]
        data[idx + 2] = color[2]
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

__all__ = [
    'RUST_AVAILABLE',
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
]
