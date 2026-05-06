"""Enemy and Boss entities with movement patterns and attack behaviors."""
import math
import random
from collections import deque
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING

import pygame

from .base import Entity, EnemyData, Vector2
from .bullet import Bullet, BulletData
from .interfaces import IBulletSpawner
from airwar.config import (
    ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING, ENEMY_VISUAL_SCALE, ENEMY_COLLISION_SCALE,
    get_screen_width, get_screen_height,
)

from airwar.config.constants_access import get_game_constants
from .movement_strategies import get_movement_strategy

from airwar.core_bindings import update_movement as rust_update_movement

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
            collision_size
        )

        super().__init__(x, y, render_size, render_size)

        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self.entity_id = id(self)
        self._init_movement(data.enemy_type)
        self.sync_rects()
        self._difficulty_multiplier = 1.0
        self._fire_rate_modifier = 1.0
        self._movement_enhancements = {}

        # Wave system: entry/exit states
        self._state = 'entering'
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

        if self._state == 'entering':
            self._update_entry_state()
            return

        if self._state == 'exiting':
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
        self._state = 'active'
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
        self._state = 'exiting'
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
        return self.move_type in MOVEMENT_TYPE_MAP and self.move_type != "zigzag"

    def _update_rust_movement(self) -> None:
        batch_result = getattr(self, '_batch_result', None)
        if batch_result is not None:
            self._apply_rust_movement_result(batch_result)
            del self._batch_result
            return

        timer = getattr(self, self._timer_attr, 0.0)
        if self.move_type == "hover":
            timer /= self.HOVER_TIMER_RUST_SCALE

        params = self._rust_params
        new_x, new_y, new_timer = rust_update_movement(
            self._rust_move_type_code, timer,
            self.active_position_x, self.active_position_y,
            self._move_range_x, self._move_range_y,
            params['offset'], params['amplitude'], params['frequency'], params['speed'], params['direction'],
            params['zigzag_interval'], params['spiral_radius'],
            self.rect.x, self.rect.y,
            params['noise_scale_x'], params['noise_scale_y'],
            params['noise_amplitude_x'], params['noise_amplitude_y'],
            params['noise_seed'],
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
        fire_threshold = max(self.FIRE_RATE_MIN, int(self.data.fire_rate / self._fire_rate_modifier))
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
        self,
        speed_mult: float,
        fire_rate_modifier: float,
        movement_enhancements: dict = None
    ) -> None:
        self._difficulty_multiplier = speed_mult
        self._fire_rate_modifier = fire_rate_modifier
        self._movement_enhancements = movement_enhancements or {}

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite

    def begin_exit(self, x_offset: float, end_y: float) -> None:
        """Begin the exit animation sequence.

        Forces the enemy into 'exiting' state and sets the target
        position for the exit animation curve.

        Args:
            x_offset: Target x-coordinate for exit end position.
            end_y: Target y-coordinate for exit end position.
        """
        self._state = 'exiting'
        self._exit_start_x = self.rect.x
        self._exit_start_y = self.rect.y
        self._exit_end_x = x_offset
        self._exit_end_y = end_y
        self._exit_progress = 0.0

    def is_active_in_wave(self) -> bool:
        return self.active and self._state != 'exiting'

    def is_ready_for_batch_movement(self) -> bool:
        return self.active and self._state == 'active'

    def apply_batch_movement_result(self, result: tuple[float, float, float]) -> None:
        self._batch_result = result

    def get_rust_batch_params(self):
        """Return (base_tuple, extra_tuple) for batch Rust movement, or (None, None)."""
        if not hasattr(self, '_rust_move_type_code') or self.move_type == "zigzag":
            return None, None
        p = self._rust_params
        timer = getattr(self, self._timer_attr, 0.0)
        if self.move_type == "hover":
            timer /= self.HOVER_TIMER_RUST_SCALE
        c = get_game_constants()
        base = (
            self._rust_move_type_code, timer,
            self.active_position_x, self.active_position_y,
            float(c.ENEMY.MOVE_RANGE_X), float(c.ENEMY.MOVE_RANGE_Y),
            p['offset'], p['amplitude'], p['frequency'], p['speed'], p['direction'],
            p['zigzag_interval'],
        )
        extra = (
            p['spiral_radius'], self.rect.x, self.rect.y,
            p['noise_scale_x'], p['noise_scale_y'],
            p['noise_amplitude_x'], p['noise_amplitude_y'],
            p['noise_seed'],
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
            'offset': getattr(self, 'move_offset', 0.0),
            'amplitude': getattr(self, 'move_amplitude', self.DEFAULT_MOVE_AMPLITUDE),
            'frequency': self._rust_frequency_param(),
            'speed': self._rust_speed_param(),
            'direction': getattr(self, 'direction', 1.0),
            'zigzag_interval': getattr(self, 'zigzag_interval', self.DEFAULT_ZIGZAG_INTERVAL),
            'spiral_radius': getattr(self, 'spiral_radius', self.DEFAULT_SPIRAL_RADIUS),
            'noise_scale_x': self._rust_noise_param('scale_x'),
            'noise_scale_y': self._rust_noise_param('scale_y'),
            'noise_amplitude_x': self._rust_noise_param('amplitude_x'),
            'noise_amplitude_y': self._rust_noise_param('amplitude_y'),
            'noise_seed': getattr(self, 'agg_seed', 0) if self.move_type == "aggressive" else getattr(self, 'noise_seed', 0),
        }
        if self.move_type == "hover":
            self._timer_attr = "hover_timer"
        elif self.move_type in ("zigzag", "dive", "spiral", "noise", "aggressive"):
            self._timer_attr = f"{self.move_type}_timer"
        else:
            self._timer_attr = "move_timer"

    def _rust_frequency_param(self) -> float:
        if self.move_type == "spiral":
            return getattr(self, 'spiral_frequency', self.DEFAULT_MOVE_FREQUENCY)
        return getattr(self, 'move_frequency', self.DEFAULT_MOVE_FREQUENCY)

    def _rust_speed_param(self) -> float:
        if self.move_type == "zigzag":
            return getattr(self, 'zigzag_speed', self.DEFAULT_MOVE_SPEED)
        if self.move_type == "noise":
            return getattr(self, 'noise_speed', self.DEFAULT_NOISE_SPEED)
        if self.move_type == "aggressive":
            return getattr(self, 'agg_speed', self.DEFAULT_AGGRESSIVE_SPEED)
        return getattr(self, 'spiral_speed', self.DEFAULT_MOVE_SPEED)

    def _rust_noise_param(self, name: str) -> float:
        if self.move_type == "aggressive":
            defaults = {
                'scale_x': self.DEFAULT_NOISE_SCALE_X,
                'scale_y': self.DEFAULT_NOISE_SCALE_Y,
                'amplitude_x': self.DEFAULT_AGGRESSIVE_AMPLITUDE_X,
                'amplitude_y': self.DEFAULT_AGGRESSIVE_AMPLITUDE_Y,
            }
            return getattr(self, f"agg_{name}", defaults[name])

        defaults = {
            'scale_x': self.DEFAULT_NOISE_SCALE_X,
            'scale_y': self.DEFAULT_NOISE_SCALE_Y,
            'amplitude_x': self.DEFAULT_NOISE_AMPLITUDE_X,
            'amplitude_y': self.DEFAULT_NOISE_AMPLITUDE_Y,
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

    def _create_bullets(self) -> List[Bullet]:
        bullets = []
        center_x = self.rect.centerx

        if self.data.bullet_type == "spread":
            for angle in self.SPREAD_FIRE_OFFSETS:
                bullet_data = BulletData(
                    damage=self._get_damage(),
                    speed=5.0,
                    owner="enemy",
                    bullet_type="spread"
                )
                bullet = Bullet(center_x + angle, self.rect.bottom, bullet_data)
                bullet.velocity = Vector2(angle * 0.15, 5)
                bullets.append(bullet)
        elif self.data.bullet_type == "laser":
            bullet_data = BulletData(
                damage=self._get_damage(),
                speed=5.0,
                owner="enemy",
                bullet_type="laser"
            )
            bullet = Bullet(center_x, self.rect.bottom, bullet_data)
            bullet.velocity = Vector2(0, 8)
            bullets.append(bullet)
        else:
            bullet_data = BulletData(
                damage=self._get_damage(),
                speed=5.0,
                owner="enemy",
                bullet_type="single"
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
        self._bullet_spawner: Optional[IBulletSpawner] = None
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

    def update(self, enemies: List[Enemy], slow_factor: float = 1.0,
               player_pos: tuple = None) -> None:
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

    def _prepare_wave_data(self, player_pos: tuple = None) -> deque:
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

        for i, (px, py) in enumerate(positions):
            px = max(collision_size // 2, min(px, screen_width - collision_size // 2))
            py = max(self.MIN_SPAWN_Y, min(py, int(screen_height * self.MAX_SPAWN_Y_FRACTION)))
            if i in elite_indices:
                spawn_data.append((
                    px, py,
                    random.choice(elite_bullet_types),
                    self._select_elite_type(),
                    True,  # is_elite flag
                ))
            else:
                spawn_data.append((
                    px, py,
                    random.choice(bullet_types),
                    self._select_enemy_type(),
                    False,
                ))
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

    def _spawn_one(self, enemies: List[Enemy], data: tuple) -> None:
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
                enemy_type=enemy_type
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

    def update(self, enemies: List['Enemy'] = None, slow_factor: float = 1.0,
               player_pos: Tuple[int, int] = None, *args, **kwargs) -> None:
        self._shield_pulse += 0.08
        super().update(enemies, slow_factor, player_pos, *args, **kwargs)


@dataclass
class BossData:
    """Data class for Boss entity configuration.

    Attributes:
        health: Maximum health points.
        speed: Movement speed in pixels per frame.
        score: Score awarded when defeated.
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
    """Boss entity with phase-based attacks.

    Boss class handles movement, phase transitions, and multiple attack patterns
    (spread, aim, wave). Boss has 3 phases that increase in difficulty. Boss will
    escape after survival_timer reaches escape_time.

    Attributes:
        data: BossData configuration.
        health: Current health points.
        max_health: Maximum health points.
        phase: Current attack phase (1-3).
        fire_timer: Timer for attack fire rate.
        attack_pattern: Current attack pattern index (0-2).
        survival_timer: Frames survived in battle.
        escaped: Whether the boss has escaped.
        _bullet_spawner: Optional spawner for bullets.
    """

    ATTACK_DIRECTIONS = ['down', 'left', 'right', 'up']
    DEFAULT_PHASE_DURATION = 120
    ENTRY_SPEED = 2
    ESCAPE_DRIFT = 0.5
    LERP_FACTOR = 0.025
    MIN_Y = 50
    CENTER_OFFSET = 60
    SPREAD_DAMAGE_INCREMENT = 2
    AIM_DAMAGE_INCREMENT = 3
    AIM_BULLET_COUNT = 3
    WAVE_BULLET_COUNT = 8
    HITBOX_WIDTH_SCALE = 1.78
    HITBOX_HEIGHT_SCALE = 1.22
    AIM_DASH_DISTANCE = 220
    AIM_DASH_PHASE_BONUS = 35
    AIM_DASH_MAX_DISTANCE_RATIO = 0.58
    AIM_DASH_DURATION = 10
    ENRAGE_TRIGGER_RATIO = 0.30
    ENRAGE_DURATION = 360
    ENRAGE_TRANSITION_DURATION = 54
    ENRAGE_SLOW_FACTOR = 0.24
    ENRAGE_BULLET_SPEED = 3.2
    ENRAGE_LASER_SPEED = 3.7
    ENRAGE_RELEASE_BULLET_SPEED = 1.55
    ENRAGE_RELEASE_LASER_SPEED = 1.35
    ENRAGE_ATTACK_INTERVAL = 42
    ENRAGE_ATTACK_WINDUP = 24
    ENRAGE_RELEASE_INTERVAL = 6
    ENRAGE_SNAPSHOT_LASER_COUNT = 4
    ENRAGE_SNAPSHOT_RING_COUNT = 8
    ENRAGE_PATH_RADIUS_SCALE = 1.50
    ENRAGE_SQUARE_PATH_RATIO = 0.48
    ENRAGE_TRAIL_LENGTH = 42
    ENRAGE_TRAIL_RENDER_MAX = 16
    ENRAGE_TRAIL_FINAL_SCALE = 3.0
    ENRAGE_TRAIL_SCALE = 0.5
    ENRAGE_TRAIL_BLUR_PASSES = 2
    ENRAGE_EXIT_BACK_OFFSET = 118
    ENRAGE_MUZZLE_FLASH_DURATION = 12
    ENRAGE_MUZZLE_FLASH_PULSES = 2
    ENRAGE_MUZZLE_FORWARD_SCALE = 0.58
    ENRAGE_MUZZLE_SIDE_SCALE = 0.34
    ENRAGE_RELEASE_HOLD_DURATION = 42
    ENRAGE_RETURN_DURATION = 48
    ENRAGE_CORE_COLOR = (126, 220, 255)
    ENRAGE_DANGER_COLOR = (230, 72, 68)
    ENRAGE_TRAIL_TINT = (96, 154, 220)

    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.attack_pattern = 0
        self.attack_direction = 'down'
        self.entering = True
        self.entry_y = y
        self.target_y = 180
        # Movement phase system
        self._move_phase = 0
        self._move_phase_timer = 0
        self._move_phase_duration = self.DEFAULT_PHASE_DURATION
        self._target_x: float = float(x)
        self._target_y: float = 180.0
        self.survival_timer = 0
        self.escaped = False
        self._show_escape_warning = False
        self.phase = data.phase
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self.entity_id = id(self)
        self._hitbox = pygame.Rect(0, 0, 0, 0)
        self._aim_dash_elapsed = 0
        self._aim_dash_duration = 0
        self._aim_dash_start_x = 0.0
        self._aim_dash_start_y = 0.0
        self._aim_dash_target_x = 0.0
        self._aim_dash_target_y = 0.0
        self._aim_fire_target: Optional[Tuple[float, float]] = None
        self._enraged = False
        self._enrage_timer = 0
        self._enrage_bullets_released = False
        self._enrage_snapshot_target: Tuple[float, float] | None = None
        self._enrage_trail: List[Tuple[float, float]] = []
        self._enrage_trail_ghost = None
        self._enrage_trail_ghost_key = None
        self._enrage_health_lock_active = False
        self._enrage_health_lock_value = data.health * self.ENRAGE_TRIGGER_RATIO
        self._enrage_attack_timer = 0
        self._enrage_attack_index = 0
        self._enrage_transition_timer = 0
        self._enrage_transition_origin: Tuple[float, float] | None = None
        self._facing_angle = 90.0
        self._muzzle_flash_timer = 0
        self._muzzle_flash_positions: List[Tuple[float, float]] = []
        self._enrage_release_hold_timer = 0
        self._enrage_release_anchor: Tuple[float, float] | None = None
        self._enrage_return_timer = 0
        self._enrage_return_origin: Tuple[float, float] | None = None
        self._enrage_return_target: Tuple[float, float] | None = None
        self.sync_hitbox()

    def sync_hitbox(self) -> None:
        self._hitbox.width = int(self.rect.width * self.HITBOX_WIDTH_SCALE)
        self._hitbox.height = int(self.rect.height * self.HITBOX_HEIGHT_SCALE)
        self._hitbox.center = (int(self.rect.centerx), int(self.rect.centery))

    def get_hitbox(self) -> pygame.Rect:
        self.sync_hitbox()
        return self._hitbox

    def _get_direction_offsets(self) -> dict:
        return {
            'down': (-90, self.rect.bottom),
            'left': (180, self.rect.centery),
            'right': (0, self.rect.centery),
            'up': (90, self.rect.y)
        }

    def _get_direction_sources(self) -> dict:
        return {
            'down': (self.rect.centerx, self.rect.bottom),
            'left': (self.rect.left, self.rect.centery),
            'right': (self.rect.right, self.rect.centery),
            'up': (self.rect.centerx, self.rect.y)
        }

    def _get_target_offsets(self) -> dict:
        d = get_game_constants().BOSS.ATTACK_DISTANCE
        return {
            'down': (0, d),
            'left': (-d, 0),
            'right': (d, 0),
            'up': (0, -d)
        }

    def update(self, enemies: List['Enemy'] = None, slow_factor: float = 1.0,
              player_pos: Tuple[int, int] = None, *args, **kwargs) -> None:
        """Update boss state each frame.

        Handles entrance animation, survival timer, horizontal movement,
        phase transitions, and attack firing based on fire rate.

        Args:
            enemies: List of active enemies (for context).
            slow_factor: Time dilation factor from slow field buffs.
            player_pos: (x, y) of the player for aim attacks.
        """
        if self.entering:
            self.rect.y += self.ENTRY_SPEED * slow_factor
            if self.rect.y >= self.target_y:
                self.rect.y = self.target_y
                self.entering = False
            return

        self._trigger_enrage_if_needed(player_pos, kwargs.get("player"))
        if self._enrage_transition_timer > 0:
            self._update_enrage_transition(player_pos, kwargs.get("player"))
            return
        if self._enrage_timer > 0:
            self._update_enrage(player_pos, kwargs.get("player"))
            return
        if self._enrage_release_hold_timer > 0:
            self._update_enrage_release_hold(player_pos, kwargs.get("player"))
            return
        if self._enrage_return_timer > 0:
            self._update_enrage_return(player_pos, kwargs.get("player"))
            return

        self.survival_timer += 1

        if self.survival_timer >= self.data.escape_time:
            self.escaped = True
            self.active = False
            return

        if self.survival_timer >= self.data.escape_time - get_game_constants().ENEMY.ESCAPE_WARNING:
            self._show_escape_warning = True
            self.rect.y -= self.ESCAPE_DRIFT

        if self._is_aim_dashing():
            self._update_aim_dash()
            return

        self._move_phase_timer += 1
        if self._move_phase_timer >= self._move_phase_duration:
            self._move_phase_timer = 0
            self._move_phase_duration = random.randint(90, 200)
            self._select_next_target(player_pos)

        lerp_speed = self.LERP_FACTOR * self.data.speed
        self.rect.x = self.rect.x + (self._target_x - self.rect.x) * lerp_speed
        self.rect.y = self.rect.y + (self._target_y - self.rect.y) * lerp_speed

        self._clamp_to_arena()

        self.rect.y += math.sin(self.survival_timer * 0.025) * 0.4

        self.phase_timer += 1
        if self.phase_timer >= get_game_constants().BOSS.PHASE_INTERVAL and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire(player_pos)

    def _clamp_to_arena(self) -> None:
        self.rect.x, self.rect.y = self._clamped_arena_position(self.rect.x, self.rect.y)

    def _clamped_arena_position(self, x: float, y: float) -> Tuple[float, float]:
        screen_w = get_screen_width()
        screen_h = get_screen_height()
        return (
            max(0, min(x, screen_w - self.rect.width)),
            max(self.MIN_Y, min(y, screen_h // 2 + self.CENTER_OFFSET)),
        )

    def _select_next_target(self, player_pos=None) -> None:
        """Pick next movement target based on cycling phase.

        Cycles through 4 phases: PATROL → SWEEP → HOVER → CHASE.
        All phases include both horizontal and vertical movement.
        """
        screen_w = get_screen_width()
        screen_h = get_screen_height()
        margin = 50
        x_min = margin + 60
        x_max = screen_w - self.rect.width - margin - 60
        # Vertical band: from near top to middle of screen
        y_min = 60
        y_max = screen_h // 2

        phase = self._move_phase % 4
        self._move_phase += 1

        if phase == 0:
            # PATROL: move to opposite horizontal side with vertical drift
            if self.rect.centerx < screen_w // 2:
                self._target_x = x_max
            else:
                self._target_x = x_min
            self._target_y = random.randint(y_min, y_max)

        elif phase == 1:
            # SWEEP: diagonal across screen to a new zone
            self._target_x = random.randint(x_min, x_max)
            self._target_y = random.randint(y_min, y_max)

        elif phase == 2:
            # HOVER: local repositioning with gentle drift
            self._target_x = random.randint(
                int(max(margin, self.rect.x - 130)),
                int(min(screen_w - self.rect.width - margin, self.rect.x + 130))
            )
            self._target_y = random.randint(
                int(max(y_min, self.rect.y - 80)),
                int(min(y_max, self.rect.y + 80))
            )

        else:
            # CHASE: drift toward player area with random offset
            if player_pos:
                self._target_x = max(x_min,
                    min(player_pos[0] + random.randint(-60, 60), x_max))
                self._target_y = max(y_min,
                    min(player_pos[1] - random.randint(80, 160), y_max))
            else:
                self._target_x = random.randint(x_min, x_max)
                self._target_y = random.randint(y_min, y_max)

    def _fire(self, player_pos: Tuple[float, float] = None) -> None:
        bullets = []

        self.attack_direction = random.choice(self.ATTACK_DIRECTIONS)

        if self.attack_pattern == 0:
            bullets = self._spread_attack()
        elif self.attack_pattern == 1:
            if player_pos:
                self._start_aim_dash(player_pos)
                return
            bullets = self._aim_attack()
        else:
            bullets = self._wave_attack()

        self._spawn_bullets(bullets)

        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _spawn_bullets(self, bullets: List[Bullet]) -> None:
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _trigger_enrage_if_needed(self, player_pos: Tuple[int, int] = None, player=None) -> None:
        if self._enraged or self.max_health <= 0:
            return
        if self.health / self.max_health > self.ENRAGE_TRIGGER_RATIO:
            return

        target = self._center_player_for_enrage(player, player_pos)
        self._enraged = True
        self._enrage_timer = self.ENRAGE_DURATION
        self._enrage_bullets_released = False
        self._enrage_health_lock_active = True
        self.health = max(self.health, self._enrage_health_lock_value)
        self._enrage_snapshot_target = target
        self._enrage_trail.clear()
        self._enrage_trail_ghost = None
        self._enrage_trail_ghost_key = None
        self._enrage_attack_timer = self.ENRAGE_ATTACK_WINDUP
        self._enrage_attack_index = 0
        self._enrage_transition_timer = self.ENRAGE_TRANSITION_DURATION
        self._enrage_transition_origin = (self.rect.centerx, self.rect.centery)
        self._enrage_release_hold_timer = 0
        self._enrage_release_anchor = None
        self._enrage_return_timer = 0
        self._enrage_return_origin = None
        self._enrage_return_target = None
        self._face_target(target)
        self._muzzle_flash_timer = 0
        self._muzzle_flash_positions = []

    def _center_player_for_enrage(self, player=None, player_pos: Tuple[int, int] = None) -> Tuple[float, float]:
        target = (get_screen_width() / 2, get_screen_height() / 2)
        if player is not None:
            player.rect.x = target[0] - player.rect.width / 2
            player.rect.y = target[1] - player.rect.height / 2
            return target
        return (float(player_pos[0]), float(player_pos[1])) if player_pos else target

    def _update_enrage(self, player_pos: Tuple[int, int] = None, player=None) -> None:
        target = self._center_player_for_enrage(player, self._enrage_snapshot_target or player_pos)
        self._enrage_snapshot_target = target
        self._record_enrage_trail()

        progress = self._enrage_progress()
        target_center_x, target_center_y = self._enrage_path_center(target, progress)
        self.rect.x, self.rect.y = self._clamped_enrage_position(
            target_center_x - self.rect.width / 2,
            target_center_y - self.rect.height / 2,
        )
        self.sync_hitbox()
        self._face_target(target)
        self._update_muzzle_flash()
        self._update_enrage_snapshot_attacks(target, progress)

        self._enrage_timer -= 1
        if self._enrage_timer <= 0:
            self._move_behind_player_after_enrage(target)
            self._release_enrage_bullets(target)

    def _update_enrage_transition(self, player_pos: Tuple[int, int] = None, player=None) -> None:
        target = self._center_player_for_enrage(player, self._enrage_snapshot_target or player_pos)
        self._enrage_snapshot_target = target

        elapsed = self.ENRAGE_TRANSITION_DURATION - self._enrage_transition_timer
        transition = max(0.0, min(1.0, elapsed / max(1, self.ENRAGE_TRANSITION_DURATION)))
        eased = 1.0 - (1.0 - transition) ** 3

        start = self._enrage_transition_origin or (self.rect.centerx, self.rect.centery)
        orbit_progress = self._enrage_progress()
        target_center_x, target_center_y = self._enrage_path_center(target, orbit_progress)
        charge_shake_x = math.sin(transition * math.tau * 7.0) * (1.0 - transition) * 13.0
        charge_shake_y = math.cos(transition * math.tau * 5.0) * (1.0 - transition) * 8.0
        center_x = start[0] + (target_center_x - start[0]) * eased + charge_shake_x
        center_y = start[1] + (target_center_y - start[1]) * eased + charge_shake_y
        self.rect.x, self.rect.y = self._clamped_enrage_position(
            center_x - self.rect.width / 2,
            center_y - self.rect.height / 2,
        )
        self.sync_hitbox()
        self._face_target(target)
        self._update_muzzle_flash()

        self._enrage_transition_timer -= 1
        self._enrage_timer -= 1
        if self._enrage_timer <= 0:
            self._enrage_transition_timer = 0
            self._move_behind_player_after_enrage(target)
            self._release_enrage_bullets(target)
        elif self._enrage_transition_timer <= 0:
            self._enrage_transition_timer = 0
            self._enrage_transition_origin = None

    def _enrage_progress(self) -> float:
        return max(0.0, min(1.0, 1.0 - self._enrage_timer / self.ENRAGE_DURATION))

    def _update_enrage_release_hold(self, player_pos: Tuple[int, int] = None, player=None) -> None:
        target = self._current_player_target(player, player_pos) or self._enrage_snapshot_target or (
            get_screen_width() / 2,
            get_screen_height() / 2,
        )
        anchor = self._enrage_release_anchor or self._enrage_path_center(target, 1.0)
        self.rect.x = anchor[0] - self.rect.width / 2
        self.rect.y = anchor[1] - self.rect.height / 2
        self._target_x = self.rect.x
        self._target_y = self.rect.y
        self.sync_hitbox()
        self._face_target(target)
        self._update_muzzle_flash()
        self._enrage_release_hold_timer -= 1
        if self._enrage_release_hold_timer <= 0:
            self._enrage_release_anchor = None
            self._start_enrage_return()

    def _start_enrage_return(self) -> None:
        self._enrage_return_timer = self.ENRAGE_RETURN_DURATION
        self._enrage_return_origin = (self.rect.x, self.rect.y)
        target_x, target_y = self._clamped_arena_position(self.rect.x, self.rect.y)
        self._enrage_return_target = (target_x, target_y)

    def _update_enrage_return(self, player_pos: Tuple[int, int] = None, player=None) -> None:
        target = self._current_player_target(player, player_pos) or self._enrage_snapshot_target
        elapsed = self.ENRAGE_RETURN_DURATION - self._enrage_return_timer
        progress = max(0.0, min(1.0, elapsed / max(1, self.ENRAGE_RETURN_DURATION)))
        eased = progress * progress * (3 - 2 * progress)
        origin = self._enrage_return_origin or (self.rect.x, self.rect.y)
        destination = self._enrage_return_target or self._clamped_arena_position(self.rect.x, self.rect.y)
        self.rect.x = origin[0] + (destination[0] - origin[0]) * eased
        self.rect.y = origin[1] + (destination[1] - origin[1]) * eased
        self._target_x = destination[0]
        self._target_y = destination[1]
        self.sync_hitbox()
        if target:
            self._face_target(target)
        self._update_muzzle_flash()
        self._enrage_return_timer -= 1
        if self._enrage_return_timer <= 0:
            self.rect.x, self.rect.y = destination
            self._enrage_return_origin = None
            self._enrage_return_target = None

    def _current_player_target(self, player=None, player_pos: Tuple[int, int] = None) -> Tuple[float, float] | None:
        if player is not None:
            rect = player.rect
            if hasattr(rect, "centerx") and hasattr(rect, "centery"):
                return (float(rect.centerx), float(rect.centery))
            if all(hasattr(rect, attr) for attr in ("x", "y", "width", "height")):
                return (float(rect.x + rect.width / 2), float(rect.y + rect.height / 2))
        if player_pos:
            return (float(player_pos[0]), float(player_pos[1]))
        return None

    def _enrage_path_radius(self, target: Tuple[float, float]) -> float:
        base_radius = max(self.rect.width, self.rect.height) * self.ENRAGE_PATH_RADIUS_SCALE
        max_radius = max(
            24.0,
            min(
                target[0] - self.rect.width / 2,
                get_screen_width() - target[0] - self.rect.width / 2,
                target[1] - self.MIN_Y - self.rect.height / 2,
                get_screen_height() - target[1] - self.rect.height / 2,
            ),
        )
        return min(base_radius, max_radius)

    def _enrage_path_center(self, target: Tuple[float, float], progress: float) -> Tuple[float, float]:
        progress = max(0.0, min(1.0, progress))
        radius = self._enrage_path_radius(target)
        if progress <= self.ENRAGE_SQUARE_PATH_RATIO:
            square_progress = progress / max(0.0001, self.ENRAGE_SQUARE_PATH_RATIO)
            return self._enrage_square_path_center(target, radius, square_progress)
        circle_progress = (progress - self.ENRAGE_SQUARE_PATH_RATIO) / max(0.0001, 1.0 - self.ENRAGE_SQUARE_PATH_RATIO)
        angle = math.pi / 2 + circle_progress * math.tau
        return (
            target[0] + math.cos(angle) * radius,
            target[1] + math.sin(angle) * radius,
        )

    def _enrage_square_path_center(
        self,
        target: Tuple[float, float],
        radius: float,
        progress: float,
    ) -> Tuple[float, float]:
        progress = max(0.0, min(1.0, progress))
        segment = min(3, int(progress * 4))
        local = progress * 4 - segment
        points = (
            (target[0], target[1] + radius),
            (target[0] + radius, target[1]),
            (target[0], target[1] - radius),
            (target[0] - radius, target[1]),
            (target[0], target[1] + radius),
        )
        start = points[segment]
        end = points[segment + 1]
        return (
            start[0] + (end[0] - start[0]) * local,
            start[1] + (end[1] - start[1]) * local,
        )

    def _record_enrage_trail(self) -> None:
        self._enrage_trail.append((self.rect.centerx, self.rect.centery))
        max_trail = max(self.ENRAGE_TRAIL_LENGTH, int(max(self.rect.width, self.rect.height) * 3 / 40))
        if len(self._enrage_trail) > max_trail:
            self._enrage_trail = self._enrage_trail[-max_trail:]

    def _clamped_enrage_position(self, x: float, y: float) -> Tuple[float, float]:
        return (
            max(0, min(x, get_screen_width() - self.rect.width)),
            max(self.MIN_Y, min(y, get_screen_height() - self.rect.height)),
        )

    def _update_enrage_snapshot_attacks(self, target: Tuple[float, float], progress: float) -> None:
        if not self._bullet_spawner or self._enrage_timer <= 1:
            return
        self._enrage_attack_timer -= 1
        if self._enrage_attack_timer > 0:
            return
        self._spawn_bullets(self._create_enrage_snapshot_attack(target, progress))
        self._enrage_attack_timer = self.ENRAGE_ATTACK_INTERVAL
        self._enrage_attack_index += 1

    def _create_enrage_snapshot_attack(self, target: Tuple[float, float], progress: float) -> List[Bullet]:
        bullets = []
        source = self._primary_boss_muzzle_position()
        bullets.extend(self._create_enrage_snapshot_lasers(source, target, progress))
        bullets.extend(self._create_enrage_snapshot_ring_bullets(target, progress))
        release_index = self._enrage_attack_index
        for bullet in bullets:
            bullet.held = True
            bullet.clear_immune = True
            bullet.enrage_release_delay = release_index * self.ENRAGE_RELEASE_INTERVAL
        return bullets

    def _create_enrage_snapshot_lasers(
        self,
        source: Tuple[float, float],
        target: Tuple[float, float],
        progress: float,
    ) -> List[Bullet]:
        aim = Vector2(target[0] - source[0], target[1] - source[1])
        if aim.length() <= 0:
            aim = Vector2(0, 1)
        aim = aim.normalize()
        side_axis = Vector2(-aim.y, aim.x)
        burst_axis = 1 if self._enrage_attack_index % 2 == 0 else -1
        bullet_data = BulletData(
            damage=get_game_constants().BOSS.AIM_BULLET_DAMAGE_BASE + self.phase * self.AIM_DAMAGE_INCREMENT,
            speed=self.ENRAGE_LASER_SPEED,
            owner="enemy",
            bullet_type="laser",
        )
        bullets = []
        spread = max(self.rect.width * 0.22, 34)
        for index in range(self.ENRAGE_SNAPSHOT_LASER_COUNT):
            offset = (index - (self.ENRAGE_SNAPSHOT_LASER_COUNT - 1) / 2) * spread
            phase_bias = math.sin(progress * math.tau * 4 + index) * 0.22 * burst_axis
            direction = Vector2(
                aim.x + side_axis.x * phase_bias,
                aim.y + side_axis.y * phase_bias,
            ).normalize()
            bullet_x = source[0] + side_axis.x * offset
            bullet_y = source[1] + side_axis.y * offset
            bullet = Bullet(bullet_x, bullet_y, bullet_data)
            bullet.velocity = Vector2(0, 0)
            bullet.release_direction = direction
            bullet.enrage_release_speed = self.ENRAGE_RELEASE_LASER_SPEED
            bullets.append(bullet)
            self._trigger_muzzle_flash((bullet_x, bullet_y))
        return bullets

    def _create_enrage_snapshot_ring_bullets(self, target: Tuple[float, float], progress: float) -> List[Bullet]:
        cx, cy = target
        bullet_data = BulletData(
            damage=get_game_constants().BOSS.WAVE_BULLET_DAMAGE,
            speed=self.ENRAGE_BULLET_SPEED,
            owner="enemy",
            bullet_type="single",
        )
        bullets = []
        muzzles = self._boss_muzzle_positions()
        radius = max(self.rect.width, self.rect.height) * (1.65 + 0.25 * math.sin(progress * math.tau * 5))
        base_angle = progress * math.tau * 2.8 + self._enrage_attack_index * 0.47
        gap_index = self._enrage_attack_index % self.ENRAGE_SNAPSHOT_RING_COUNT
        for index in range(self.ENRAGE_SNAPSHOT_RING_COUNT):
            if index == gap_index:
                continue
            angle = base_angle + math.tau * index / self.ENRAGE_SNAPSHOT_RING_COUNT
            bullet_x = cx + math.cos(angle) * radius
            bullet_y = cy + math.sin(angle) * radius * 0.78
            direction = Vector2(cx - bullet_x, cy - bullet_y).normalize()
            if direction.length() <= 0:
                direction = Vector2(0, 1)
            bullet = Bullet(bullet_x, bullet_y, bullet_data)
            bullet.velocity = Vector2(0, 0)
            bullet.release_direction = direction
            bullet.enrage_release_speed = self.ENRAGE_RELEASE_BULLET_SPEED
            bullets.append(bullet)
            self._trigger_muzzle_flash(muzzles[(len(bullets) - 1) % len(muzzles)])
        return bullets

    def _release_enrage_bullets(self, target: Tuple[float, float]) -> None:
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
        self._enrage_bullets_released = True
        self._enrage_health_lock_active = False
        self._enrage_timer = 0
        self._enrage_release_hold_timer = self.ENRAGE_RELEASE_HOLD_DURATION
        self._enrage_trail.clear()
        self._enrage_trail_ghost = None
        self._enrage_trail_ghost_key = None

    def _move_behind_player_after_enrage(self, target: Tuple[float, float]) -> None:
        behind_center_x, behind_center_y = self._enrage_path_center(target, 1.0)
        self._enrage_release_anchor = (behind_center_x, behind_center_y)
        self.rect.x = behind_center_x - self.rect.width / 2
        self.rect.y = behind_center_y - self.rect.height / 2
        self._target_x = self.rect.x
        self._target_y = self.rect.y
        self.sync_hitbox()
        self._face_target(target)

    def _face_target(self, target: Tuple[float, float]) -> None:
        dx = target[0] - self.rect.centerx
        dy = target[1] - self.rect.centery
        if dx == 0 and dy == 0:
            return
        self._facing_angle = math.degrees(math.atan2(dy, dx))

    def _facing_vector(self) -> Vector2:
        radians = math.radians(self._facing_angle)
        return Vector2(math.cos(radians), math.sin(radians))

    def _boss_muzzle_positions(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        forward = self._facing_vector().normalize()
        if forward.length() <= 0:
            forward = Vector2(0, 1)
        side_axis = Vector2(-forward.y, forward.x)
        muzzle_center_x = self.rect.centerx + forward.x * self.rect.height * self.ENRAGE_MUZZLE_FORWARD_SCALE
        muzzle_center_y = self.rect.centery + forward.y * self.rect.height * self.ENRAGE_MUZZLE_FORWARD_SCALE
        side_offset = self.rect.width * self.ENRAGE_MUZZLE_SIDE_SCALE
        return (
            (muzzle_center_x + side_axis.x * side_offset, muzzle_center_y + side_axis.y * side_offset),
            (muzzle_center_x - side_axis.x * side_offset, muzzle_center_y - side_axis.y * side_offset),
        )

    def _primary_boss_muzzle_position(self) -> Tuple[float, float]:
        muzzles = self._boss_muzzle_positions()
        return (
            (muzzles[0][0] + muzzles[1][0]) / 2,
            (muzzles[0][1] + muzzles[1][1]) / 2,
        )

    def _trigger_muzzle_flash(self, position: Tuple[float, float] | None = None) -> None:
        self._muzzle_flash_timer = self.ENRAGE_MUZZLE_FLASH_DURATION
        if position is None:
            self._muzzle_flash_positions = list(self._boss_muzzle_positions())
            return
        self._muzzle_flash_positions.append(position)

    def _update_muzzle_flash(self) -> None:
        if self._muzzle_flash_timer <= 0:
            return
        self._muzzle_flash_timer -= 1
        if self._muzzle_flash_timer <= 0:
            self._muzzle_flash_positions = []

    def _enrage_spawned_bullets(self) -> List[Bullet]:
        if hasattr(self._bullet_spawner, "get_bullets"):
            return self._bullet_spawner.get_bullets()
        if hasattr(self._bullet_spawner, "bullets"):
            return self._bullet_spawner.bullets
        if hasattr(self._bullet_spawner, "bullet_list"):
            return self._bullet_spawner.bullet_list
        return []

    def _is_aim_dashing(self) -> bool:
        return self._aim_dash_duration > 0

    def _start_aim_dash(self, player_pos: Tuple[float, float]) -> None:
        if not player_pos:
            return

        self._aim_fire_target = (float(player_pos[0]), float(player_pos[1]))
        dx = player_pos[0] - self.rect.centerx
        dy = player_pos[1] - self.rect.centery
        distance = math.hypot(dx, dy)
        if distance <= 0:
            self._finish_aim_dash()
            return

        dash_distance = self.AIM_DASH_DISTANCE + self.phase * self.AIM_DASH_PHASE_BONUS
        dash_distance = min(dash_distance, distance * self.AIM_DASH_MAX_DISTANCE_RATIO)
        target_center_x = self.rect.centerx + dx / distance * dash_distance
        target_center_y = self.rect.centery + dy / distance * dash_distance
        target_x = target_center_x - self.rect.width / 2
        target_y = target_center_y - self.rect.height / 2
        target_x, target_y = self._clamped_arena_position(target_x, target_y)

        if abs(target_x - self.rect.x) < 1 and abs(target_y - self.rect.y) < 1:
            self._finish_aim_dash()
            return

        self._aim_dash_elapsed = 0
        self._aim_dash_duration = self.AIM_DASH_DURATION
        self._aim_dash_start_x = self.rect.x
        self._aim_dash_start_y = self.rect.y
        self._aim_dash_target_x = target_x
        self._aim_dash_target_y = target_y
        self._target_x = target_x
        self._target_y = target_y

    def _update_aim_dash(self) -> None:
        self._aim_dash_elapsed += 1
        progress = min(1.0, self._aim_dash_elapsed / self._aim_dash_duration)
        self.rect.x = self._aim_dash_start_x + (self._aim_dash_target_x - self._aim_dash_start_x) * progress
        self.rect.y = self._aim_dash_start_y + (self._aim_dash_target_y - self._aim_dash_start_y) * progress
        self._clamp_to_arena()

        if progress >= 1.0:
            self._finish_aim_dash()

    def _finish_aim_dash(self) -> None:
        self._aim_dash_duration = 0
        self._aim_dash_elapsed = 0
        bullets = self._aim_attack(self._aim_fire_target)
        self._aim_fire_target = None
        self._spawn_bullets(bullets)
        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _select_attack_direction_for_target(self, player_pos: Tuple[float, float]) -> None:
        dx = player_pos[0] - self.rect.centerx
        dy = player_pos[1] - self.rect.centery
        if abs(dx) > abs(dy) * 1.2:
            self.attack_direction = 'right' if dx > 0 else 'left'
        else:
            self.attack_direction = 'down' if dy >= 0 else 'up'

    def _spread_attack(self) -> List[Bullet]:
        B = get_game_constants().BOSS
        bullets = []

        direction_offsets = self._get_direction_offsets()

        base_angle, y_pos = direction_offsets.get(self.attack_direction, (-90, self.rect.bottom))
        center_x = self.rect.centerx
        bullet_count = B.SPREAD_BULLET_COUNT_BASE + self.phase

        for i in range(bullet_count):
            if self.attack_direction == 'left' or self.attack_direction == 'right':
                angle = base_angle + (B.SIDE_ANGLE_RANGE / (bullet_count - 1)) * i - B.SIDE_ANGLE_OFFSET
            else:
                angle = base_angle + (B.SPREAD_ANGLE_RANGE / (bullet_count - 1)) * i

            rad = math.radians(angle)
            speed = B.SPREAD_SPEED
            vx = math.cos(rad) * speed
            vy = math.sin(rad) * speed

            bullet_data = BulletData(
                damage=B.BULLET_DAMAGE_BASE + self.phase * self.SPREAD_DAMAGE_INCREMENT,
                speed=B.SPREAD_SPEED,
                owner="enemy",
                bullet_type="spread"
            )
            bullet = Bullet(center_x, y_pos, bullet_data)
            bullet.velocity = Vector2(vx, vy)
            bullets.append(bullet)

        return bullets

    def _aim_attack(self, player_pos: Tuple[float, float] = None) -> List[Bullet]:
        bullets = []

        if player_pos:
            self._select_attack_direction_for_target(player_pos)

        direction_sources = self._get_direction_sources()

        source_x, source_y = direction_sources.get(self.attack_direction, (self.rect.centerx, self.rect.bottom))

        if player_pos:
            aim_dx = player_pos[0] - source_x
            aim_dy = player_pos[1] - source_y
        else:
            target_offsets = self._get_target_offsets()
            aim_dx, aim_dy = target_offsets.get(self.attack_direction, (0, get_game_constants().BOSS.ATTACK_DISTANCE))

        aim_vector = Vector2(aim_dx, aim_dy)
        if aim_vector.length() <= 0:
            aim_vector = Vector2(0, get_game_constants().BOSS.ATTACK_DISTANCE)
        aim_vector = aim_vector.normalize()
        spread_axis = Vector2(-aim_vector.y, aim_vector.x)

        bullet_data = BulletData(
            damage=get_game_constants().BOSS.AIM_BULLET_DAMAGE_BASE + self.phase * self.AIM_DAMAGE_INCREMENT,
            speed=get_game_constants().BOSS.AIM_SPEED,
            owner="enemy",
            bullet_type="laser"
        )

        for i in range(self.AIM_BULLET_COUNT):
            offset = (i - (self.AIM_BULLET_COUNT - 1) / 2) * get_game_constants().BOSS.BULLET_OFFSET_X
            bullet_x = source_x + spread_axis.x * offset
            bullet_y = source_y + spread_axis.y * offset
            bullet = Bullet(bullet_x, bullet_y, bullet_data)
            if player_pos:
                velocity = Vector2(player_pos[0] - bullet_x, player_pos[1] - bullet_y)
                velocity = aim_vector if velocity.length() <= 0 else velocity.normalize()
            else:
                velocity = aim_vector
            bullet.velocity = velocity * get_game_constants().BOSS.AIM_SPEED
            bullets.append(bullet)

        return bullets

    def _wave_attack(self) -> List[Bullet]:
        bullets = []

        direction_sources = self._get_direction_sources()

        center_x, center_y = direction_sources.get(self.attack_direction, (self.rect.centerx, self.rect.centery))

        for i in range(self.WAVE_BULLET_COUNT):
            if self.attack_direction == 'left':
                angle = 180 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            elif self.attack_direction == 'right':
                angle = 0 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            elif self.attack_direction == 'up':
                angle = 90 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            else:
                angle = -90 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i

            rad = math.radians(angle)
            speed = get_game_constants().BOSS.WAVE_SPEED

            bullet_data = BulletData(
                damage=get_game_constants().BOSS.WAVE_BULLET_DAMAGE,
                speed=speed,
                owner="enemy",
                bullet_type="single"
            )
            bullet = Bullet(center_x, center_y, bullet_data)
            bullet.velocity = Vector2(math.cos(rad) * speed, math.sin(rad) * speed)
            bullets.append(bullet)

        return bullets

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def render(self, surface: pygame.Surface) -> None:
        if self._sprite:
            surface.blit(self._sprite, self.get_rect())

    def take_damage(self, damage: int) -> int:

        """Apply damage to the boss.

        Reduces health and returns the score value if the boss is killed.

        Args:
        damage: Amount of damage to apply.

        Returns:
        Score value if boss is killed, 0 otherwise.
        """
        if damage is None or damage < 0:
            return 0
        if not self._enraged and self.max_health > 0:
            projected_health = self.health - damage
            if projected_health <= self._enrage_health_lock_value:
                self.health = self._enrage_health_lock_value
                return 0
        if self._enrage_health_lock_active:
            self.health = max(self.health, self._enrage_health_lock_value)
            return 0
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return self.data.score
        return 0

    def is_enraged(self) -> bool:
        return self._enraged

    def is_enrage_active(self) -> bool:
        return self._enrage_timer > 0

    def should_lock_player_movement(self) -> bool:
        return self._enrage_timer > 0 and not self._enrage_bullets_released

    def enrage_slow_factor(self) -> float:
        return self.ENRAGE_SLOW_FACTOR if self._enrage_timer > 0 else 1.0

    def enrage_visual_intensity(self) -> float:
        if self._enrage_timer > 0:
            progress = self._enrage_progress()
            eased = progress * progress * (3 - 2 * progress)
            transition_ramp = 1.0
            if self._enrage_transition_timer > 0:
                elapsed = self.ENRAGE_TRANSITION_DURATION - self._enrage_transition_timer
                transition = max(0.0, min(1.0, elapsed / max(1, self.ENRAGE_TRANSITION_DURATION)))
                transition_ramp = transition * transition * (3 - 2 * transition)
            return max(0.0, min(0.88, (0.18 + 0.70 * eased) * transition_ramp))
        if self._enrage_release_hold_timer > 0:
            hold = self._enrage_release_hold_timer / max(1, self.ENRAGE_RELEASE_HOLD_DURATION)
            return max(0.0, min(0.74, 0.52 + 0.22 * hold))
        if self._enrage_return_timer > 0:
            fade = self._enrage_return_timer / max(1, self.ENRAGE_RETURN_DURATION)
            eased = fade * fade * (3 - 2 * fade)
            return max(0.0, min(0.52, 0.52 * eased))
        return 0.0

    def is_enrage_transitioning(self) -> bool:
        return self._enrage_transition_timer > 0

    def is_entering(self) -> bool:
        return self.entering

    def is_escaped(self) -> bool:
        return self.escaped

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)
