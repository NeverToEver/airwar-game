"""Player entity module.

Provides the Player class representing the user's spaceship, handling
movement, weapon firing, health and shield systems.
"""

# === Standard library ===
import math
from typing import List, Optional

# === Third-party ===
import pygame

# === Local: same package ===
from .base import Entity
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

    # 1. Special methods

    def __init__(self, x: float, y: float, input_handler: InputHandler):
        constants = get_game_constants()
        super().__init__(x, y, 68, 82)
        self._constants = constants  # Cache for hot path access
        self._input_handler = input_handler
        self.health = constants.PLAYER.MAX_HEALTH
        self.max_health = constants.PLAYER.MAX_HEALTH
        self.speed = constants.PLAYER.SPEED
        self.bullet_damage = constants.PLAYER.BULLET_DAMAGE
        self._fire_cooldown = 0
        self._has_spread = False
        self._has_laser = False
        self._has_explosive = False
        self._bullet_listeners: List = []
        self._bullets: List = []
        self.is_shielded = False
        self._shield_duration = 0
        self.controls_locked = False
        self.hitbox_width = 10
        self.hitbox_height = 14
        self._hitbox_timer = 0
        self._render_hitbox = False
        self._hitbox_glow_surf = None

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

    def add_listener(self, listener) -> None:
        if hasattr(listener, 'on_bullet_fired'):
            self._bullet_listeners.append(listener)

    # 5. Private lifecycle methods

    def _update_movement(self) -> None:
        if self.controls_locked:
            return
        direction = self._input_handler.get_movement_direction()
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

    # 6. Private behavior methods

    def _create_bullets_for_shot_mode(self, return_first: bool = False) -> Optional[Bullet]:
        center_x = self.rect.x + self.rect.width / 2
        bullet_y = self.rect.y - 36

        if self._has_spread:
            bullet_x = center_x - 5
            first_bullet = None
            for angle in [-15, 0, 15]:
                bullet = Bullet(
                    bullet_x,
                    bullet_y,
                    BulletData(
                        damage=self.bullet_damage,
                        angle_offset=angle,
                        bullet_type='spread_laser' if self._has_laser else 'spread'
                    )
                )
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
                center_x - 3,
                bullet_y,
                BulletData(damage=self.bullet_damage, bullet_type='laser', is_laser=True)
            )
            if self._has_explosive:
                bullet.data.is_explosive = True
            self._bullets.append(bullet)
            return bullet
        else:
            bullet = Bullet(
                center_x - 5,
                bullet_y,
                BulletData(damage=self.bullet_damage)
            )
            if self._has_explosive:
                bullet.data.is_explosive = True
            self._bullets.append(bullet)
            return bullet

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
