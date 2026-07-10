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


_ENEMY_TUNING = get_game_constants().ENEMY_TUNING


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

    # Backward-compatible aliases. The values are sourced from
    # GAME_CONSTANTS.ENEMY_TUNING so enemy tuning has one definition.
    ENTRY_START_Y = _ENEMY_TUNING.ENTRY_START_Y
    EXIT_X_OFFSETS = _ENEMY_TUNING.EXIT_X_OFFSETS
    EXIT_END_Y = _ENEMY_TUNING.EXIT_END_Y
    EXIT_ACTIVE_END_Y = _ENEMY_TUNING.EXIT_ACTIVE_END_Y
    TRANSITION_DURATION = _ENEMY_TUNING.TRANSITION_DURATION
    ENTRY_SPEED = _ENEMY_TUNING.ENTRY_SPEED
    EXIT_SPEED = _ENEMY_TUNING.EXIT_SPEED
    FIRE_RATE_MIN = _ENEMY_TUNING.FIRE_RATE_MIN
    ENEMY_BULLET_SPEED = _ENEMY_TUNING.ENEMY_BULLET_SPEED

    SINE_AMP_RANGE = _ENEMY_TUNING.SINE_AMP_RANGE
    SINE_FREQ_RANGE = _ENEMY_TUNING.SINE_FREQ_RANGE
    ZIGZAG_INTERVAL_RANGE = _ENEMY_TUNING.ZIGZAG_INTERVAL_RANGE
    ZIGZAG_SPEED_RANGE = _ENEMY_TUNING.ZIGZAG_SPEED_RANGE
    DIVE_DELAY_RANGE = _ENEMY_TUNING.DIVE_DELAY_RANGE
    HOVER_SPEED_RANGE = _ENEMY_TUNING.HOVER_SPEED_RANGE
    HOVER_AMP_RANGE = _ENEMY_TUNING.HOVER_AMP_RANGE
    SPIRAL_SPEED_RANGE = _ENEMY_TUNING.SPIRAL_SPEED_RANGE
    SPIRAL_RADIUS_RANGE = _ENEMY_TUNING.SPIRAL_RADIUS_RANGE
    SPIRAL_FREQ_RANGE = _ENEMY_TUNING.SPIRAL_FREQ_RANGE
    NOISE_SPEED_RANGE = _ENEMY_TUNING.NOISE_SPEED_RANGE
    NOISE_SCALE_X_RANGE = _ENEMY_TUNING.NOISE_SCALE_X_RANGE
    NOISE_SCALE_Y_RANGE = _ENEMY_TUNING.NOISE_SCALE_Y_RANGE
    NOISE_AMP_X_RANGE = _ENEMY_TUNING.NOISE_AMP_X_RANGE
    NOISE_AMP_Y_RANGE = _ENEMY_TUNING.NOISE_AMP_Y_RANGE
    AGGR_SPEED_RANGE = _ENEMY_TUNING.AGGR_SPEED_RANGE
    AGGR_SCALE_X_RANGE = _ENEMY_TUNING.AGGR_SCALE_X_RANGE
    AGGR_SCALE_Y_RANGE = _ENEMY_TUNING.AGGR_SCALE_Y_RANGE
    AGGR_AMP_X_RANGE = _ENEMY_TUNING.AGGR_AMP_X_RANGE
    AGGR_AMP_Y_RANGE = _ENEMY_TUNING.AGGR_AMP_Y_RANGE
    SPREAD_FIRE_OFFSETS = _ENEMY_TUNING.SPREAD_FIRE_OFFSETS
    HOVER_TIMER_RUST_SCALE = _ENEMY_TUNING.HOVER_TIMER_RUST_SCALE
    DEFAULT_MOVE_AMPLITUDE = _ENEMY_TUNING.DEFAULT_MOVE_AMPLITUDE
    DEFAULT_MOVE_FREQUENCY = _ENEMY_TUNING.DEFAULT_MOVE_FREQUENCY
    DEFAULT_MOVE_SPEED = _ENEMY_TUNING.DEFAULT_MOVE_SPEED
    DEFAULT_NOISE_SPEED = _ENEMY_TUNING.DEFAULT_NOISE_SPEED
    DEFAULT_AGGRESSIVE_SPEED = _ENEMY_TUNING.DEFAULT_AGGRESSIVE_SPEED
    DEFAULT_ZIGZAG_INTERVAL = _ENEMY_TUNING.DEFAULT_ZIGZAG_INTERVAL
    DEFAULT_SPIRAL_RADIUS = _ENEMY_TUNING.DEFAULT_SPIRAL_RADIUS
    DEFAULT_NOISE_SCALE_X = _ENEMY_TUNING.DEFAULT_NOISE_SCALE_X
    DEFAULT_NOISE_SCALE_Y = _ENEMY_TUNING.DEFAULT_NOISE_SCALE_Y
    DEFAULT_NOISE_AMPLITUDE_X = _ENEMY_TUNING.DEFAULT_NOISE_AMPLITUDE_X
    DEFAULT_NOISE_AMPLITUDE_Y = _ENEMY_TUNING.DEFAULT_NOISE_AMPLITUDE_Y
    DEFAULT_AGGRESSIVE_AMPLITUDE_X = _ENEMY_TUNING.DEFAULT_AGGRESSIVE_AMPLITUDE_X
    DEFAULT_AGGRESSIVE_AMPLITUDE_Y = _ENEMY_TUNING.DEFAULT_AGGRESSIVE_AMPLITUDE_Y

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
        """Return (base_tuple, extra_tuple) for batch Rust movement, or (None, None).

        F07 god-class split: the 173-line encoding logic is in
        :mod:`airwar.entities.enemy.enemy_movement_batch`. This method
        is a 1-line forwarder kept for backward compatibility with
        GameLoopManager callers.
        """
        from .enemy_movement_batch import encode_rust_movement_params

        return encode_rust_movement_params(self)

    # 5. Private lifecycle methods

    def _init_movement(self, enemy_type: str) -> None:
        init_method = self._movement_initializers().get(enemy_type, self._init_straight_movement)
        init_method()
        self._movement_strategy = get_movement_strategy(self.move_type)
        # F07 god-class split: extracted to enemy_movement_batch.py
        from .enemy_movement_batch import configure_rust_movement

        configure_rust_movement(self)

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
        """Backward-compat shim: delegates to :func:`configure_rust_movement`.

        F07 god-class split: the actual logic lives in
        :mod:`airwar.entities.enemy.enemy_movement_batch`. This method
        provides the entity-level entry point used by movement setup.
        """
        from .enemy_movement_batch import configure_rust_movement

        configure_rust_movement(self)

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

    # Backward-compatible aliases for values in GAME_CONSTANTS.ENEMY_TUNING.
    ENEMIES_PER_FRAME = _ENEMY_TUNING.ENEMIES_PER_FRAME
    DEFAULT_SPEED = _ENEMY_TUNING.DEFAULT_SPEED
    DEFAULT_SPAWN_RATE = _ENEMY_TUNING.DEFAULT_SPAWN_RATE
    MAX_CONCURRENT_ENEMIES = _ENEMY_TUNING.MAX_CONCURRENT_ENEMIES
    ELITES_PER_WAVE = _ENEMY_TUNING.ELITES_PER_WAVE
    MIN_SPAWN_Y = _ENEMY_TUNING.MIN_SPAWN_Y
    MAX_SPAWN_Y_FRACTION = _ENEMY_TUNING.MAX_SPAWN_Y_FRACTION
    LASER_FIRE_RATE = _ENEMY_TUNING.LASER_FIRE_RATE
    NORMAL_FIRE_RATE = _ENEMY_TUNING.NORMAL_FIRE_RATE
    ENTRY_SPAWN_Y = _ENEMY_TUNING.ENTRY_SPAWN_Y
    DEFAULT_SPREAD_ENEMY_CAP = _ENEMY_TUNING.DEFAULT_SPREAD_ENEMY_CAP

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

    # Backward-compatible aliases for values in GAME_CONSTANTS.ENEMY_TUNING.
    VISUAL_SCALE = _ENEMY_TUNING.VISUAL_SCALE
    COLLISION_SCALE = _ENEMY_TUNING.COLLISION_SCALE
    ENTRY_SPEED = _ENEMY_TUNING.ELITE_ENTRY_SPEED
    ELITE_FIRE_RATE = _ENEMY_TUNING.ELITE_FIRE_RATE
    MIN_SPAWN_Y = _ENEMY_TUNING.MIN_SPAWN_Y
    SPAWN_START_Y = _ENEMY_TUNING.SPAWN_START_Y

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
