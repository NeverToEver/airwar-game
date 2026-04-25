import pygame
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
# NOTE: GAME_CONSTANTS is imported locally in methods to avoid circular import

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
}

if TYPE_CHECKING:
    from airwar.scenes.game_scene import GameScene


class Enemy(Entity):
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
        self._entry_start_y = y - 150  # Start above screen
        self._entry_target_x = x
        self._entry_target_y = y
        self._exit_progress = 0.0
        self._exit_start_x = x
        self._exit_start_y = y
        self._exit_end_x = random.choice([x - 300, x + 300, x, x - 150, x + 150])
        self._exit_end_y = -150

        # Lifetime timer: 15 seconds = 900 frames at 60fps
        self._lifetime = 0
        self._max_lifetime = 900
        self._active_position_x = x
        self._active_position_y = y

    @property
    def collision_rect(self) -> pygame.Rect:
        return self._collision_rect

    @collision_rect.setter
    def collision_rect(self, value: pygame.Rect) -> None:
        self._collision_rect = value

    def _sync_rects(self) -> None:
        self._collision_rect.x = self.rect.x - (self._collision_rect.width - self.rect.width) // 2
        self._collision_rect.y = self.rect.y - (self._collision_rect.height - self.rect.height) // 2

    def _init_movement(self, enemy_type: str) -> None:
        if enemy_type == "sine":
            self.move_type = "sine"
            self.move_offset = random.uniform(0, math.pi * 2)
            self.move_amplitude = random.uniform(1.5, 3.0)
            self.move_frequency = random.uniform(0.03, 0.06)
            self.start_x = self.rect.x
            self.move_timer = 0
            
        elif enemy_type == "zigzag":
            self.move_type = "zigzag"
            self.direction = random.choice([-1, 1])
            self.zigzag_timer = 0
            self.zigzag_interval = random.randint(30, 60)
            self.zigzag_speed = random.uniform(1.5, 2.5)
            
        elif enemy_type == "dive":
            self.move_type = "dive"
            self.target_x = self.start_x = self.rect.x
            self.dive_timer = 0
            self.dive_delay = random.randint(20, 50)
            self.diving = False
            
        elif enemy_type == "hover":
            self.move_type = "hover"
            self.hover_timer = 0
            self.hover_speed = random.uniform(1.0, 1.8)
            self.hover_amplitude = random.uniform(20, 40)
            self.start_x = self.rect.x
            
        elif enemy_type == "spiral":
            self.move_type = "spiral"
            self.spiral_timer = 0
            self.spiral_speed = random.uniform(1.0, 2.0)
            self.spiral_radius = random.uniform(30, 50)
            self.spiral_frequency = random.uniform(0.05, 0.08)
            self.start_x = self.rect.x
            
        else:
            self.move_type = "straight"

    def update(self, *args, **kwargs) -> None:
        if not self.active:
            return

        # Handle entry animation
        if self._state == 'entering':
            # Check if enemy somehow got placed off screen during entry
            if self.rect.y > get_screen_height():
                self.active = False
                return

            self._entry_progress += 0.02
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
                # Linear entry animation from above screen to target position
                t = self._entry_progress
                self.rect.x = self._entry_start_x + (self._entry_target_x - self._entry_start_x) * t
                self.rect.y = self._entry_start_y + (self._entry_target_y - self._entry_start_y) * t
                self._sync_rects()
            return

        # Handle exit animation
        if self._state == 'exiting':
            self._exit_progress += 0.015
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
            self._exit_end_x = random.choice([
                self.rect.x - 300,
                self.rect.x + 300,
                self.rect.x,
                self.rect.x - 150,
                self.rect.x + 150
            ])
            self._exit_end_y = -100
            return

        # Movement range around active position
        move_range_x = 80
        move_range_y = 40

        # Try Rust movement first if available
        # Exclude zigzag: Rust uses active_x as base instead of current x,
        # which produces different (non-accumulating) movement behavior
        if rust_update_movement is not None and self.move_type in MOVEMENT_TYPE_MAP and self.move_type != "zigzag":
            move_type_code = MOVEMENT_TYPE_MAP[self.move_type]

            # Get movement timer
            timer = getattr(self, 'move_timer', 0.0)
            if self.move_type == "zigzag":
                timer = getattr(self, 'zigzag_timer', 0.0)
            elif self.move_type == "dive":
                timer = getattr(self, 'dive_timer', 0.0)
            elif self.move_type == "hover":
                timer = getattr(self, 'hover_timer', 0.0) / 0.08  # Convert back to frame count
            elif self.move_type == "spiral":
                timer = getattr(self, 'spiral_timer', 0.0)

            # Get movement parameters
            offset = getattr(self, 'move_offset', 0.0)
            amplitude = getattr(self, 'move_amplitude', 2.0)
            # Spiral uses its own random frequency (set in __init__), other types use move_frequency
            if self.move_type == "spiral":
                frequency = getattr(self, 'spiral_frequency', 0.05)
            else:
                frequency = getattr(self, 'move_frequency', 0.05)
            speed = getattr(self, 'zigzag_speed', 2.0) if self.move_type == "zigzag" else getattr(self, 'spiral_speed', 2.0)
            direction = getattr(self, 'direction', 1.0)
            zigzag_interval = getattr(self, 'zigzag_interval', 45.0)
            spiral_radius = getattr(self, 'spiral_radius', 40.0)

            new_x, new_y, new_timer = rust_update_movement(
                move_type_code, timer,
                self._active_position_x, self._active_position_y,
                move_range_x, move_range_y,
                offset, amplitude, frequency, speed, direction,
                zigzag_interval, spiral_radius
            )

            self.rect.x = new_x
            self.rect.y = new_y

            # Update timer back
            if self.move_type == "zigzag":
                self.zigzag_timer = new_timer
            elif self.move_type == "dive":
                self.dive_timer = new_timer
            elif self.move_type == "hover":
                self.hover_timer = new_timer * 0.08
            elif self.move_type == "spiral":
                self.spiral_timer = new_timer
            else:
                self.move_timer = new_timer

            self._sync_rects()
        else:
            # Fallback to Python movement
            if self.move_type == "sine":
                self.move_timer += 1
                self.rect.x = self._active_position_x + math.sin(self.move_timer * self.move_frequency + self.move_offset) * move_range_x
                self.rect.y = self._active_position_y + math.sin(self.move_timer * self.move_frequency * 0.5) * move_range_y
                self._sync_rects()

            elif self.move_type == "zigzag":
                self.zigzag_timer += 1
                if self.zigzag_timer >= self.zigzag_interval:
                    self.zigzag_timer = 0
                    self.direction *= -1
                new_x = self.rect.x + self.direction * self.zigzag_speed
                self.rect.x = max(self._active_position_x - move_range_x, min(new_x, self._active_position_x + move_range_x))
                self.rect.y = self._active_position_y + math.sin(self.zigzag_timer * 0.1) * (move_range_y * 0.5)
                self._sync_rects()

            elif self.move_type == "dive":
                self.dive_timer += 1
                wave = math.sin(self.dive_timer * 0.05) * (move_range_x * 0.3)
                self.rect.x = self._active_position_x + wave
                self.rect.y = self._active_position_y + math.sin(self.dive_timer * 0.03) * (move_range_y * 0.3)
                self._sync_rects()

            elif self.move_type == "hover":
                self.hover_timer += 0.08
                self.rect.x = self._active_position_x + math.sin(self.hover_timer) * move_range_x
                self.rect.y = self._active_position_y + math.sin(self.hover_timer * 0.7) * (move_range_y * 0.5)
                self._sync_rects()

            elif self.move_type == "spiral":
                self.spiral_timer += 1
                spiral_x = math.cos(self.spiral_timer * self.spiral_frequency) * (move_range_x * 0.5)
                spiral_y = math.sin(self.spiral_timer * self.spiral_frequency * 2) * (move_range_y * 0.3)
                self.rect.x = self._active_position_x + spiral_x
                self.rect.y = self._active_position_y + spiral_y
                self._sync_rects()

            else:
                # straight movement with very small vertical oscillation
                self.rect.x = self._active_position_x
                self.rect.y = self._active_position_y + math.sin(self._lifetime * 0.05) * (move_range_y * 0.3)
                self._sync_rects()

        if self.rect.y > screen_height:
            self.active = False

        self.fire_timer += 1
        fire_threshold = max(10, int(self.data.fire_rate / self._fire_rate_modifier))
        if self.fire_timer >= fire_threshold:
            self.fire_timer = 0
            self._fire()

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
        # Local import to avoid circular dependency
        from ..game.constants import GAME_CONSTANTS
        return GAME_CONSTANTS.BOSS.BULLET_DAMAGE_MAP.get(self.data.bullet_type, 15)

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

    def render(self, surface: pygame.Surface) -> None:
        if not self._sprite:
            health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
            draw_enemy_ship(surface, self.rect.x, self.rect.y, 
                          self.rect.width, self.rect.height, health_ratio)
        else:
            surface.blit(self._sprite, self.get_rect())

    def set_sprite(self, sprite: pygame.Surface) -> None:
        self._sprite = sprite

    def take_damage(self, damage: int) -> None:
        if damage is None or damage < 0:
            return
        self.health -= damage
        if self.health <= 0:
            self.active = False

    def get_hitbox(self) -> pygame.Rect:
        return self._collision_rect

    def check_point_collision(self, x: float, y: float) -> bool:
        return self._collision_rect.collidepoint(x, y)


