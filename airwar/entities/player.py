"""Player entity module.

Provides the Player class representing the user's spaceship, handling
movement, weapon firing, health and shield systems.
"""

# === Standard library ===
import math
from typing import List, Optional, Tuple

# === Third-party ===
import pygame

# === Local: same package ===
from .base import Entity
from .base import Vector2
from .bullet import Bullet, BulletData

# === Local: different package in airwar ===
from ..input.input_handler import InputHandler
from ..config import (
    get_screen_width,
    get_screen_height,
    HITBOX_INDICATOR_PADDING,
    HITBOX_INDICATOR_FREQUENCY,
    HITBOX_INDICATOR_ALPHA_MIN,
    HITBOX_INDICATOR_ALPHA_MAX,
)
from ..utils.sprites import draw_player_ship
from ..config.constants_access import get_game_constants


class Player(Entity):
    """Player entity representing the user's spaceship.

    Handles movement via InputHandler, weapon firing, health and shield
    systems. Bullets are delegated to UIManager for rendering to avoid
    double rendering.

    Attributes:
        health: Current health points (0 to max_health).
        max_health: Maximum health points.
        speed: Movement speed in pixels per frame.
        bullet_damage: Damage dealt by each bullet.
        is_shielded: Whether the player currently has shield active.
    """

    # --- Class constants ---
    PLAYER_SPRITE_W = 68
    PLAYER_SPRITE_H = 82
    DEFAULT_RECOVERY_RATE = 1.0
    DEFAULT_SPEED_MULT = 1.7
    DEFAULT_BOOST_MAX = 200
    DEFAULT_BOOST_RECOVERY_DELAY = 90
    DEFAULT_BOOST_RECOVERY_RAMP = 120
    PLAYER_HITBOX_W = 10
    PLAYER_HITBOX_H = 14
    BOOST_RAMP_MIN = 0.15
    BOOST_RAMP_DELTA = 0.85
    BULLET_SPAWN_Y_OFFSET = 36
    SPREAD_ANGLES = (-15, 0, 15)
    LASER_X_OFFSET = 3
    SINGLE_X_OFFSET = 5
    PHASE_DASH_COST_RATIO = 0.25
    PHASE_DASH_WINDUP_FRAMES = 5
    PHASE_DASH_ACTIVE_FRAMES = 14
    PHASE_DASH_RECOVERY_FRAMES = 8
    PHASE_DASH_COOLDOWN_FRAMES = 90
    PHASE_DASH_DISTANCE = 250
    PHASE_DASH_MIN_DISTANCE = 120
    PHASE_DASH_ALPHA_MIN = 75
    PHASE_DASH_ALPHA_MAX = 165

    # 1. Special methods

    def __init__(self, x: float, y: float, input_handler: InputHandler):
        constants = get_game_constants()
        super().__init__(x, y, self.PLAYER_SPRITE_W, self.PLAYER_SPRITE_H)
        self._constants = constants  # Cache for hot path access
        self._input_handler = input_handler
        self.health = constants.PLAYER.MAX_HEALTH
        self.max_health = constants.PLAYER.MAX_HEALTH
        self.base_speed = constants.PLAYER.SPEED
        self.speed = self.base_speed
        self.bullet_damage = constants.PLAYER.BULLET_DAMAGE
        # Boost system
        self.boost_active: bool = False
        self.boost_max: float = self.DEFAULT_BOOST_MAX
        self.boost_current: float = self.DEFAULT_BOOST_MAX
        self.boost_recovery_rate: float = self.DEFAULT_RECOVERY_RATE
        self.boost_speed_mult: float = self.DEFAULT_SPEED_MULT
        self.boost_recovery_delay: int = self.DEFAULT_BOOST_RECOVERY_DELAY
        self.boost_recovery_ramp: int = self.DEFAULT_BOOST_RECOVERY_RAMP
        self.phase_dash_enabled: bool = False
        self._boost_idle_frames: int = 0
        self._boost_pressed_last_frame = False
        self.mothership_cooldown_mult: float = 1.0
        self._fire_cooldown = 0
        self._has_spread = False
        self._has_laser = False
        self._has_explosive = False
        self._bullet_listeners: List = []
        self._bullets: List = []
        self.is_shielded = False
        self._shield_duration = 0
        self.controls_locked = False
        self.hitbox_width = self.PLAYER_HITBOX_W
        self.hitbox_height = self.PLAYER_HITBOX_H
        self._hitbox_timer = 0
        self._render_hitbox = False
        self._hitbox_glow_surf = None
        self._phase_dash_state = "ready"
        self._phase_dash_timer = 0
        self._phase_dash_cooldown = 0
        self._phase_dash_start = (0.0, 0.0)
        self._phase_dash_target = (0.0, 0.0)
        self._phase_dash_direction = (0.0, -1.0)
        self._aim_target: Tuple[float, float] | None = None
        self._last_aim_direction = Vector2(0, -1)

    # 2. Properties

    @property
    def fire_cooldown(self) -> int:
        return self._fire_cooldown

    @fire_cooldown.setter
    def fire_cooldown(self, value: int) -> None:
        self._fire_cooldown = value

    @property
    def bullet_damage_value(self) -> int:
        return self.bullet_damage

    @bullet_damage_value.setter
    def bullet_damage_value(self, value: int) -> None:
        self.bullet_damage = value

    # 3. Public lifecycle methods

    def update(self, *args, **kwargs) -> None:
        """Update player state each frame.

        Moves the player, updates weapon cooldowns, activates shield
        timer, and increments the hitbox indicator timer.
        """
        self._update_movement()
        self._update_weapons(*args, **kwargs)
        self._update_effects()
        self._hitbox_timer += 1

    def render(self, surface: pygame.Surface) -> None:
        """Render the player ship and hitbox indicator.

        Args:
            surface: Pygame surface to render onto.
        """
        if self.is_phase_dashing():
            sprite = pygame.Surface((int(self.rect.width * 4), int(self.rect.height * 3)), pygame.SRCALPHA)
            draw_player_ship(sprite, sprite.get_width() / 2, sprite.get_height() / 2, self.rect.width, self.rect.height)
            alpha = self._phase_dash_alpha()
            sprite.set_alpha(alpha)
            surface.blit(sprite, sprite.get_rect(center=(self.rect.centerx, self.rect.centery)))
        else:
            draw_player_ship(surface, self.rect.centerx, self.rect.centery, self.rect.width, self.rect.height)

        self._render_hitbox_indicator(surface)

    # 4. Public behavior methods

    def fire(self) -> Optional[Bullet]:
        """Fire a single bullet from the player ship.

        Returns:
            Bullet entity if cooldown allows, None otherwise.
        """
        if self._fire_cooldown <= 0:
            self._fire_cooldown = self._constants.PLAYER.FIRE_COOLDOWN
            return self._create_bullets_for_shot_mode(return_first=True)
        return None

    def auto_fire(self) -> None:
        """Auto-fire bullets each frame when cooldown allows.

        Used by the game loop for continuous firing without returning
        the created bullets.
        """
        if self.controls_locked:
            return
        if self._fire_cooldown <= 0:
            self._fire_cooldown = self._constants.PLAYER.FIRE_COOLDOWN
            self._create_bullets_for_shot_mode()

    def activate_shotgun(self) -> None:
        """Enable spread-shot weapon mode."""
        self._has_spread = True

    def activate_laser(self, duration: int) -> None:
        """Enable laser weapon mode.

        Args:
            duration: Number of frames the laser remains active.
        """
        self._has_laser = True

    def activate_explosive(self) -> None:
        """Enable explosive bullet modifier."""
        self._has_explosive = True

    def activate_phase_dash(self) -> None:
        """Enable boost-fueled invincible phase dash."""
        self.phase_dash_enabled = True

    def take_damage(self, damage: int) -> None:
        """Apply damage to the player.

        Damage is ignored if the player has an active shield.
        If health reaches 0, the player dies (handled by health system).

        Args:
            damage: Amount of damage to apply.
        """
        if self.is_shielded:
            return
        self.health -= damage
        if self.health <= 0:
            self.health = 0

    def heal(self, amount: int) -> None:
        """Heal the player by a specified amount.

        Health cannot exceed max_health.

        Args:
            amount: Health points to restore.
        """
        self.health = min(self.max_health, self.health + amount)

    def activate_shield(self, duration: int) -> None:
        """Activate a temporary shield that blocks the next hit.

        Args:
            duration: Number of frames the shield remains active.
        """
        self.is_shielded = True
        self._shield_duration = duration

    def get_hitbox(self) -> pygame.Rect:
        hb_x = self.rect.x + (self.rect.width - self.hitbox_width) // 2
        hb_y = self.rect.y + (self.rect.height - self.hitbox_height) // 2
        return pygame.Rect(hb_x, hb_y, self.hitbox_width, self.hitbox_height)

    def get_boost_status(self) -> dict:
        return {
            'current': self.boost_current,
            'max': self.boost_max,
            'active': self.boost_active,
            'dash_cooldown': self._phase_dash_cooldown,
            'dash_cooldown_max': self.PHASE_DASH_COOLDOWN_FRAMES,
            'dash_enabled': self.phase_dash_enabled,
            'dash_active': self.is_phase_dashing(),
            'dash_ready': self.can_phase_dash(),
        }

    def get_bullets(self) -> List[Bullet]:
        return self._bullets

    def remove_bullet(self, bullet: Bullet) -> None:
        bullet.active = False

    def cleanup_inactive_bullets(self) -> None:
        if not self._bullets:
            return
        # 原地过滤以避免每次创建新列表
        self._bullets[:] = [b for b in self._bullets if b.active]

    def is_colliding_with(self, other) -> bool:
        return self.get_hitbox().colliderect(other.rect)

    def is_phase_dashing(self) -> bool:
        return self._phase_dash_state in {"windup", "active", "recovery"}

    def is_phase_dash_invincible(self) -> bool:
        return self._phase_dash_state in {"windup", "active", "recovery"}

    def can_phase_dash(self) -> bool:
        return (
            self.phase_dash_enabled
            and self._phase_dash_state == "ready"
            and self._phase_dash_cooldown <= 0
            and self.boost_current >= self._phase_dash_cost()
        )

    def add_listener(self, listener) -> None:
        if hasattr(listener, 'on_bullet_fired'):
            self._bullet_listeners.append(listener)

    def set_aim_target(self, x: float, y: float) -> None:
        self._aim_target = (x, y)

    def get_aim_target(self) -> Tuple[float, float] | None:
        return self._aim_target

    # 5. Private lifecycle methods

    def _update_movement(self) -> None:
        if self.controls_locked:
            return

        if self.is_phase_dashing():
            self._update_phase_dash_motion()
            self._update_boost_recovery(active_blocked=True)
            return

        self._update_phase_dash_cooldown()
        direction = self._input_handler.get_movement_direction()

        # Boost: activate when Shift held + has energy
        boost_pressed = self._input_handler.is_boost_pressed()
        boost_just_pressed = self._read_boost_just_pressed(boost_pressed)
        if boost_just_pressed and self.can_phase_dash():
            self._start_phase_dash(direction)
            self._update_phase_dash_motion()
            self._update_boost_recovery(active_blocked=True)
            return

        self.boost_active = boost_pressed and self.boost_current > 0

        if self.boost_active:
            self._boost_idle_frames = 0
            self.boost_current = max(0, self.boost_current - 1)
            self.speed = self.base_speed * self.boost_speed_mult
        else:
            self._update_boost_recovery()
            self.speed = self.base_speed

        self.rect.x += direction.x * self.speed
        self.rect.y += direction.y * self.speed
        self.rect.x = max(0, min(self.rect.x, get_screen_width() - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, get_screen_height() - self.rect.height))

    def _update_weapons(self, *args, **kwargs) -> None:
        if self._fire_cooldown > 0:
            self._fire_cooldown -= 1

    def _update_effects(self) -> None:
        if self._shield_duration > 0:
            self._shield_duration -= 1
            if self._shield_duration <= 0:
                self.is_shielded = False

    def _phase_dash_cost(self) -> float:
        return self.boost_max * self.PHASE_DASH_COST_RATIO

    def _read_boost_just_pressed(self, boost_pressed: bool) -> bool:
        if hasattr(self._input_handler, "is_boost_just_pressed"):
            return self._input_handler.is_boost_just_pressed()
        just_pressed = boost_pressed and not self._boost_pressed_last_frame
        self._boost_pressed_last_frame = boost_pressed
        return just_pressed

    def _update_boost_recovery(self, active_blocked: bool = False) -> None:
        if active_blocked:
            self.boost_active = False
        self._boost_idle_frames += 1
        if self._boost_idle_frames > self.boost_recovery_delay:
            ramp_frames = self._boost_idle_frames - self.boost_recovery_delay
            t = 1.0 if self.boost_recovery_ramp <= 0 else min(1.0, ramp_frames / self.boost_recovery_ramp)
            rate = self.boost_recovery_rate * (self.BOOST_RAMP_MIN + self.BOOST_RAMP_DELTA * t)
            self.boost_current = min(self.boost_max, self.boost_current + rate)

    def _update_phase_dash_cooldown(self) -> None:
        if self._phase_dash_cooldown > 0:
            self._phase_dash_cooldown -= 1

    def _start_phase_dash(self, direction) -> None:
        self.boost_current = max(0, self.boost_current - self._phase_dash_cost())
        self._boost_idle_frames = 0
        dx, dy = direction.x, direction.y
        if dx == 0 and dy == 0:
            dx, dy = self._phase_dash_direction
        length = math.hypot(dx, dy)
        if length <= 0:
            dx, dy = 0.0, -1.0
        else:
            dx, dy = dx / length, dy / length
        self._phase_dash_direction = (dx, dy)
        self._phase_dash_state = "windup"
        self._phase_dash_timer = self.PHASE_DASH_WINDUP_FRAMES
        self._phase_dash_start = (self.rect.x, self.rect.y)
        target_x = self.rect.x + dx * self.PHASE_DASH_DISTANCE
        target_y = self.rect.y + dy * self.PHASE_DASH_DISTANCE
        max_x = get_screen_width() - self.rect.width
        max_y = get_screen_height() - self.rect.height
        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))
        if math.hypot(target_x - self.rect.x, target_y - self.rect.y) < self.PHASE_DASH_MIN_DISTANCE:
            target_x = max(0, min(self.rect.x + dx * self.PHASE_DASH_MIN_DISTANCE, max_x))
            target_y = max(0, min(self.rect.y + dy * self.PHASE_DASH_MIN_DISTANCE, max_y))
        self._phase_dash_target = (target_x, target_y)

    def _update_phase_dash_motion(self) -> None:
        if self._phase_dash_state == "windup":
            self._phase_dash_timer -= 1
            if self._phase_dash_timer <= 0:
                self._phase_dash_state = "active"
                self._phase_dash_timer = 0
            return

        if self._phase_dash_state == "active":
            self._phase_dash_timer += 1
            progress = min(1.0, self._phase_dash_timer / self.PHASE_DASH_ACTIVE_FRAMES)
            eased = 1 - (1 - progress) * (1 - progress)
            self.rect.x = self._phase_dash_start[0] + (self._phase_dash_target[0] - self._phase_dash_start[0]) * eased
            self.rect.y = self._phase_dash_start[1] + (self._phase_dash_target[1] - self._phase_dash_start[1]) * eased
            if progress >= 1.0:
                self._phase_dash_state = "recovery"
                self._phase_dash_timer = self.PHASE_DASH_RECOVERY_FRAMES
            return

        if self._phase_dash_state == "recovery":
            self._phase_dash_timer -= 1
            if self._phase_dash_timer <= 0:
                self._phase_dash_state = "ready"
                self._phase_dash_cooldown = self.PHASE_DASH_COOLDOWN_FRAMES

    def _phase_dash_alpha(self) -> int:
        if self._phase_dash_state == "windup":
            return 210
        if self._phase_dash_state == "recovery":
            progress = 1 - max(0, self._phase_dash_timer) / self.PHASE_DASH_RECOVERY_FRAMES
            return int(self.PHASE_DASH_ALPHA_MAX + (255 - self.PHASE_DASH_ALPHA_MAX) * progress)
        pulse = abs(math.sin(self._hitbox_timer * 0.8))
        return int(self.PHASE_DASH_ALPHA_MIN + (self.PHASE_DASH_ALPHA_MAX - self.PHASE_DASH_ALPHA_MIN) * pulse)

    # 6. Private behavior methods

    def _create_bullets_for_shot_mode(self, return_first: bool = False) -> Optional[Bullet]:
        center_x = self.rect.x + self.rect.width / 2
        bullet_y = self.rect.y - self.BULLET_SPAWN_Y_OFFSET
        aim_direction = self._get_aim_direction(center_x, bullet_y)

        if self._has_spread:
            bullet_x = center_x - 5
            first_bullet = None
            for angle in self.SPREAD_ANGLES:
                bullet = Bullet(
                    bullet_x,
                    bullet_y,
                    BulletData(
                        damage=self.bullet_damage,
                        speed=self._constants.PLAYER.BULLET_SPEED,
                        angle_offset=angle,
                        bullet_type='spread_laser' if self._has_laser else 'spread'
                    )
                )
                self._aim_bullet_velocity(bullet, aim_direction, angle)
                if self._has_laser:
                    bullet.data.is_laser = True
                if self._has_explosive:
                    bullet.data.is_explosive = True
                self._bullets.append(bullet)
                if first_bullet is None:
                    first_bullet = bullet
            return first_bullet if return_first else None
        elif self._has_laser:
            bullet = Bullet(
                center_x - self.LASER_X_OFFSET,
                bullet_y,
                BulletData(damage=self.bullet_damage, speed=self._constants.PLAYER.BULLET_SPEED,
                          bullet_type='laser', is_laser=True)
            )
            self._aim_bullet_velocity(bullet, aim_direction)
            if self._has_explosive:
                bullet.data.is_explosive = True
            self._bullets.append(bullet)
            return bullet
        else:
            bullet = Bullet(
                center_x - self.SINGLE_X_OFFSET,
                bullet_y,
                BulletData(damage=self.bullet_damage, speed=self._constants.PLAYER.BULLET_SPEED)
            )
            self._aim_bullet_velocity(bullet, aim_direction)
            if self._has_explosive:
                bullet.data.is_explosive = True
            self._bullets.append(bullet)
            return bullet

    def _get_aim_direction(self, origin_x: float, origin_y: float) -> Vector2:
        if self._aim_target is None:
            return self._last_aim_direction

        dx = self._aim_target[0] - origin_x
        dy = self._aim_target[1] - origin_y
        length = math.hypot(dx, dy)
        if length <= 0.001:
            return self._last_aim_direction

        direction = Vector2(dx / length, dy / length)
        self._last_aim_direction = direction
        return direction

    def _aim_bullet_velocity(self, bullet: Bullet, aim_direction: Vector2, angle_offset: float = 0.0) -> None:
        direction = aim_direction
        if angle_offset:
            angle_rad = math.radians(angle_offset)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            direction = Vector2(
                aim_direction.x * cos_a - aim_direction.y * sin_a,
                aim_direction.x * sin_a + aim_direction.y * cos_a,
            )
        bullet.velocity = direction * bullet.data.speed

    def _render_hitbox_indicator(self, surface: pygame.Surface) -> None:
        hb = self.get_hitbox()
        padding = HITBOX_INDICATOR_PADDING
        cx = hb.width / 2 + padding
        cy = hb.height / 2 + padding
        pulse = abs(math.sin(self._hitbox_timer * HITBOX_INDICATOR_FREQUENCY))

        half_w = hb.width / 2
        half_h = hb.height / 2

        diamond_points = [
            (cx, cy - half_h),
            (cx + half_w, cy),
            (cx, cy + half_h),
            (cx - half_w, cy),
        ]

        alpha_range = HITBOX_INDICATOR_ALPHA_MAX - HITBOX_INDICATOR_ALPHA_MIN
        alpha = int(HITBOX_INDICATOR_ALPHA_MIN + pulse * alpha_range)

        # Reuse cached surface to avoid per-frame SRCALPHA allocation
        surf_size = (hb.width + padding * 2, hb.height + padding * 2)
        if self._hitbox_glow_surf is None or self._hitbox_glow_surf.get_size() != surf_size:
            self._hitbox_glow_surf = pygame.Surface(surf_size, pygame.SRCALPHA)
        self._hitbox_glow_surf.fill((0, 0, 0, 0))
        pygame.draw.polygon(self._hitbox_glow_surf, (255, 255, 255, alpha), diamond_points)

        surface.blit(self._hitbox_glow_surf, (hb.x - padding, hb.y - padding))
