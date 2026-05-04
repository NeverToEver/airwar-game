"""Enemy and Boss entities with movement patterns and attack behaviors."""
import pygame
from airwar.utils.fonts import get_cjk_font
import random
import math
from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from airwar.config.design_tokens import Colors
from .base import Entity, EnemyData, Vector2
from .bullet import Bullet, BulletData
from .interfaces import IBulletSpawner
from ..utils.sprites import draw_enemy_ship, draw_boss_ship
from ..config import (
    ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING, ENEMY_VISUAL_SCALE, ENEMY_COLLISION_SCALE,
    get_screen_width, get_screen_height,
    BOSS_AIM_BULLET_DAMAGE_BASE, BOSS_AIM_SPEED, BOSS_ATTACK_DISTANCE, BOSS_BULLET_OFFSET_X,
    BOSS_WAVE_BULLET_DAMAGE, BOSS_WAVE_SPEED, BOSS_WAVE_ANGLE_INTERVAL,
)

from ..config.constants_access import get_game_constants
from .movement_strategies import get_movement_strategy

# Try to import Rust movement function
try:
    from airwar.core_bindings import update_movement as rust_update_movement, RUST_AVAILABLE
except ImportError:
    rust_update_movement = None
    RUST_AVAILABLE = False

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
        movement (Rust-accelerated or Python fallback), and firing.
        """
        if not self.active:
            return

        # Handle entry animation
        if self._state == 'entering':
            # Check if enemy somehow got placed off screen during entry
            if self.rect.y > get_screen_height():
                self.active = False
                return

            self._entry_progress += self.ENTRY_SPEED
            if self._entry_progress >= 1.0:
                self._entry_progress = 1.0
                self._state = 'active'
                self.rect.x = self._entry_target_x
                self.rect.y = self._entry_target_y
                self.sync_rects()
                # Record position for small-range movement
                self.active_position_x = self.rect.x
                self.active_position_y = self.rect.y
                self.lifetime = 0
            else:
                # Eased entry: decelerate into target position
                t = self._entry_progress
                t_eased = 1.0 - (1.0 - t) * (1.0 - t)  # ease-out quad
                self.rect.x = self._entry_start_x + (self._entry_target_x - self._entry_start_x) * t_eased
                self.rect.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * t_eased
                self.sync_rects()
            return

        # Handle exit animation
        if self._state == 'exiting':
            self._exit_progress += self.EXIT_SPEED
            if self._exit_progress >= 1.0:
                self.active = False
                return
            t = self._exit_progress
            # Smooth exit with curve
            self.rect.x = self._exit_start_x + (self._exit_end_x - self._exit_start_x) * t + math.sin(t * math.pi) * 30
            self.rect.y = self._exit_start_y + (self._exit_end_y - self._exit_start_y) * t
            self.sync_rects()
            return

        # Active state: check lifetime (15 seconds max)
        self.lifetime += 1
        if self.lifetime >= self._max_lifetime:
            self._state = 'exiting'
            self._exit_start_x = self.rect.x
            self._exit_start_y = self.rect.y
            self._exit_end_x = self.rect.x + random.choice(self.EXIT_X_OFFSETS)
            self._exit_end_y = self.EXIT_ACTIVE_END_Y
            return

        # Use cached movement ranges
        move_range_x = self._move_range_x
        move_range_y = self._move_range_y

        # Try Rust movement first if available
        # Exclude zigzag: Rust uses active_x as base instead of current x,
        # which produces different (non-accumulating) movement behavior
        if rust_update_movement is not None and self.move_type in MOVEMENT_TYPE_MAP and self.move_type != "zigzag":
            # Use batch result if already computed this frame (see GameLoopManager)
            br = getattr(self, '_batch_result', None)
            if br is not None:
                self.rect.x, self.rect.y, new_timer = br
                del self._batch_result
                if self.move_type == "hover":
                    new_timer *= 0.08
                setattr(self, self._timer_attr, new_timer)
                self.sync_rects()
                # Fall through to skip rest of movement block
            else:
                timer = getattr(self, self._timer_attr, 0.0)
                if self.move_type == "hover":
                    timer /= 0.08

                params = self._rust_params
                new_x, new_y, new_timer = rust_update_movement(
                    self._rust_move_type_code, timer,
                    self.active_position_x, self.active_position_y,
                    move_range_x, move_range_y,
                    params['offset'], params['amplitude'], params['frequency'], params['speed'], params['direction'],
                    params['zigzag_interval'], params['spiral_radius'],
                    self.rect.x, self.rect.y,
                    params['noise_scale_x'], params['noise_scale_y'],
                    params['noise_amplitude_x'], params['noise_amplitude_y'],
                    params['noise_seed'],
                )

                self.rect.x = new_x
                self.rect.y = new_y

                if self.move_type == "hover":
                    new_timer *= 0.08
                setattr(self, self._timer_attr, new_timer)

                self.sync_rects()
        else:
            # Fallback to Python movement via strategy pattern
            self._movement_strategy.update(self)

        # Blend from entry target to full pattern amplitude during transition
        if self._transition_timer < self._transition_duration:
            self._transition_timer += 1
            t = self._transition_timer / self._transition_duration
            blend = t * t  # ease-in quad
            self.rect.x = self.active_position_x + (self.rect.x - self.active_position_x) * blend
            self.rect.y = self.active_position_y + (self.rect.y - self.active_position_y) * blend
            self.sync_rects()

        if self.rect.y > get_screen_height():
            self.active = False

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
        if not self._sprite:
            health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
            draw_enemy_ship(surface, self.rect.centerx, self.rect.centery,
                          self.rect.width, self.rect.height, health_ratio)
        else:
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
            timer /= 0.08
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
        if enemy_type == "sine":
            self.move_type = "sine"
            self.move_offset = random.uniform(0, math.pi * 2)
            self.move_amplitude = random.uniform(*self.SINE_AMP_RANGE)
            self.move_frequency = random.uniform(*self.SINE_FREQ_RANGE)
            self.start_x = self.rect.x
            self.move_timer = 0

        elif enemy_type == "zigzag":
            self.move_type = "zigzag"
            self.direction = random.choice([-1, 1])
            self.zigzag_timer = 0
            self.zigzag_interval = random.randint(*self.ZIGZAG_INTERVAL_RANGE)
            self.zigzag_speed = random.uniform(*self.ZIGZAG_SPEED_RANGE)

        elif enemy_type == "dive":
            self.move_type = "dive"
            self.target_x = self.start_x = self.rect.x
            self.dive_timer = 0
            self.dive_delay = random.randint(*self.DIVE_DELAY_RANGE)
            self.diving = False

        elif enemy_type == "hover":
            self.move_type = "hover"
            self.hover_timer = 0
            self.hover_speed = random.uniform(*self.HOVER_SPEED_RANGE)
            self.hover_amplitude = random.uniform(*self.HOVER_AMP_RANGE)
            self.start_x = self.rect.x

        elif enemy_type == "spiral":
            self.move_type = "spiral"
            self.spiral_timer = 0
            self.spiral_speed = random.uniform(*self.SPIRAL_SPEED_RANGE)
            self.spiral_radius = random.uniform(*self.SPIRAL_RADIUS_RANGE)
            self.spiral_frequency = random.uniform(*self.SPIRAL_FREQ_RANGE)
            self.start_x = self.rect.x

        elif enemy_type == "noise":
            self.move_type = "noise"
            self.noise_timer = 0.0
            self.noise_speed = random.uniform(*self.NOISE_SPEED_RANGE)  # slower for smooth movement
            self.noise_scale_x = random.uniform(*self.NOISE_SCALE_X_RANGE)
            self.noise_scale_y = random.uniform(*self.NOISE_SCALE_Y_RANGE)
            self.noise_amplitude_x = random.uniform(*self.NOISE_AMP_X_RANGE)
            self.noise_amplitude_y = random.uniform(*self.NOISE_AMP_Y_RANGE)
            self.noise_seed = random.randint(0, 9999)

        elif enemy_type == "aggressive":
            self.move_type = "aggressive"
            self.agg_timer = 0.0
            self.agg_speed = random.uniform(*self.AGGR_SPEED_RANGE)  # moderate speed for smoothness
            self.agg_scale_x = random.uniform(*self.AGGR_SCALE_X_RANGE)
            self.agg_scale_y = random.uniform(*self.AGGR_SCALE_Y_RANGE)
            self.agg_amplitude_x = random.uniform(*self.AGGR_AMP_X_RANGE)
            self.agg_amplitude_y = random.uniform(*self.AGGR_AMP_Y_RANGE)
            self.agg_seed = random.randint(0, 9999)

        else:
            self.move_type = "straight"

        self._movement_strategy = get_movement_strategy(self.move_type)

        # Pre-compute movement params for Rust call to avoid 15+ getattr() per frame
        self._rust_move_type_code = MOVEMENT_TYPE_MAP.get(self.move_type, 0)
        self._rust_params = {
            'offset': getattr(self, 'move_offset', 0.0),
            'amplitude': getattr(self, 'move_amplitude', 2.0),
            'frequency': getattr(self, 'spiral_frequency', 0.05) if self.move_type == "spiral" else getattr(self, 'move_frequency', 0.05),
            'speed': getattr(self, 'zigzag_speed', 2.0) if self.move_type == "zigzag" else
                     getattr(self, 'noise_speed', 0.03) if self.move_type == "noise" else
                     getattr(self, 'agg_speed', 0.035) if self.move_type == "aggressive" else
                     getattr(self, 'spiral_speed', 2.0),
            'direction': getattr(self, 'direction', 1.0),
            'zigzag_interval': getattr(self, 'zigzag_interval', 45.0),
            'spiral_radius': getattr(self, 'spiral_radius', 40.0),
            'noise_scale_x': getattr(self, 'agg_scale_x', 0.04) if self.move_type == "aggressive" else getattr(self, 'noise_scale_x', 0.04),
            'noise_scale_y': getattr(self, 'agg_scale_y', 0.02) if self.move_type == "aggressive" else getattr(self, 'noise_scale_y', 0.02),
            'noise_amplitude_x': getattr(self, 'agg_amplitude_x', 0.6) if self.move_type == "aggressive" else getattr(self, 'noise_amplitude_x', 0.7),
            'noise_amplitude_y': getattr(self, 'agg_amplitude_y', 0.5) if self.move_type == "aggressive" else getattr(self, 'noise_amplitude_y', 0.4),
            'noise_seed': getattr(self, 'agg_seed', 0) if self.move_type == "aggressive" else getattr(self, 'noise_seed', 0),
        }

        # Pre-compute timer attribute for fast read/write in hot path
        if self.move_type == "hover":
            self._timer_attr = "hover_timer"
        elif self.move_type in ("zigzag", "dive", "spiral", "noise", "aggressive"):
            self._timer_attr = f"{self.move_type}_timer"
        else:
            self._timer_attr = "move_timer"

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
        self._pending_spawns: list = []
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
            self._pending_spawns = []

        # Start new wave if no wave active — prepare spawn data
        if not self._wave_active:
            self._wave_active = True
            self._wave_enemies_spawned = 0
            self._pending_spawns = self._prepare_wave_data(player_pos)

        # Gradual spawn: pop up to ENEMIES_PER_FRAME per frame
        for _ in range(self.ENEMIES_PER_FRAME):
            if not self._pending_spawns:
                break
            spawn_data = self._pending_spawns.pop(0)
            self._spawn_one(enemies, spawn_data)
            self._wave_enemies_spawned += 1

    def _prepare_wave_data(self, player_pos: tuple = None) -> list:
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
        return self._limit_spread_bullet_types(spawn_data)

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

    def render(self, surface: pygame.Surface) -> None:
        from ..utils.sprites import draw_elite_enemy_ship
        health_ratio = self.health / self.max_health if self.max_health > 0 else 0.0
        draw_elite_enemy_ship(
            surface,
            self.rect.centerx, self.rect.centery,
            self.rect.width * self.VISUAL_SCALE,
            self.rect.height * self.VISUAL_SCALE,
            health_ratio
        )

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
    ENTRY_FONT_SIZE = 36
    ESCAPE_FONT_SIZE = 28
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
    ENRAGE_DURATION = 150
    ENRAGE_SLOW_FACTOR = 0.22
    ENRAGE_BULLET_SPEED = 2.4
    ENRAGE_LASER_SPEED = 2.0
    ENRAGE_POLYGON_GAP = 96
    ENRAGE_RING_COUNT = 36
    ENRAGE_RING_RADIUS_STEP = 52
    ENRAGE_TRAIL_LENGTH = 18
    ENRAGE_TRAIL_RENDER_MAX = 9

    _warning_font = None
    _escape_font = None

    @classmethod
    def _get_warning_font(cls):
        if cls._warning_font is None:
            cls._warning_font = get_cjk_font(cls.ENTRY_FONT_SIZE)
        return cls._warning_font

    @classmethod
    def _get_escape_font(cls):
        if cls._escape_font is None:
            cls._escape_font = get_cjk_font(cls.ESCAPE_FONT_SIZE)
        return cls._escape_font

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
        if self._enrage_timer > 0:
            self._update_enrage(player_pos, kwargs.get("player"))
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
        self._enrage_snapshot_target = target
        self._enrage_trail.clear()
        self._spawn_bullets(self._create_enrage_bullet_field(target))

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

        progress = 1.0 - self._enrage_timer / self.ENRAGE_DURATION
        angle = progress * math.tau * 2.0
        radius = max(self.rect.width, self.rect.height) * 1.35
        target_center_x = target[0] + math.cos(angle) * radius
        target_center_y = target[1] + math.sin(angle) * radius * 0.72
        self.rect.x, self.rect.y = self._clamped_arena_position(
            target_center_x - self.rect.width / 2,
            target_center_y - self.rect.height / 2,
        )

        self._enrage_timer -= 1
        if self._enrage_timer <= 0:
            self._release_enrage_bullets(target)

    def _record_enrage_trail(self) -> None:
        self._enrage_trail.append((self.rect.centerx, self.rect.centery))
        max_trail = max(self.ENRAGE_TRAIL_LENGTH, int(max(self.rect.width, self.rect.height) * 3 / 40))
        if len(self._enrage_trail) > max_trail:
            self._enrage_trail = self._enrage_trail[-max_trail:]

    def _create_enrage_bullet_field(self, target: Tuple[float, float]) -> List[Bullet]:
        bullets = []
        bullets.extend(self._create_enrage_polygon_lasers(target))
        bullets.extend(self._create_enrage_ring_bullets(target))
        return bullets

    def _create_enrage_polygon_lasers(self, target: Tuple[float, float]) -> List[Bullet]:
        cx, cy = target
        radius_x = max(230, get_screen_width() * 0.25)
        radius_y = max(170, get_screen_height() * 0.20)
        corners = [
            (cx, cy - radius_y),
            (cx + radius_x, cy),
            (cx, cy + radius_y),
            (cx - radius_x, cy),
        ]
        bullet_data = BulletData(
            damage=BOSS_AIM_BULLET_DAMAGE_BASE + self.phase * self.AIM_DAMAGE_INCREMENT,
            speed=self.ENRAGE_LASER_SPEED,
            owner="enemy",
            bullet_type="laser",
        )
        bullets = []
        for start, end in zip(corners, corners[1:] + corners[:1], strict=False):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.hypot(dx, dy)
            if length <= 0:
                continue
            steps = max(1, int(length // self.ENRAGE_POLYGON_GAP))
            direction = Vector2(cx - start[0], cy - start[1]).normalize()
            for index in range(steps):
                if index % 3 == 1:
                    continue
                t = (index + 0.5) / steps
                bullet = Bullet(start[0] + dx * t, start[1] + dy * t, bullet_data)
                bullet.velocity = Vector2(0, 0)
                bullet.held = True
                bullet.clear_immune = True
                bullet.enrage_target = target
                bullet.enrage_speed = self.ENRAGE_LASER_SPEED
                bullet.release_direction = direction
                bullets.append(bullet)
        return bullets

    def _create_enrage_ring_bullets(self, target: Tuple[float, float]) -> List[Bullet]:
        cx, cy = target
        bullet_data = BulletData(
            damage=BOSS_WAVE_BULLET_DAMAGE,
            speed=self.ENRAGE_BULLET_SPEED,
            owner="enemy",
            bullet_type="single",
        )
        bullets = []
        for ring in (1, 2):
            radius = 130 + ring * self.ENRAGE_RING_RADIUS_STEP
            for index in range(self.ENRAGE_RING_COUNT):
                if index % 4 == 0:
                    continue
                angle = math.tau * index / self.ENRAGE_RING_COUNT + ring * 0.18
                bullet = Bullet(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius, bullet_data)
                bullet.velocity = Vector2(0, 0)
                bullet.held = True
                bullet.clear_immune = True
                bullet.enrage_target = target
                bullet.enrage_speed = self.ENRAGE_BULLET_SPEED
                bullet.release_direction = Vector2(cx - bullet.rect.x, cy - bullet.rect.y).normalize()
                bullets.append(bullet)
        return bullets

    def _release_enrage_bullets(self, target: Tuple[float, float]) -> None:
        if self._enrage_bullets_released or not self._bullet_spawner:
            self._enrage_timer = 0
            return
        for bullet in self._enrage_spawned_bullets():
            if not getattr(bullet, "clear_immune", False) or not getattr(bullet, "held", False):
                continue
            direction = getattr(bullet, "release_direction", None)
            if direction is None or direction.length() <= 0:
                direction = Vector2(target[0] - bullet.rect.x, target[1] - bullet.rect.y).normalize()
            if direction.length() <= 0:
                direction = Vector2(0, -1)
            speed = min(getattr(bullet, "enrage_speed", self.ENRAGE_BULLET_SPEED), self.ENRAGE_BULLET_SPEED) * 0.98
            bullet.velocity = direction * speed
            bullet.held = False
        self._enrage_bullets_released = True
        self._enrage_timer = 0

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
            aim_dx, aim_dy = target_offsets.get(self.attack_direction, (0, BOSS_ATTACK_DISTANCE))

        aim_vector = Vector2(aim_dx, aim_dy)
        if aim_vector.length() <= 0:
            aim_vector = Vector2(0, BOSS_ATTACK_DISTANCE)
        aim_vector = aim_vector.normalize()
        spread_axis = Vector2(-aim_vector.y, aim_vector.x)

        bullet_data = BulletData(
            damage=BOSS_AIM_BULLET_DAMAGE_BASE + self.phase * self.AIM_DAMAGE_INCREMENT,
            speed=BOSS_AIM_SPEED,
            owner="enemy",
            bullet_type="laser"
        )

        for i in range(self.AIM_BULLET_COUNT):
            offset = (i - (self.AIM_BULLET_COUNT - 1) / 2) * BOSS_BULLET_OFFSET_X
            bullet_x = source_x + spread_axis.x * offset
            bullet_y = source_y + spread_axis.y * offset
            bullet = Bullet(bullet_x, bullet_y, bullet_data)
            if player_pos:
                velocity = Vector2(player_pos[0] - bullet_x, player_pos[1] - bullet_y)
                velocity = aim_vector if velocity.length() <= 0 else velocity.normalize()
            else:
                velocity = aim_vector
            bullet.velocity = velocity * BOSS_AIM_SPEED
            bullets.append(bullet)

        return bullets

    def _wave_attack(self) -> List[Bullet]:
        bullets = []

        direction_sources = self._get_direction_sources()

        center_x, center_y = direction_sources.get(self.attack_direction, (self.rect.centerx, self.rect.centery))

        for i in range(self.WAVE_BULLET_COUNT):
            if self.attack_direction == 'left':
                angle = 180 + BOSS_WAVE_ANGLE_INTERVAL * i
            elif self.attack_direction == 'right':
                angle = 0 + BOSS_WAVE_ANGLE_INTERVAL * i
            elif self.attack_direction == 'up':
                angle = 90 + BOSS_WAVE_ANGLE_INTERVAL * i
            else:
                angle = -90 + BOSS_WAVE_ANGLE_INTERVAL * i

            rad = math.radians(angle)
            speed = BOSS_WAVE_SPEED

            bullet_data = BulletData(
                damage=BOSS_WAVE_BULLET_DAMAGE,
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

        """Render the boss ship with health-based coloring and warning text.

        Displays entry warning during entrance animation and escape
        warning when the boss is about to flee.

        Args:
        surface: Pygame surface to render onto.
        """
        health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
        self._render_enrage_trail(surface)
        draw_boss_ship(surface, self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height, health_ratio)

        if self.entering:
            warning_y = 20
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.3 + 0.7
            warning_surf = self._get_warning_font().render("! 警告 !", True, Colors.ACCENT_DANGER)
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

        if self._enrage_timer > 0:
            warning_y = 86
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.025)) * 0.35 + 0.65
            warning_surf = self._get_escape_font().render("狂暴 EMP", True, (255, 112, 42))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

        if self._show_escape_warning and not self.entering:
            warning_y = 50
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.02)) * 0.3 + 0.7
            warning_surf = self._get_escape_font().render("逃跑中...", True, (255, 200, 50))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

    def _render_enrage_trail(self, surface: pygame.Surface) -> None:
        if not self._enrage_trail:
            return
        trail = self._sample_enrage_trail_for_render()
        trail_len = len(trail)
        health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
        ghost = self._get_enrage_trail_ghost(health_ratio)
        for index, center in enumerate(trail):
            alpha = int(32 + 100 * (index + 1) / trail_len)
            ghost.set_alpha(alpha)
            surface.blit(ghost, ghost.get_rect(center=center))
        ghost.set_alpha(255)

    def _sample_enrage_trail_for_render(self) -> List[Tuple[float, float]]:
        trail_len = len(self._enrage_trail)
        if trail_len <= self.ENRAGE_TRAIL_RENDER_MAX:
            return self._enrage_trail
        max_points = self.ENRAGE_TRAIL_RENDER_MAX
        step = (trail_len - 1) / (max_points - 1)
        return [self._enrage_trail[round(index * step)] for index in range(max_points)]

    def _get_enrage_trail_ghost(self, health_ratio: float) -> pygame.Surface:
        health_bucket = int(health_ratio * 10)
        cache_key = (int(self.rect.width), int(self.rect.height), health_bucket)
        if self._enrage_trail_ghost_key != cache_key:
            ghost = pygame.Surface((int(self.rect.width * 3), int(self.rect.height * 3)), pygame.SRCALPHA)
            draw_boss_ship(
                ghost,
                ghost.get_width() / 2,
                ghost.get_height() / 2,
                self.rect.width,
                self.rect.height,
                health_ratio,
            )
            ghost.fill((255, 74, 22, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._enrage_trail_ghost = ghost
            self._enrage_trail_ghost_key = cache_key
        return self._enrage_trail_ghost

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
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return self.data.score
        return 0

    def is_enraged(self) -> bool:
        return self._enraged

    def is_enrage_active(self) -> bool:
        return self._enrage_timer > 0

    def enrage_slow_factor(self) -> float:
        return self.ENRAGE_SLOW_FACTOR if self._enrage_timer > 0 else 1.0

    def enrage_visual_intensity(self) -> float:
        if self._enrage_timer <= 0:
            return 0.0
        progress = self._enrage_timer / self.ENRAGE_DURATION
        return max(0.0, min(1.0, progress))

    def is_entering(self) -> bool:
        return self.entering

    def is_escaped(self) -> bool:
        return self.escaped

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)
