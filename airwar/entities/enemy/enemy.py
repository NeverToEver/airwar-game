"""Enemy and Boss entities with movement patterns and attack behaviors."""

import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import pygame

from airwar.config import (
    ENEMY_COLLISION_SCALE,
    ENEMY_HITBOX_PADDING,
    ENEMY_HITBOX_SIZE,
    ENEMY_VISUAL_SCALE,
    get_screen_height,
    get_screen_width,
)
from airwar.config.constants_access import get_game_constants
from airwar.core_bindings import update_movement as rust_update_movement

from ..base import EnemyData, Entity, Vector2
from ..bullet import Bullet, BulletData
from ..interfaces import IBulletSpawner
from ..movement_strategies import get_movement_strategy
from .boss import boss_attack, boss_movement, boss_render, boss_state


class EnemyState(Enum):
    """Enemy lifecycle states."""

    ENTERING = "entering"
    ACTIVE = "active"
    EXITING = "exiting"


# Movement type string to Rust enum mapping
MOVEMENT_TYPE_MAP = {
    "straight": 0,
    "sine": 1,
    "zigzag": 2,
    "dive": 3,
    "hover": 4,
    "spiral": 5,
    "noise": 6,
    "aggressive": 7,
}

if TYPE_CHECKING:
    pass