class EnemySpawner:
    def __init__(self):
        self.spawn_timer = 0
        self.health = 100
        self.speed = 3.0
        self.spawn_rate = 30
        self.bullet_type = "single"
        self._bullet_spawner: Optional[IBulletSpawner] = None
        self._enemy_type_distribution = {
            "straight": 0.25,
            "sine": 0.20,
            "zigzag": 0.18,
            "dive": 0.14,
            "hover": 0.13,
            "spiral": 0.10,
        }
        self._max_enemies = 5
        self._wave_active = False
        self._wave_enemies_spawned = 0
        self._wave_size = self._get_wave_size()

    def _get_wave_size(self) -> int:
        # Local import to avoid circular dependency
        from ..game.constants import GAME_CONSTANTS
        return GAME_CONSTANTS.BALANCE.WAVE_SIZE

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
        active_enemies = [e for e in enemies if e.active and e._state != 'exiting']

        # Check if wave is complete (all enemies exited or died)
        if self._wave_active and len(active_enemies) == 0 and self._wave_enemies_spawned >= self._wave_size:
            self._wave_active = False
            self._wave_enemies_spawned = 0

        # Start new wave if no wave active — spawn V-formation immediately
        if not self._wave_active:
            self._wave_active = True
            self._wave_enemies_spawned = 0
            self._spawn_v_formation(enemies, slow_factor, player_pos)

    def _spawn_v_formation(self, enemies: List[Enemy], slow_factor: float,
                           player_pos: tuple = None) -> None:
        """Spawn a wave of enemies in V-formation with tip pointing toward the player."""
        screen_width = get_screen_width()
        screen_height = get_screen_height()

        # V-formation: tip closest to player, arms opening upward
        # Formation tip positioned in the upper half of the screen
        player_x = player_pos[0] if player_pos else screen_width // 2

        # Arm geometry: horizontal spread and vertical step per arm position
        arm_spread = 140  # px per step outward
        arm_step = 50      # px per step upward
        enemies_per_side = (self._wave_size - 1) // 2

        # Clamp tip_x so the entire V-formation stays within screen bounds
        margin = enemies_per_side * arm_spread + 40
        base_x = min(margin, max(player_x, screen_width - margin))
        tip_x = base_x + random.randint(-80, 80)
        tip_x = max(margin, min(tip_x, screen_width - margin))
        tip_y = int(screen_height * 0.40) + random.randint(-30, 30)

        # Generate V formation positions: tip first, then alternating left/right up the arms
        positions = [(tip_x, tip_y)]
        for i in range(1, enemies_per_side + 1):
            positions.append((tip_x - arm_spread * i, tip_y - arm_step * i))
            positions.append((tip_x + arm_spread * i, tip_y - arm_step * i))

        # If wave_size is even, add one more at the top center
        if len(positions) < self._wave_size:
            top_y = tip_y - arm_step * enemies_per_side
            positions.append((tip_x, top_y - arm_step))

        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2
        collision_size = int(base_size * ENEMY_COLLISION_SCALE)

        bullet_types = ["single", "spread", "laser"]

        for px, py in positions:
            # Clamp to screen bounds (upper half only)
            px = max(collision_size // 2, min(px, screen_width - collision_size // 2))
            py = max(-30, min(py, int(screen_height * 0.70)))

            bullet_type = random.choice(bullet_types)
            enemy_type = self._select_enemy_type()

            data = EnemyData(
                health=self.health,
                speed=self.speed * slow_factor,
                bullet_type=bullet_type,
                fire_rate=60 if bullet_type == "laser" else 80,
                enemy_type=enemy_type
            )
            enemy = Enemy(px, py, data)
            # Override entry start Y so all enemies fly in from above screen
            enemy._entry_start_y = -50
            enemy._entry_start_x = px
            if self._bullet_spawner:
                enemy.set_bullet_spawner(self._bullet_spawner)
            enemies.append(enemy)
            self._wave_enemies_spawned += 1


@dataclass
class BossData:
    health: int = 2000
    speed: float = 1.5
    score: int = 5000
    width: float = 120
    height: float = 100
    fire_rate: int = 45
    phase: int = 1
    escape_time: int = 3000


class Boss(Entity):
    ATTACK_DIRECTIONS = ['down', 'left', 'right', 'up']
    _warning_font = None
    _escape_font = None

    @classmethod
    def _get_warning_font(cls):
        if cls._warning_font is None:
            cls._warning_font = pygame.font.Font(None, 36)
        return cls._warning_font

    @classmethod
    def _get_escape_font(cls):
        if cls._escape_font is None:
            cls._escape_font = pygame.font.Font(None, 28)
        return cls._escape_font

    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.move_direction = 1
        self.move_timer = 0
        self.attack_pattern = 0
        self.attack_direction = 'down'
        self.entering = True
        self.entry_y = y
        self.target_y = 80
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
        # Local import to avoid circular dependency
        from ..game.constants import GAME_CONSTANTS
        d = GAME_CONSTANTS.BOSS.ATTACK_DISTANCE
        return {
            'down': (0, d),
            'left': (-d, 0),
            'right': (d, 0),
            'up': (0, -d)
        }

    def update(self, enemies: List['Enemy'] = None, slow_factor: float = 1.0,
              player_pos: Tuple[int, int] = None, *args, **kwargs) -> None:
        if self.entering:
            self.rect.y += 2 * slow_factor
            if self.rect.y >= self.target_y:
                self.rect.y = self.target_y
                self.entering = False
            return

        self.survival_timer += 1

        if self.survival_timer >= self.data.escape_time:
            self.escaped = True
            self.active = False
            return

        if self.survival_timer >= self.data.escape_time - 180:
            self._show_escape_warning = True
            self.rect.y -= 0.5

        self.move_timer += 1
        if self.move_timer >= 60:
            self.move_timer = 0
            self.move_direction *= -1

        self.rect.x += self.move_direction * self.data.speed

        if self.rect.x <= 0:
            self.rect.x = 0
            self.move_direction = 1
        elif self.rect.x >= get_screen_width() - self.rect.width:
            self.rect.x = get_screen_width() - self.rect.width
            self.move_direction = -1

        self.phase_timer += 1
        if self.phase_timer >= 300 and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire()

    def _fire(self) -> None:
        import random
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
        # Local import to avoid circular dependency
        from ..game.constants import GAME_CONSTANTS
        B = GAME_CONSTANTS.BOSS
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
                damage=B.BULLET_DAMAGE_BASE + self.phase * 2,
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
            damage=BOSS_AIM_BULLET_DAMAGE_BASE + self.phase * 3,
            speed=BOSS_AIM_SPEED,
            owner="enemy",
            bullet_type="laser"
        )

        for i in range(3):
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

        for i in range(8):
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
        health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
        draw_boss_ship(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height, health_ratio)

        if self.entering:
            warning_y = 20
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.3 + 0.7
            warning_surf = self._get_warning_font().render("! WARNING !", True, (255, 50, 50))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

        if self._show_escape_warning and not self.entering:
            warning_y = 50
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.02)) * 0.3 + 0.7
            warning_surf = self._get_escape_font().render("ESCAPING...", True, (255, 200, 50))
            warning_surf.set_alpha(int(255 * pulse))
            warning_rect = warning_surf.get_rect(center=(surface.get_width() // 2, warning_y))
            surface.blit(warning_surf, warning_rect)

    def take_damage(self, damage: int) -> int:
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
