"""Enemy and Boss entities with movement patterns and attack behaviors."""
import pygame
from airwar.utils.fonts import get_cjk_font
import random
import math
from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
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
    from airwar.scenes.game_scene import GameScene


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
        self._sync_rects()
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
        self._lifetime = 0
        consts = get_game_constants()
        self._max_lifetime = consts.ENEMY.LIFETIME
        self._move_range_x = consts.ENEMY.MOVE_RANGE_X
        self._move_range_y = consts.ENEMY.MOVE_RANGE_Y
        self._active_position_x = x
        self._active_position_y = y

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
                self._sync_rects()
                # Record position for small-range movement
                self._active_position_x = self.rect.x
                self._active_position_y = self.rect.y
                self._lifetime = 0
            else:
                # Eased entry: decelerate into target position
                t = self._entry_progress
                t_eased = 1.0 - (1.0 - t) * (1.0 - t)  # ease-out quad
                self.rect.x = self._entry_start_x + (self._entry_target_x - self._entry_start_x) * t_eased
                self.rect.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * t_eased
                self._sync_rects()
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
            self._sync_rects()
            return

        # Active state: check lifetime (15 seconds max)
        self._lifetime += 1
        if self._lifetime >= self._max_lifetime:
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
                self._sync_rects()
                # Fall through to skip rest of movement block
            else:
                timer = getattr(self, self._timer_attr, 0.0)
                if self.move_type == "hover":
                    timer /= 0.08

                params = self._rust_params
                new_x, new_y, new_timer = rust_update_movement(
                    self._rust_move_type_code, timer,
                    self._active_position_x, self._active_position_y,
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

                self._sync_rects()
        else:
            # Fallback to Python movement via strategy pattern
            self._movement_strategy.update(self)

        # Blend from entry target to full pattern amplitude during transition
        if self._transition_timer < self._transition_duration:
            self._transition_timer += 1
            t = self._transition_timer / self._transition_duration
            blend = t * t  # ease-in quad
            self.rect.x = self._active_position_x + (self.rect.x - self._active_position_x) * blend
            self.rect.y = self._active_position_y + (self.rect.y - self._active_position_y) * blend
            self._sync_rects()

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
            self._active_position_x, self._active_position_y,
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

    def _sync_rects(self) -> None:
        self._collision_rect.x = self.rect.x - (self._collision_rect.width - self.rect.width) // 2
        self._collision_rect.y = self.rect.y - (self._collision_rect.height - self.rect.height) // 2

    def _fire(self) -> None:
        bullets = self._create_bullets()

        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _create_bullets(self) -> List[Bullet]:
        bullets = []
        center_x = self.rect.centerx

        if self.data.bullet_type == "spread":
            for angle in [-40, -20, 0, 20, 40]:
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
    MIN_SPAWN_Y = -30
    MAX_SPAWN_Y_FRACTION = 0.70
    LASER_FIRE_RATE = 60
    NORMAL_FIRE_RATE = 80
    ENTRY_SPAWN_Y = -50

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
        self._max_enemies = self.MAX_CONCURRENT_ENEMIES
        self._wave_active = False
        self._wave_enemies_spawned = 0
        self._wave_size = self._get_wave_size()
        self._pending_spawns: list = []

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

    def set_params(self, health: int, speed: float, spawn_rate: int, bullet_type: str = "single") -> None:
        self.health = health
        self.speed = speed
        self.spawn_rate = spawn_rate
        self.bullet_type = bullet_type

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def update(self, enemies: List[Enemy], slow_factor: float = 1.0,
               player_pos: tuple = None) -> None:
        # Count active enemies (not exiting or dead)
        active_enemies = 0
        for e in enemies:
            if e.active and e._state != 'exiting':
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
        spawn_data = []
        for px, py in positions:
            px = max(collision_size // 2, min(px, screen_width - collision_size // 2))
            py = max(self.MIN_SPAWN_Y, min(py, int(screen_height * self.MAX_SPAWN_Y_FRACTION)))
            spawn_data.append((
                px, py,
                random.choice(bullet_types),
                self._select_enemy_type(),
            ))
        return spawn_data

    def _spawn_one(self, enemies: List[Enemy], data: tuple) -> None:
        """Create a single enemy from precomputed spawn tuple and add to list."""
        px, py, bullet_type, enemy_type = data
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

        self.survival_timer += 1

        if self.survival_timer >= self.data.escape_time:
            self.escaped = True
            self.active = False
            return

        if self.survival_timer >= self.data.escape_time - get_game_constants().ENEMY.ESCAPE_WARNING:
            self._show_escape_warning = True
            self.rect.y -= self.ESCAPE_DRIFT

        self._move_phase_timer += 1
        if self._move_phase_timer >= self._move_phase_duration:
            self._move_phase_timer = 0
            self._move_phase_duration = random.randint(90, 200)
            self._select_next_target(player_pos)

        lerp_speed = self.LERP_FACTOR * self.data.speed
        self.rect.x = self.rect.x + (self._target_x - self.rect.x) * lerp_speed
        self.rect.y = self.rect.y + (self._target_y - self.rect.y) * lerp_speed

        screen_w = get_screen_width()
        screen_h = get_screen_height()
        self.rect.x = max(0, min(self.rect.x, screen_w - self.rect.width))
        self.rect.y = max(self.MIN_Y, min(self.rect.y, screen_h // 2 + self.CENTER_OFFSET))

        self.rect.y += int(math.sin(self.survival_timer * 0.025) * 0.4)

        self.phase_timer += 1
        if self.phase_timer >= get_game_constants().BOSS.PHASE_INTERVAL and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire()

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

    def _fire(self) -> None:
        bullets = []

        self.attack_direction = random.choice(self.ATTACK_DIRECTIONS)

        if self.attack_pattern == 0:
            bullets = self._spread_attack()
        elif self.attack_pattern == 1:
            bullets = self._aim_attack()
        else:
            bullets = self._wave_attack()

        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

        self.attack_pattern = (self.attack_pattern + 1) % 3

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

        direction_sources = self._get_direction_sources()

        source_x, source_y = direction_sources.get(self.attack_direction, (self.rect.centerx, self.rect.bottom))

        target_offsets = self._get_target_offsets()
        dx, dy = target_offsets.get(self.attack_direction, (0, BOSS_ATTACK_DISTANCE))

        bullet_data = BulletData(
            damage=BOSS_AIM_BULLET_DAMAGE_BASE + self.phase * self.AIM_DAMAGE_INCREMENT,
            speed=BOSS_AIM_SPEED,
            owner="enemy",
            bullet_type="laser"
        )

        for i in range(self.AIM_BULLET_COUNT):
            bullet = Bullet(source_x - BOSS_BULLET_OFFSET_X + i * BOSS_BULLET_OFFSET_X, source_y, bullet_data)
            velocity = Vector2(dx, dy)
            velocity = velocity.normalize() * BOSS_AIM_SPEED
            bullet.velocity = velocity
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
        draw_boss_ship(surface, self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height, health_ratio)

        if self.entering:
            warning_y = 20
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.3 + 0.7
            warning_surf = self._get_warning_font().render("! 警告 !", True, (255, 50, 50))
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

    def is_entering(self) -> bool:
        return self.entering

    def is_escaped(self) -> bool:
        return self.escaped

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)