class Enemy(Entity):
    """Enemy entity with various movement patterns.

    Enemy class handles movement, firing, and lifecycle for regular enemies.
    Supports multiple movement patterns: straight, sine, zigzag, dive, hover, spiral.
    Enemies enter from above screen, stay active for ~15 seconds, then exit.

    Attributes:
        data: EnemyData configuration for health, speed, score, etc.
        health: Current health points.
        max_health: Maximum health points.
        fire_timer: Timer for tracking fire rate.
        move_type: Current movement pattern type.
        entity_id: Unique identifier for this entity.
    """

    # --- Entry/Exit constants ---
    ENTRY_START_Y = 150
    EXIT_X_OFFSETS = (-300, 300, 0, -150, 150)
    EXIT_END_Y = -150
    EXIT_ACTIVE_END_Y = -100
    TRANSITION_DURATION = 15
    ENTRY_SPEED = 0.04
    EXIT_SPEED = 0.03
    FIRE_RATE_MIN = 10
    ENEMY_BULLET_SPEED = 5.0

    # --- Movement pattern range constants ---
    SINE_AMP_RANGE = (1.5, 3.0)
    SINE_FREQ_RANGE = (0.03, 0.06)
    ZIGZAG_INTERVAL_RANGE = (30, 60)
    ZIGZAG_SPEED_RANGE = (1.5, 2.5)
    DIVE_DELAY_RANGE = (20, 50)
    HOVER_SPEED_RANGE = (1.0, 1.8)
    HOVER_AMP_RANGE = (20, 40)
    SPIRAL_SPEED_RANGE = (1.0, 2.0)
    SPIRAL_RADIUS_RANGE = (30, 50)
    SPIRAL_FREQ_RANGE = (0.05, 0.08)
    NOISE_SPEED_RANGE = (0.02, 0.04)
    NOISE_SCALE_X_RANGE = (0.5, 1.0)
    NOISE_SCALE_Y_RANGE = (0.3, 0.6)
    NOISE_AMP_X_RANGE = (0.6, 0.9)
    NOISE_AMP_Y_RANGE = (0.3, 0.6)
    AGGR_SPEED_RANGE = (0.025, 0.045)
    AGGR_SCALE_X_RANGE = (0.6, 1.0)
    AGGR_SCALE_Y_RANGE = (0.5, 0.8)
    AGGR_AMP_X_RANGE = (0.5, 0.8)
    AGGR_AMP_Y_RANGE = (0.4, 0.7)
    SPREAD_FIRE_OFFSETS = (-28, -14, 0, 14, 28)
    HOVER_TIMER_RUST_SCALE = 0.08
    DEFAULT_MOVE_AMPLITUDE = 2.0
    DEFAULT_MOVE_FREQUENCY = 0.05
    DEFAULT_MOVE_SPEED = 2.0
    DEFAULT_NOISE_SPEED = 0.03
    DEFAULT_AGGRESSIVE_SPEED = 0.035
    DEFAULT_ZIGZAG_INTERVAL = 45.0
    DEFAULT_SPIRAL_RADIUS = 40.0
    DEFAULT_NOISE_SCALE_X = 0.04
    DEFAULT_NOISE_SCALE_Y = 0.02
    DEFAULT_NOISE_AMPLITUDE_X = 0.7
    DEFAULT_NOISE_AMPLITUDE_Y = 0.4
    DEFAULT_AGGRESSIVE_AMPLITUDE_X = 0.6
    DEFAULT_AGGRESSIVE_AMPLITUDE_Y = 0.5

    # 1. Special methods

    def __init__(self, x: float, y: float, data: EnemyData):
        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2

        collision_size = int(base_size * ENEMY_COLLISION_SCALE)
        render_size = int(base_size * ENEMY_VISUAL_SCALE)

        self._collision_rect = pygame.Rect(
            x - (collision_size - render_size) // 2,
            y - (collision_size - render_size) // 2,
            collision_size,
            collision_size,
        )

        super().__init__(x, y, render_size, render_size)

        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self._bullet_spawner: IBulletSpawner | None = None
        self.entity_id = id(self)
        self._init_movement(data.enemy_type)
        self.sync_rects()
        self._difficulty_multiplier = 1.0
        self._fire_rate_modifier = 1.0
        self._movement_enhancements = {}

        # Wave system: entry/exit states
        self._state = EnemyState.ENTERING
        self._entry_progress = 0.0
        self._entry_start_x = x
        self._entry_start_y = y - self.ENTRY_START_Y  # Start above screen
        self._entry_target_x = x
        self._entry_target_y = y
        self._exit_progress = 0.0
        self._exit_start_x = x
        self._exit_start_y = y
        self._exit_end_x = x + random.choice(self.EXIT_X_OFFSETS)
        self._exit_end_y = self.EXIT_END_Y

        # Lifetime timer: 15 seconds = 900 frames at 60fps
        self.lifetime = 0
        consts = get_game_constants()
        self._max_lifetime = consts.ENEMY.LIFETIME
        self._move_range_x = consts.ENEMY.MOVE_RANGE_X
        self._move_range_y = consts.ENEMY.MOVE_RANGE_Y
        self.active_position_x = x
        self.active_position_y = y

        # Entry-to-active transition smoothing
        self._transition_timer = 0
        self._transition_duration = self.TRANSITION_DURATION

    # 2. Properties

    @property
    def collision_rect(self) -> pygame.Rect:
        return self._collision_rect

    @collision_rect.setter
    def collision_rect(self, value: pygame.Rect) -> None:
        self._collision_rect = value

    # 3. Public lifecycle methods

    def update(self, *args, **kwargs) -> None:
        """Update enemy state each frame.

        Handles entry/active/exit state machine, lifetime tracking,
        movement, and firing.
        """
        if not self.active:
            return

        if self._state == EnemyState.ENTERING:
            self._update_entry_state()
            return

        if self._state == EnemyState.EXITING:
            self._update_exit_state()
            return

        self._update_active_state()

    def _update_entry_state(self) -> None:
        if self.rect.y > get_screen_height():
            self.active = False
            return

        self._entry_progress += self.ENTRY_SPEED
        if self._entry_progress >= 1.0:
            self._finish_entry()
            return

        t = self._entry_progress
        t_eased = 1.0 - (1.0 - t) * (1.0 - t)
        self.rect.x = self._entry_start_x + (self._entry_target_x - self._entry_start_x) * t_eased
        self.rect.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * t_eased
        self.sync_rects()

    def _finish_entry(self) -> None:
        self._entry_progress = 1.0
        self._state = EnemyState.ACTIVE
        self.rect.x = self._entry_target_x
        self.rect.y = self._entry_target_y
        self.sync_rects()
        self.active_position_x = self.rect.x
        self.active_position_y = self.rect.y
        self.lifetime = 0

    def _update_exit_state(self) -> None:
        self._exit_progress += self.EXIT_SPEED
        if self._exit_progress >= 1.0:
            self.active = False
            return

        t = self._exit_progress
        self.rect.x = self._exit_start_x + (self._exit_end_x - self._exit_start_x) * t + math.sin(t * math.pi) * 30
        self.rect.y = self._exit_start_y + (self._exit_end_y - self._exit_start_y) * t
        self.sync_rects()

    def _update_active_state(self) -> None:
        self.lifetime += 1
        if self.lifetime >= self._max_lifetime:
            self._begin_lifetime_exit()
            return

        self._update_movement()
        self._apply_entry_transition_blend()

        if self.rect.y > get_screen_height():
            self.active = False

        self._update_fire_timer()

    def _begin_lifetime_exit(self) -> None:
        self._state = EnemyState.EXITING
        self._exit_start_x = self.rect.x
        self._exit_start_y = self.rect.y
        self._exit_end_x = self.rect.x + random.choice(self.EXIT_X_OFFSETS)
        self._exit_end_y = self.EXIT_ACTIVE_END_Y

    def _update_movement(self) -> None:
        if self._can_use_rust_movement():
            self._update_rust_movement()
        else:
            self._movement_strategy.update(self)

    def _can_use_rust_movement(self) -> bool:
        return self.move_type in MOVEMENT_TYPE_MAP

    def _update_rust_movement(self) -> None:
        batch_result = getattr(self, "_batch_result", None)
        if batch_result is not None:
            self._apply_rust_movement_result(batch_result)
            del self._batch_result
            return

        timer = getattr(self, self._timer_attr, 0.0)
        if self.move_type == "hover":
            timer /= self.HOVER_TIMER_RUST_SCALE

        params = self._rust_params
        new_x, new_y, new_timer = rust_update_movement(
            self._rust_move_type_code,
            timer,
            self.active_position_x,
            self.active_position_y,
            self._move_range_x,
            self._move_range_y,
            params["offset"],
            params["amplitude"],
            params["frequency"],
            params["speed"],
            params["direction"],
            params["zigzag_interval"],
            params["spiral_radius"],
            self.rect.x,
            self.rect.y,
            params["noise_scale_x"],
            params["noise_scale_y"],
            params["noise_amplitude_x"],
            params["noise_amplitude_y"],
            params["noise_seed"],
        )
        self._apply_rust_movement_result((new_x, new_y, new_timer))

    def _apply_rust_movement_result(self, result: tuple[float, float, float]) -> None:
        self.rect.x, self.rect.y, new_timer = result
        if self.move_type == "hover":
            new_timer *= self.HOVER_TIMER_RUST_SCALE
        setattr(self, self._timer_attr, new_timer)
        self.sync_rects()

    def _apply_entry_transition_blend(self) -> None:
        if self._transition_timer < self._transition_duration:
            self._transition_timer += 1
            t = self._transition_timer / self._transition_duration
            blend = t * t
            self.rect.x = self.active_position_x + (self.rect.x - self.active_position_x) * blend
            self.rect.y = self.active_position_y + (self.rect.y - self.active_position_y) * blend
            self.sync_rects()

    def _update_fire_timer(self) -> None:
        self.fire_timer += 1
        modifier = max(0.01, self._fire_rate_modifier)
        fire_threshold = max(self.FIRE_RATE_MIN, int(self.data.fire_rate / modifier))
        if self.fire_timer >= fire_threshold:
            self.fire_timer = 0
            self._fire()

    def render(self, surface: pygame.Surface) -> None:
        """Render the enemy sprite with health-based coloring.

        Args:
        surface: Pygame surface to render onto.
        """
        if self._sprite:
            surface.blit(self._sprite, self.get_rect())

    # 4. Public behavior methods

    def take_damage(self, damage: int) -> None:
        """Apply damage to the enemy.

        Reduces health by the damage amount. If health reaches 0,
        the enemy is deactivated.

        Args:
        damage: Amount of damage to apply (ignored if None or negative).
        """
        if damage is None or damage < 0:
            return
        self.health -= damage
        if self.health <= 0:
            self.active = False

    def get_hitbox(self) -> pygame.Rect:
        return self._collision_rect

    def check_point_collision(self, x: float, y: float) -> bool:
        return self._collision_rect.collidepoint(x, y)

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def set_difficulty(
        self, speed_mult: float, fire_rate_modifier: float, movement_enhancements: dict | None = None
    ) -> None:
        self._difficulty_multiplier = max(0.01, speed_mult)
        self._fire_rate_modifier = max(0.01, fire_rate_modifier)
        self._movement_enhancements = movement_enhancements or {}

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite

    def begin_exit(self, x_offset: float, end_y: float) -> None:
        """Begin the exit animation sequence.

        Forces the enemy into EnemyState.EXITING state and sets the target
        position for the exit animation curve.

        Args:
            x_offset: Target x-coordinate for exit end position.
            end_y: Target y-coordinate for exit end position.
        """
        self._state = EnemyState.EXITING
        self._exit_start_x = self.rect.x
        self._exit_start_y = self.rect.y
        self._exit_end_x = x_offset
        self._exit_end_y = end_y
        self._exit_progress = 0.0

    def is_active_in_wave(self) -> bool:
        return self.active and self._state != EnemyState.EXITING

    def is_ready_for_batch_movement(self) -> bool:
        return self.active and self._state == EnemyState.ACTIVE

    def apply_batch_movement_result(self, result: tuple[float, float, float]) -> None:
        self._batch_result = result

    def get_rust_batch_params(self):
        """Return (base_tuple, extra_tuple) for batch Rust movement, or (None, None)."""
        if not hasattr(self, "_rust_move_type_code"):
            return None, None
        p = self._rust_params
        timer = getattr(self, self._timer_attr, 0.0)
        if self.move_type == "hover":
            timer /= self.HOVER_TIMER_RUST_SCALE
        c = get_game_constants()
        base = (
            self._rust_move_type_code,
            timer,
            self.active_position_x,
            self.active_position_y,
            float(c.ENEMY.MOVE_RANGE_X),
            float(c.ENEMY.MOVE_RANGE_Y),
            p["offset"],
            p["amplitude"],
            p["frequency"],
            p["speed"],
            p["direction"],
            p["zigzag_interval"],
        )
        extra = (
            p["spiral_radius"],
            self.rect.x,
            self.rect.y,
            p["noise_scale_x"],
            p["noise_scale_y"],
            p["noise_amplitude_x"],
            p["noise_amplitude_y"],
            p["noise_seed"],
        )
        return base, extra

    # 5. Private lifecycle methods

    def _init_movement(self, enemy_type: str) -> None:
        init_method = self._movement_initializers().get(enemy_type, self._init_straight_movement)
        init_method()
        self._movement_strategy = get_movement_strategy(self.move_type)
        self._configure_rust_movement()

    def _movement_initializers(self) -> dict[str, Callable[[], None]]:
        return {
            "sine": self._init_sine_movement,
            "zigzag": self._init_zigzag_movement,
            "dive": self._init_dive_movement,
            "hover": self._init_hover_movement,
            "spiral": self._init_spiral_movement,
            "noise": self._init_noise_movement,
            "aggressive": self._init_aggressive_movement,
        }

    def _init_straight_movement(self) -> None:
        self.move_type = "straight"

    def _init_sine_movement(self) -> None:
        self.move_type = "sine"
        self.move_offset = random.uniform(0, math.pi * 2)
        self.move_amplitude = random.uniform(*self.SINE_AMP_RANGE)
        self.move_frequency = random.uniform(*self.SINE_FREQ_RANGE)
        self.start_x = self.rect.x
        self.move_timer = 0

    def _init_zigzag_movement(self) -> None:
        self.move_type = "zigzag"
        self.direction = random.choice([-1, 1])
        self.zigzag_timer = 0
        self.zigzag_interval = random.randint(*self.ZIGZAG_INTERVAL_RANGE)
        self.zigzag_speed = random.uniform(*self.ZIGZAG_SPEED_RANGE)

    def _init_dive_movement(self) -> None:
        self.move_type = "dive"
        self.target_x = self.start_x = self.rect.x
        self.dive_timer = 0
        self.dive_delay = random.randint(*self.DIVE_DELAY_RANGE)
        self.diving = False

    def _init_hover_movement(self) -> None:
        self.move_type = "hover"
        self.hover_timer = 0
        self.hover_speed = random.uniform(*self.HOVER_SPEED_RANGE)
        self.hover_amplitude = random.uniform(*self.HOVER_AMP_RANGE)
        self.start_x = self.rect.x

    def _init_spiral_movement(self) -> None:
        self.move_type = "spiral"
        self.spiral_timer = 0
        self.spiral_speed = random.uniform(*self.SPIRAL_SPEED_RANGE)
        self.spiral_radius = random.uniform(*self.SPIRAL_RADIUS_RANGE)
        self.spiral_frequency = random.uniform(*self.SPIRAL_FREQ_RANGE)
        self.start_x = self.rect.x

    def _init_noise_movement(self) -> None:
        self.move_type = "noise"
        self.noise_timer = 0.0
        self.noise_speed = random.uniform(*self.NOISE_SPEED_RANGE)
        self.noise_scale_x = random.uniform(*self.NOISE_SCALE_X_RANGE)
        self.noise_scale_y = random.uniform(*self.NOISE_SCALE_Y_RANGE)
        self.noise_amplitude_x = random.uniform(*self.NOISE_AMP_X_RANGE)
        self.noise_amplitude_y = random.uniform(*self.NOISE_AMP_Y_RANGE)
        self.noise_seed = random.randint(0, 9999)

    def _init_aggressive_movement(self) -> None:
        self.move_type = "aggressive"
        self.agg_timer = 0.0
        self.agg_speed = random.uniform(*self.AGGR_SPEED_RANGE)
        self.agg_scale_x = random.uniform(*self.AGGR_SCALE_X_RANGE)
        self.agg_scale_y = random.uniform(*self.AGGR_SCALE_Y_RANGE)
        self.agg_amplitude_x = random.uniform(*self.AGGR_AMP_X_RANGE)
        self.agg_amplitude_y = random.uniform(*self.AGGR_AMP_Y_RANGE)
        self.agg_seed = random.randint(0, 9999)

    def _configure_rust_movement(self) -> None:
        self._rust_move_type_code = MOVEMENT_TYPE_MAP.get(self.move_type, 0)
        self._rust_params = {
            "offset": getattr(self, "move_offset", 0.0),
            "amplitude": getattr(self, "move_amplitude", self.DEFAULT_MOVE_AMPLITUDE),
            "frequency": self._rust_frequency_param(),
            "speed": self._rust_speed_param(),
            "direction": getattr(self, "direction", 1.0),
            "zigzag_interval": getattr(self, "zigzag_interval", self.DEFAULT_ZIGZAG_INTERVAL),
            "spiral_radius": getattr(self, "spiral_radius", self.DEFAULT_SPIRAL_RADIUS),
            "noise_scale_x": self._rust_noise_param("scale_x"),
            "noise_scale_y": self._rust_noise_param("scale_y"),
            "noise_amplitude_x": self._rust_noise_param("amplitude_x"),
            "noise_amplitude_y": self._rust_noise_param("amplitude_y"),
            "noise_seed": (
                getattr(self, "agg_seed", 0) if self.move_type == "aggressive" else getattr(self, "noise_seed", 0)
            ),
        }
        if self.move_type == "hover":
            self._timer_attr = "hover_timer"
        elif self.move_type in ("zigzag", "dive", "spiral", "noise", "aggressive"):
            self._timer_attr = f"{self.move_type}_timer"
        else:
            self._timer_attr = "move_timer"

    def _rust_frequency_param(self) -> float:
        if self.move_type == "spiral":
            return getattr(self, "spiral_frequency", self.DEFAULT_MOVE_FREQUENCY)
        return getattr(self, "move_frequency", self.DEFAULT_MOVE_FREQUENCY)

    def _rust_speed_param(self) -> float:
        if self.move_type == "zigzag":
            return getattr(self, "zigzag_speed", self.DEFAULT_MOVE_SPEED)
        if self.move_type == "noise":
            return getattr(self, "noise_speed", self.DEFAULT_NOISE_SPEED)
        if self.move_type == "aggressive":
            return getattr(self, "agg_speed", self.DEFAULT_AGGRESSIVE_SPEED)
        return getattr(self, "spiral_speed", self.DEFAULT_MOVE_SPEED)

    def _rust_noise_param(self, name: str) -> float:
        if self.move_type == "aggressive":
            defaults = {
                "scale_x": self.DEFAULT_NOISE_SCALE_X,
                "scale_y": self.DEFAULT_NOISE_SCALE_Y,
                "amplitude_x": self.DEFAULT_AGGRESSIVE_AMPLITUDE_X,
                "amplitude_y": self.DEFAULT_AGGRESSIVE_AMPLITUDE_Y,
            }
            return getattr(self, f"agg_{name}", defaults[name])

        defaults = {
            "scale_x": self.DEFAULT_NOISE_SCALE_X,
            "scale_y": self.DEFAULT_NOISE_SCALE_Y,
            "amplitude_x": self.DEFAULT_NOISE_AMPLITUDE_X,
            "amplitude_y": self.DEFAULT_NOISE_AMPLITUDE_Y,
        }
        return getattr(self, f"noise_{name}", defaults[name])

    # 6. Private behavior methods

    def sync_rects(self) -> None:
        self._collision_rect.x = self.rect.x - (self._collision_rect.width - self.rect.width) // 2
        self._collision_rect.y = self.rect.y - (self._collision_rect.height - self.rect.height) // 2

    def _resize_collision_rect(self, scale: float) -> None:
        size = int(max(self.rect.width, self.rect.height) * scale)
        self._collision_rect.size = (size, size)
        self.sync_rects()

    def _fire(self) -> None:
        bullets = self._create_bullets()

        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _create_bullets(self) -> list[Bullet]:
        bullets = []
        center_x = self.rect.centerx

        if self.data.bullet_type == "spread":
            for angle in self.SPREAD_FIRE_OFFSETS:
                bullet_data = BulletData(
                    damage=self._get_damage(), speed=self.ENEMY_BULLET_SPEED, owner="enemy", bullet_type="spread"
                )
                bullet = Bullet(center_x + angle, self.rect.bottom, bullet_data)
                bullet.velocity = Vector2(angle * 0.15, 5)
                bullets.append(bullet)
        elif self.data.bullet_type == "laser":
            bullet_data = BulletData(
                damage=self._get_damage(), speed=self.ENEMY_BULLET_SPEED, owner="enemy", bullet_type="laser"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(0, 8)
            bullets.append(bullet)
        else:
            bullet_data = BulletData(
                damage=self._get_damage(), speed=self.ENEMY_BULLET_SPEED, owner="enemy", bullet_type="single"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(0, 5)
            bullets.append(bullet)

        return bullets

    def _get_damage(self) -> int:
        return get_game_constants().BOSS.BULLET_DAMAGE_MAP.get(self.data.bullet_type, 15)


class EnemySpawner:
    """Spawns enemies in V-formation waves.

    Manages enemy wave spawning with V-formation patterns. Handles wave
    lifecycle tracking and enemy type selection based on probability
    distribution.

    Attributes:
        health: Health value for spawned enemies.
        speed: Speed value for spawned enemies.
        spawn_rate: Frames between potential spawns.
        bullet_type: Type of bullet spawned enemies fire.
        _wave_active: Whether a spawn wave is currently active.
        _wave_enemies_spawned: Count of enemies spawned in current wave.
    """

    ENEMIES_PER_FRAME = 2
    DEFAULT_SPEED = 3.0
    DEFAULT_SPAWN_RATE = 30
    MAX_CONCURRENT_ENEMIES = 5
    ELITES_PER_WAVE = 2
    MIN_SPAWN_Y = -30
    MAX_SPAWN_Y_FRACTION = 0.70
    LASER_FIRE_RATE = 60
    NORMAL_FIRE_RATE = 80
    ENTRY_SPAWN_Y = -50
    DEFAULT_SPREAD_ENEMY_CAP = 2

    def __init__(self):
        self.spawn_timer = 0
        self.health = 100
        self.speed = self.DEFAULT_SPEED
        self.spawn_rate = self.DEFAULT_SPAWN_RATE
        self.bullet_type = "single"
        self._bullet_spawner: IBulletSpawner | None = None
        self._enemy_type_distribution = {
            "straight": 0.10,
            "sine": 0.10,
            "zigzag": 0.10,
            "dive": 0.10,
            "hover": 0.10,
            "spiral": 0.10,
            "noise": 0.20,
            "aggressive": 0.20,
        }
        self._elite_type_distribution = {
            "aggressive": 0.50,
            "noise": 0.50,
        }
        self._max_enemies = self.MAX_CONCURRENT_ENEMIES
        self._wave_active = False
        self._wave_enemies_spawned = 0
        self._wave_size = self._get_wave_size()
        self._pending_spawns: deque = deque()
        self._spread_enemy_cap = self.DEFAULT_SPREAD_ENEMY_CAP

    def _get_wave_size(self) -> int:
        return get_game_constants().BALANCE.WAVE_SIZE

    def _select_enemy_type(self) -> str:
        rand = random.random()
        cumulative = 0.0
        for enemy_type, prob in self._enemy_type_distribution.items():
            cumulative += prob
            if rand < cumulative:
                return enemy_type
        return "straight"

    def _select_elite_type(self) -> str:
        rand = random.random()
        cumulative = 0.0
        for enemy_type, prob in self._elite_type_distribution.items():
            cumulative += prob
            if rand < cumulative:
                return enemy_type
        return "aggressive"

    def set_params(self, health: int, speed: float, spawn_rate: int, bullet_type: str = "single") -> None:
        self.health = health
        self.speed = speed
        self.spawn_rate = spawn_rate
        self.bullet_type = bullet_type

    def set_spread_enemy_cap(self, cap: int) -> None:
        self._spread_enemy_cap = max(0, int(cap))

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def update(self, enemies: list[Enemy], slow_factor: float = 1.0, player_pos: tuple | None = None) -> None:
        # Count active enemies (not exiting or dead)
        active_enemies = 0
        for e in enemies:
            if e.is_active_in_wave():
                active_enemies += 1

        # Check if wave is complete (all enemies exited or died)
        if self._wave_active and active_enemies == 0 and self._wave_enemies_spawned >= self._wave_size:
            self._wave_active = False
            self._wave_enemies_spawned = 0
            self._pending_spawns = deque()

        # Start new wave if no wave active — prepare spawn data
        if not self._wave_active:
            self._wave_active = True
            self._wave_enemies_spawned = 0
            self._pending_spawns = self._prepare_wave_data(player_pos)

        # Gradual spawn: pop up to ENEMIES_PER_FRAME per frame
        for _ in range(self.ENEMIES_PER_FRAME):
            if not self._pending_spawns:
                break
            spawn_data = self._pending_spawns.popleft()
            self._spawn_one(enemies, spawn_data)
            self._wave_enemies_spawned += 1

    def _prepare_wave_data(self, player_pos: tuple | None = None) -> deque:
        """Precompute spawn descriptors for a V-formation wave.

        Returns a list of (x, y, bullet_type, enemy_type) tuples.
        """
        screen_width = get_screen_width()
        screen_height = get_screen_height()
        center_x = player_pos[0] if player_pos else screen_width // 2

        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2
        collision_size = int(base_size * ENEMY_COLLISION_SCALE)

        enemies_back = self._wave_size // 2
        enemies_front = self._wave_size - enemies_back

        back_y = int(screen_height * 0.25) + random.randint(-10, 10)
        front_y = int(screen_height * 0.40) + random.randint(-10, 10)
        back_width = int(screen_width * 0.80)
        front_width = int(screen_width * 0.35)

        positions = []
        for i in range(enemies_back):
            t = i / max(1, enemies_back - 1)
            positions.append((center_x - back_width // 2 + int(t * back_width), back_y))
        for i in range(enemies_front):
            t = i / max(1, enemies_front - 1)
            positions.append((center_x - front_width // 2 + int(t * front_width), front_y))

        bullet_types = ("single", "spread", "laser")
        elite_bullet_types = ("spread", "laser")
        spawn_data = []

        # Pick which positions get elite enemies
        elite_count = min(self.ELITES_PER_WAVE, len(positions))
        elite_indices = set(random.sample(range(len(positions)), elite_count))

        for i, (raw_px, raw_py) in enumerate(positions):
            px = max(collision_size // 2, min(raw_px, screen_width - collision_size // 2))
            py = max(self.MIN_SPAWN_Y, min(raw_py, int(screen_height * self.MAX_SPAWN_Y_FRACTION)))
            if i in elite_indices:
                spawn_data.append(
                    (
                        px,
                        py,
                        random.choice(elite_bullet_types),
                        self._select_elite_type(),
                        True,  # is_elite flag
                    )
                )
            else:
                spawn_data.append(
                    (
                        px,
                        py,
                        random.choice(bullet_types),
                        self._select_enemy_type(),
                        False,
                    )
                )
        return deque(self._limit_spread_bullet_types(spawn_data))

    def _limit_spread_bullet_types(self, spawn_data: list) -> list:
        spread_count = 0
        limited = []
        for px, py, bullet_type, enemy_type, is_elite in spawn_data:
            next_type = bullet_type
            if bullet_type == "spread":
                if spread_count >= self._spread_enemy_cap:
                    next_type = "laser" if is_elite else "single"
                else:
                    spread_count += 1
            limited.append((px, py, next_type, enemy_type, is_elite))
        return limited

    def _spawn_one(self, enemies: list[Enemy], data: tuple) -> None:
        """Create a single enemy from precomputed spawn tuple and add to list."""
        px, py, bullet_type, enemy_type, is_elite = data
        if is_elite:
            elite_data = EliteEnemyData(
                health=int(self.health * 2.5),
                speed=self.speed * 1.3,
                enemy_type=enemy_type,
                fire_rate=int(self.LASER_FIRE_RATE if bullet_type == "laser" else self.NORMAL_FIRE_RATE * 0.6),
                bullet_type=bullet_type,
            )
            enemy = EliteEnemy(px, py, elite_data)
        else:
            enemy_data = EnemyData(
                health=self.health,
                speed=self.speed,
                bullet_type=bullet_type,
                fire_rate=self.LASER_FIRE_RATE if bullet_type == "laser" else self.NORMAL_FIRE_RATE,
                enemy_type=enemy_type,
            )
            enemy = Enemy(px, py, enemy_data)
        enemy._entry_start_y = self.ENTRY_SPAWN_Y
        enemy._entry_start_x = px
        if self._bullet_spawner:
            enemy.set_bullet_spawner(self._bullet_spawner)
        enemies.append(enemy)


@dataclass
class EliteEnemyData:
    """Data class for Elite enemy configuration.

    Elite enemies are tougher variants that replace regular enemies in waves.
    They have 2.5x health, faster fire rate, more aggressive movement patterns,
    and a distinctive golden/amber visual style.

    Attributes:
        health: Maximum health points (2.5x base).
        speed: Movement speed (1.3x base).
        score: Score awarded when destroyed (3x base).
        enemy_type: Movement pattern type (always aggressive/noise).
        fire_rate: Frames between shots (40% faster than base).
        bullet_type: Type of bullet fired ("spread" or "laser").
    """

    health: int = 250
    speed: float = 3.9
    score: int = 300
    enemy_type: str = "aggressive"
    fire_rate: int = 40
    bullet_type: str = "spread"


class EliteEnemy(Enemy):
    """Elite enemy — tougher, more aggressive variant of regular enemies.

    Elite enemies replace 2 enemies per wave. They feature reinforced armor
    (2.5x HP), faster movement (1.3x), aggressive attack patterns, and a
    distinctive golden/amber visual style with energy shield glow.

    Attributes:
        data: EliteEnemyData configuration.
        _shield_pulse: Timer for energy shield visual effect.
    """

    VISUAL_SCALE = 1.3
    COLLISION_SCALE = 1.18
    ENTRY_SPEED = 0.03
    ELITE_FIRE_RATE = 30
    MIN_SPAWN_Y = -30
    SPAWN_START_Y = -80

    def __init__(self, x: float, y: float, data: EliteEnemyData):
        self.elite_data = data
        enemy_data = EnemyData(
            health=data.health,
            speed=data.speed,
            score=data.score,
            enemy_type=data.enemy_type,
            fire_rate=data.fire_rate,
            bullet_type=data.bullet_type,
        )
        super().__init__(x, y, enemy_data)
        self._resize_collision_rect(self.COLLISION_SCALE)
        self._shield_pulse: float = 0.0
        self._is_elite = True

    def update(
        self,
        enemies: list["Enemy"] | None = None,
        slow_factor: float = 1.0,
        player_pos: tuple[int, int] | None = None,
        *args,
        **kwargs,
    ) -> None:
        self._shield_pulse += 0.08
        super().update(enemies, slow_factor, player_pos, *args, **kwargs)


@dataclass
class BossData:
    """Data class for Boss entity configuration.

    Attributes:
        health: Maximum health points.
        speed: Movement speed in pixels per frame.
        score: Score awarded when points are defeated.
        width: Width of the boss sprite.
        height: Height of the boss sprite.
        fire_rate: Frames between attacks.
        phase: Current attack phase (1-3).
        escape_time: Frames before boss escapes.
    """

    health: int = 2000
    speed: float = 1.5
    score: int = 5000
    width: float = 120
    height: float = 100
    fire_rate: int = 45
    phase: int = 1
    escape_time: int = 3000


class Boss(Entity):
    """Boss entity with phase-based attacks and enrage sub-machine.

    After the Phase 1 refactor (boss class split), this class is a thin
    coordinator over four components:

    * :class:`BossStateMachine` -- lifecycle, enrage timers, damage-lock
    * :class:`BossMovement`     -- 4-phase patrol, aim-dash, enrage path
    * :class:`BossAttackPatterns` -- spread/aim/wave/snapshot attacks
    * :class:`BossRenderer`     -- sprite blit, facing angle, trail

    All public attributes and the most-used private methods are
    preserved so callers (and the 79+ Boss tests) keep working without
    any change.
    """

    # Re-exported tuning constants so legacy ``Boss.ENRAGE_DURATION``
    # style imports continue to work after the split.
    ATTACK_DIRECTIONS = boss_attack.ATTACK_DIRECTIONS
    DEFAULT_PHASE_DURATION = boss_movement.DEFAULT_PHASE_DURATION
    ENTRY_SPEED = boss_movement.ENTRY_SPEED
    ESCAPE_DRIFT = boss_movement.ESCAPE_DRIFT
    LERP_FACTOR = boss_movement.LERP_FACTOR
    MIN_Y = boss_movement.MIN_Y
    CENTER_OFFSET = boss_movement.CENTER_OFFSET
    SPREAD_DAMAGE_INCREMENT = boss_attack.SPREAD_DAMAGE_INCREMENT
    AIM_DAMAGE_INCREMENT = boss_attack.AIM_DAMAGE_INCREMENT
    AIM_BULLET_COUNT = boss_attack.AIM_BULLET_COUNT
    WAVE_BULLET_COUNT = boss_attack.WAVE_BULLET_COUNT
    HITBOX_WIDTH_SCALE = 1.78
    HITBOX_HEIGHT_SCALE = 1.22
    AIM_DASH_DISTANCE = boss_movement.AIM_DASH_DISTANCE
    AIM_DASH_PHASE_BONUS = boss_movement.AIM_DASH_PHASE_BONUS
    AIM_DASH_MAX_DISTANCE_RATIO = boss_movement.AIM_DASH_MAX_DISTANCE_RATIO
    AIM_DASH_DURATION = boss_movement.AIM_DASH_DURATION
    ENRAGE_TRIGGER_RATIO = boss_state.ENRAGE_TRIGGER_RATIO
    ENRAGE_DURATION = boss_state.ENRAGE_DURATION
    ENRAGE_TRANSITION_DURATION = boss_state.ENRAGE_TRANSITION_DURATION
    ENRAGE_SLOW_FACTOR = boss_state.ENRAGE_SLOW_FACTOR
    ENRAGE_BULLET_SPEED = boss_state.ENRAGE_BULLET_SPEED
    ENRAGE_LASER_SPEED = boss_state.ENRAGE_LASER_SPEED
    ENRAGE_RELEASE_BULLET_SPEED = boss_state.ENRAGE_RELEASE_BULLET_SPEED
    ENRAGE_RELEASE_LASER_SPEED = boss_state.ENRAGE_RELEASE_LASER_SPEED
    ENRAGE_ATTACK_INTERVAL = boss_state.ENRAGE_ATTACK_INTERVAL
    ENRAGE_ATTACK_WINDUP = boss_state.ENRAGE_ATTACK_WINDUP
    ENRAGE_RELEASE_INTERVAL = boss_state.ENRAGE_RELEASE_INTERVAL
    ENRAGE_SNAPSHOT_LASER_COUNT = boss_state.ENRAGE_SNAPSHOT_LASER_COUNT
    ENRAGE_SNAPSHOT_RING_COUNT = boss_state.ENRAGE_SNAPSHOT_RING_COUNT
    ENRAGE_PATH_RADIUS_SCALE = boss_state.ENRAGE_PATH_RADIUS_SCALE
    ENRAGE_SQUARE_PATH_RATIO = boss_state.ENRAGE_SQUARE_PATH_RATIO
    ENRAGE_TRAIL_LENGTH = boss_state.ENRAGE_TRAIL_LENGTH
    ENRAGE_TRAIL_RENDER_MAX = boss_state.ENRAGE_TRAIL_RENDER_MAX
    ENRAGE_TRAIL_FINAL_SCALE = boss_state.ENRAGE_TRAIL_FINAL_SCALE
    ENRAGE_TRAIL_SCALE = boss_state.ENRAGE_TRAIL_SCALE
    ENRAGE_TRAIL_BLUR_PASSES = boss_state.ENRAGE_TRAIL_BLUR_PASSES
    ENRAGE_EXIT_BACK_OFFSET = boss_state.ENRAGE_EXIT_BACK_OFFSET
    ENRAGE_MUZZLE_FLASH_DURATION = boss_state.ENRAGE_MUZZLE_FLASH_DURATION
    ENRAGE_MUZZLE_FLASH_PULSES = boss_state.ENRAGE_MUZZLE_FLASH_PULSES
    ENRAGE_MUZZLE_FORWARD_SCALE = boss_state.ENRAGE_MUZZLE_FORWARD_SCALE
    ENRAGE_MUZZLE_SIDE_SCALE = boss_state.ENRAGE_MUZZLE_SIDE_SCALE
    ENRAGE_RELEASE_HOLD_DURATION = boss_state.ENRAGE_RELEASE_HOLD_DURATION
    ENRAGE_RETURN_DURATION = boss_state.ENRAGE_RETURN_DURATION
    ENRAGE_CORE_COLOR = boss_state.ENRAGE_CORE_COLOR
    ENRAGE_DANGER_COLOR = boss_state.ENRAGE_DANGER_COLOR
    ENRAGE_TRAIL_TINT = boss_state.ENRAGE_TRAIL_TINT

    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.attack_pattern = 0
        self.attack_direction = "down"
        self.is_entering = True
        self.entry_y = y
        self.target_y = 180
        # Movement phase system
        self._move_phase = 0
        self._move_phase_timer = 0
        self._move_phase_duration = self.DEFAULT_PHASE_DURATION
        self._target_x: float = float(x)
        self._target_y: float = 180.0
        self.survival_timer = 0
        self.is_escaped = False
        self._show_escape_warning = False
        self.phase = data.phase
        self._bullet_spawner: IBulletSpawner | None = None
        self.entity_id = id(self)
        self._hitbox = pygame.Rect(0, 0, 0, 0)
        # Aim-dash state (mirrored on Boss for backward compat with tests)
        self._aim_dash_elapsed = 0
        self._aim_dash_duration = 0
        self._aim_dash_start_x = 0.0
        self._aim_dash_start_y = 0.0
        self._aim_dash_target_x = 0.0
        self._aim_dash_target_y = 0.0
        self._aim_fire_target: tuple[float, float] | None = None
        # Enrage render-only state
        self._facing_angle = 90.0
        self._muzzle_flash_timer = 0
        self._muzzle_flash_positions: list[tuple[float, float]] = []
        self._enrage_trail: list[tuple[float, float]] = []
        self._enrage_trail_ghost = None
        self._enrage_trail_ghost_key = None
        # ---- Components (Phase 1 split) ----
        self._state = boss_state.BossStateMachine(self)
        self._movement = boss_movement.BossMovement(self)
        self._attack = boss_attack.BossAttackPatterns(self)
        self._renderer = boss_render.BossRenderer(self)
        self.sync_hitbox()

    # ------------------------------------------------------------------
    # Hitbox
    # ------------------------------------------------------------------

    def sync_hitbox(self) -> None:
        self._hitbox.width = int(self.rect.width * self.HITBOX_WIDTH_SCALE)
        self._hitbox.height = int(self.rect.height * self.HITBOX_HEIGHT_SCALE)
        self._hitbox.center = (int(self.rect.centerx), int(self.rect.centery))

    def get_hitbox(self) -> pygame.Rect:
        self.sync_hitbox()
        return self._hitbox

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def update(
        self,
        enemies: list["Enemy"] | None = None,
        slow_factor: float = 1.0,
        player_pos: tuple[int, int] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Update boss state each frame.

        After the Phase 1 split, this method is the single per-frame
        entry point. The explicit state→movement→attack ordering is
        preserved by consulting :class:`BossStateMachine` first and only
        running movement/attack when appropriate.
        """
        # 1. Entrance animation
        if self.is_entering:
            if self._movement.tick_entry(slow_factor):
                self.is_entering = False
                self._state.finish_entry()
            return

        player = kwargs.get("player")

        # 2. Enrage trigger (idempotent, may transition the state machine)
        self._trigger_enrage_if_needed(player_pos, player)

        # 3. Enrage sub-state dispatch
        if self._state.is_enrage_transitioning():
            self._movement.tick_enrage_transition()
            target = self._state.enrage_snapshot_target
            if target is not None:
                self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_transition_timer()
            if self._state.enrage_transition_timer <= 0:
                self._state.finish_enrage_transition()
            return

        if self._state.is_enrage_active():
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_timer()
            target = self._state.enrage_snapshot_target
            if target is not None:
                self._renderer.record_enrage_trail()
                progress = self._state.enrage_progress()
                self._movement.tick_enrage_active()
                self._renderer.face_target(target)
                self._update_enrage_snapshot_attacks(target, progress)
            if self._state.enrage_timer <= 0:
                self._move_behind_player_after_enrage(target)
                self._release_enrage_bullets(target)
            return

        if self._state.is_enrage_release_holding():
            target = (
                self._current_player_target(player, player_pos)
                or self._state.enrage_snapshot_target
                or (get_screen_width() / 2, get_screen_height() / 2)
            )
            self._movement.tick_enrage_release_hold()
            self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_release_hold_timer()
            if self._state.enrage_release_hold_timer <= 0:
                self._movement.start_enrage_return()
            return

        if self._state.is_enrage_returning():
            target = self._current_player_target(player, player_pos) or self._state.enrage_snapshot_target
            self._movement.tick_enrage_return()
            if target is not None:
                self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_return_timer()
            if self._state.enrage_return_timer <= 0:
                self._state.finish_enrage_return()
            return

        # 4. Active (non-enrage) frame
        self.survival_timer += 1
        if self.survival_timer >= self.data.escape_time:
            self.is_escaped = True
            self.active = False
            self._state.mark_escaped()
            return

        if self._movement.is_aim_dashing():
            if self._movement.tick_aim_dash():
                self._finish_aim_dash()
            return

        self._movement.tick_active(player_pos, slow_factor)

        self.phase_timer += 1
        if self.phase_timer >= get_game_constants().BOSS.PHASE_INTERVAL and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire(player_pos)

    # ------------------------------------------------------------------
    # Damage & death
    # ------------------------------------------------------------------

    def take_damage(self, damage: int) -> int:
        """Apply damage to the boss. Returns score value if killed."""
        new_health, score_delta = self._state.compute_take_damage(damage)
        if new_health != self.health:
            self.health = new_health
        if score_delta:
            self.active = False
            self._state.mark_dead()
        return score_delta

    # ------------------------------------------------------------------
    # Public enrage predicates (delegate to state machine)
    # ------------------------------------------------------------------

    def is_enraged(self) -> bool:
        return self._state.enraged

    def is_enrage_active(self) -> bool:
        return self._state.is_enrage_active()

    def is_enrage_transitioning(self) -> bool:
        return self._state.is_enrage_transitioning()

    def should_lock_player_movement(self) -> bool:
        return self._state.should_lock_player_movement()

    def enrage_slow_factor(self) -> float:
        return self._state.enrage_slow_factor()

    def enrage_visual_intensity(self) -> float:
        return self._state.enrage_visual_intensity()

    # ------------------------------------------------------------------
    # Backward-compatible state-field shims
    #
    # Several tests (and a few non-test callers) used to read/write the
    # enrage state flags directly on the Boss instance. After the
    # Phase 1 split those flags live on :class:`BossStateMachine`; the
    # shims below keep the legacy attribute access working until those
    # callers are migrated.
    # ------------------------------------------------------------------

    @property
    def _enraged(self) -> bool:
        return self._state._enraged

    @_enraged.setter
    def _enraged(self, value: bool) -> None:
        self._state._enraged = bool(value)

    @property
    def _enrage_health_lock_active(self) -> bool:
        return self._state._enrage_health_lock_active

    @_enrage_health_lock_active.setter
    def _enrage_health_lock_active(self, value: bool) -> None:
        self._state._enrage_health_lock_active = bool(value)

    @property
    def _enrage_health_lock_value(self) -> int:
        return self._state._enrage_health_lock_value

    @_enrage_health_lock_value.setter
    def _enrage_health_lock_value(self, value: int) -> None:
        self._state._enrage_health_lock_value = int(value)

    @property
    def _enrage_attack_index(self) -> int:
        return self._state._enrage_attack_index

    @_enrage_attack_index.setter
    def _enrage_attack_index(self, value: int) -> None:
        self._state._enrage_attack_index = int(value)

    @property
    def _enrage_attack_timer(self) -> int:
        return self._state._enrage_attack_timer

    @_enrage_attack_timer.setter
    def _enrage_attack_timer(self, value: int) -> None:
        self._state._enrage_attack_timer = int(value)

    # ------------------------------------------------------------------
    # Backward-compatible private method shims
    #
    # These exist so tests / callers that previously poked the old
    # internal methods continue to work. The shims delegate to the
    # appropriate component and exist only for the duration of the
    # deprecation window. New code should call the components directly.
    # ------------------------------------------------------------------

    def _clamp_to_arena(self) -> None:
        self.rect.x, self.rect.y = self._movement.clamped_arena_position(self.rect.x, self.rect.y)

    def _clamped_arena_position(self, x: float, y: float) -> tuple[float, float]:
        return self._movement.clamped_arena_position(x, y)

    def _select_next_target(self, player_pos=None) -> None:
        self._movement.select_next_target(player_pos)

    def _fire(self, player_pos: tuple[float, float] | None = None) -> None:
        self.attack_direction = self._attack.choose_attack_direction()
        bullets: list[Bullet] = []
        if self.attack_pattern == 0:
            bullets = self._attack.spread_attack()
        elif self.attack_pattern == 1:
            if player_pos and self._movement.start_aim_dash(player_pos):
                self._aim_fire_target = (float(player_pos[0]), float(player_pos[1]))
                return
            bullets = self._attack.aim_attack(player_pos)
        else:
            bullets = self._attack.wave_attack()
        self._spawn_bullets(bullets)
        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _spawn_bullets(self, bullets: list[Bullet]) -> None:
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _aim_attack(self, player_pos: tuple[float, float] | None = None) -> list[Bullet]:
        return self._attack.aim_attack(player_pos)

    def _spread_attack(self) -> list[Bullet]:
        return self._attack.spread_attack()

    def _wave_attack(self) -> list[Bullet]:
        return self._attack.wave_attack()

    def _get_direction_offsets(self) -> dict:
        return self._attack.get_direction_offsets()

    def _get_direction_sources(self) -> dict:
        return self._attack.get_direction_sources()

    def _get_target_offsets(self) -> dict:
        return self._attack.get_target_offsets()

    def _select_attack_direction_for_target(self, player_pos: tuple[float, float]) -> None:
        self._attack.select_attack_direction_for_target(player_pos)

    def _boss_muzzle_positions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return self._attack.boss_muzzle_positions()

    def _primary_boss_muzzle_position(self) -> tuple[float, float]:
        return self._attack.primary_muzzle_position()

    def _trigger_muzzle_flash(self, position: tuple[float, float] | None = None) -> None:
        self._attack.trigger_muzzle_flash(position)

    def _update_muzzle_flash(self) -> None:
        self._attack.tick_muzzle_flash()

    def _face_target(self, target: tuple[float, float]) -> None:
        self._renderer.face_target(target)

    def _facing_vector(self):
        return self._renderer.facing_vector()

    def _is_aim_dashing(self) -> bool:
        return self._movement.is_aim_dashing()

    def _start_aim_dash(self, player_pos: tuple[float, float]) -> None:
        if not self._movement.start_aim_dash(player_pos):
            self._finish_aim_dash()

    def _update_aim_dash(self) -> None:
        if self._movement.tick_aim_dash():
            self._finish_aim_dash()

    def _finish_aim_dash(self) -> None:
        self._movement.finish_aim_dash()
        bullets = self._attack.aim_attack(self._aim_fire_target)
        self._aim_fire_target = None
        self._spawn_bullets(bullets)
        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _enrage_spawned_bullets(self) -> list[Bullet]:
        if hasattr(self._bullet_spawner, "get_bullets"):
            return self._bullet_spawner.get_bullets()
        if hasattr(self._bullet_spawner, "bullets"):
            return self._bullet_spawner.bullets
        if hasattr(self._bullet_spawner, "bullet_list"):
            return self._bullet_spawner.bullet_list
        return []

    # ------------------------------------------------------------------
    # Enrage orchestration
    # ------------------------------------------------------------------

    def _trigger_enrage_if_needed(
        self,
        player_pos: tuple[int, int] | None = None,
        player=None,
    ) -> None:
        if self._state.enraged or self.max_health <= 0:
            return
        if self.health / self.max_health > self.ENRAGE_TRIGGER_RATIO:
            return
        target = self._center_player_for_enrage(player, player_pos)
        self._state.trigger_enrage(target)
        self._renderer.face_target(target)
        self._attack.trigger_muzzle_flash()
        self._renderer.clear_enrage_trail()

    def _center_player_for_enrage(
        self,
        player=None,
        player_pos: tuple[int, int] | None = None,
    ) -> tuple[float, float]:
        target = (get_screen_width() / 2, get_screen_height() / 2)
        if player is not None:
            player.rect.x = target[0] - player.rect.width / 2
            player.rect.y = target[1] - player.rect.height / 2
            return target
        if player_pos:
            return (float(player_pos[0]), float(player_pos[1]))
        return target

    def _update_enrage_snapshot_attacks(
        self,
        target: tuple[float, float],
        progress: float,
    ) -> None:
        if not self._bullet_spawner or self._state.enrage_timer <= 1:
            return
        self._state.tick_enrage_attack_timer()
        if self._state.enrage_attack_timer > 0:
            return
        self._spawn_bullets(self._attack.create_enrage_snapshot_attack(target, progress))
        self._state.reset_enrage_attack_timer()

    def _create_enrage_snapshot_attack(self, target: tuple[float, float], progress: float) -> list[Bullet]:
        return self._attack.create_enrage_snapshot_attack(target, progress)

    def _release_enrage_bullets(self, target: tuple[float, float]) -> None:
        for bullet in self._enrage_spawned_bullets():
            if not getattr(bullet, "clear_immune", False) or not getattr(bullet, "held", False):
                continue
            direction = getattr(bullet, "release_direction", None)
            if direction is None or direction.length() <= 0:
                direction = Vector2(target[0] - bullet.rect.centerx, target[1] - bullet.rect.centery)
                direction = direction.normalize() if direction.length() > 0 else Vector2(0, 1)
            bullet.release_direction = direction
            bullet.enrage_release_pending = True
            bullet.enrage_release_delay = max(0, getattr(bullet, "enrage_release_delay", 0))
        # Compute the release anchor by walking the path all the way to 1.0.
        behind_center_x, behind_center_y = self._movement.enrage_path_center(target, 1.0)
        self._state.begin_enrage_release_hold((behind_center_x, behind_center_y))
        self._renderer.clear_enrage_trail()

    def _move_behind_player_after_enrage(self, target: tuple[float, float]) -> None:
        behind_center_x, behind_center_y = self._movement.enrage_path_center(target, 1.0)
        self.rect.x = behind_center_x - self.rect.width / 2
        self.rect.y = behind_center_y - self.rect.height / 2
        self._target_x = self.rect.x
        self._target_y = self.rect.y
        self.sync_hitbox()
        if target is not None:
            self._renderer.face_target(target)

    def _current_player_target(
        self, player=None, player_pos: tuple[int, int] | None = None
    ) -> tuple[float, float] | None:
        if player is not None:
            rect = player.rect
            if hasattr(rect, "centerx") and hasattr(rect, "centery"):
                return (float(rect.centerx), float(rect.centery))
            if all(hasattr(rect, attr) for attr in ("x", "y", "width", "height")):
                return (float(rect.x + rect.width / 2), float(rect.y + rect.height / 2))
        if player_pos:
            return (float(player_pos[0]), float(player_pos[1]))
        return None

    def _record_enrage_trail(self) -> None:
        self._renderer.record_enrage_trail()

    def _clamped_enrage_position(self, x: float, y: float) -> tuple[float, float]:
        return self._movement.clamped_enrage_position(x, y)

    def _enrage_path_radius(self, target: tuple[float, float]) -> float:
        return self._movement.enrage_path_radius(target)

    def _enrage_path_center(self, target: tuple[float, float], progress: float) -> tuple[float, float]:
        return self._movement.enrage_path_center(target, progress)

    def _update_enrage(self, player_pos: tuple[int, int] | None = None, player=None) -> None:
        """Legacy entrypoint — kept for tests that called it directly."""
        target = self._center_player_for_enrage(player, self._state.enrage_snapshot_target or player_pos)
        self._state._enrage_snapshot_target = target
        self._renderer.record_enrage_trail()
        progress = self._state.enrage_progress()
        self._movement.tick_enrage_active()
        self._renderer.face_target(target)
        self._attack.tick_muzzle_flash()
        self._update_enrage_snapshot_attacks(target, progress)
        self._state.tick_enrage_timer()
        if self._state.enrage_timer <= 0:
            self._move_behind_player_after_enrage(target)
            self._release_enrage_bullets(target)

    def _update_enrage_transition(self, player_pos: tuple[int, int] | None = None, player=None) -> None:
        target = self._center_player_for_enrage(player, self._state.enrage_snapshot_target or player_pos)
        self._state._enrage_snapshot_target = target
        self._movement.tick_enrage_transition()
        self._renderer.face_target(target)
        self._attack.tick_muzzle_flash()
        self._state.tick_enrage_transition_timer()
        if self._state.enrage_transition_timer <= 0:
            self._state.finish_enrage_transition()

    def _update_enrage_release_hold(self, player_pos: tuple[int, int] | None = None, player=None) -> None:
        target = (
            self._current_player_target(player, player_pos)
            or self._state.enrage_snapshot_target
            or (get_screen_width() / 2, get_screen_height() / 2)
        )
        self._movement.tick_enrage_release_hold()
        self._renderer.face_target(target)
        self._attack.tick_muzzle_flash()
        self._state.tick_enrage_release_hold_timer()
        if self._state.enrage_release_hold_timer <= 0:
            self._movement.start_enrage_return()

    def _start_enrage_return(self) -> None:
        self._movement.start_enrage_return()

    def _update_enrage_return(self, player_pos: tuple[int, int] | None = None, player=None) -> None:
        target = self._current_player_target(player, player_pos) or self._state.enrage_snapshot_target
        self._movement.tick_enrage_return()
        if target is not None:
            self._renderer.face_target(target)
        self._attack.tick_muzzle_flash()
        self._state.tick_enrage_return_timer()
        if self._state.enrage_return_timer <= 0:
            self._state.finish_enrage_return()

    def _enrage_progress(self) -> float:
        return self._state.enrage_progress()

    # ------------------------------------------------------------------
    # Renderer
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        self._renderer.draw(surface)

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)
