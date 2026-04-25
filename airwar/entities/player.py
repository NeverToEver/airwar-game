import pygame
import math
from typing import Optional, List
from .base import Entity
from .bullet import Bullet, BulletData
from airwar.input.input_handler import InputHandler


class Player(Entity):
    def __init__(self, x: float, y: float, input_handler: InputHandler):
        super().__init__(x, y, 50, 60)
        self._input_handler = input_handler
        self.health = 100
        self.max_health = 100
        self.speed = 5
        self.bullet_damage = 10
        self._fire_cooldown = 0
        self._has_spread = False
        self._has_laser = False
        self._has_explosive = False
        self._bullet_listeners: List = []
        self._bullets: List = []
        self.is_shielded = False
        self._shield_duration = 0
        self.hitbox_width = 12
        self.hitbox_height = 16
        self._hitbox_timer = 0
        self._render_hitbox = False

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

    def update(self, *args, **kwargs) -> None:
        self._update_movement()
        self._update_weapons(*args, **kwargs)
        self._update_effects()
        self._hitbox_timer += 1

    def _update_movement(self) -> None:
        direction = self._input_handler.get_movement_direction()
        self.rect.x += direction.x * self.speed
        self.rect.y += direction.y * self.speed
        from airwar.config import get_screen_width, get_screen_height
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

    def _create_bullets_for_shot_mode(self, return_first: bool = False) -> Optional[Bullet]:
        center_x = self.rect.x + self.rect.width / 2
        bullet_y = self.rect.y - 10

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

    def fire(self) -> Optional[Bullet]:
        if self._fire_cooldown <= 0:
            self._fire_cooldown = 8
            return self._create_bullets_for_shot_mode(return_first=True)
        return None

    def auto_fire(self) -> None:
        if self._fire_cooldown <= 0:
            self._fire_cooldown = 8
            self._create_bullets_for_shot_mode()

    def activate_shotgun(self) -> None:
        self._has_spread = True

    def activate_laser(self, duration: int) -> None:
        self._has_laser = True

    def activate_explosive(self) -> None:
        self._has_explosive = True

    def get_hitbox(self) -> pygame.Rect:
        hb_x = self.rect.x + (self.rect.width - self.hitbox_width) // 2
        hb_y = self.rect.y + (self.rect.height - self.hitbox_height) // 2
        return pygame.Rect(hb_x, hb_y, self.hitbox_width, self.hitbox_height)

    def _render_hitbox_indicator(self, surface: pygame.Surface) -> None:
        from airwar.config import (
            HITBOX_INDICATOR_PADDING,
            HITBOX_INDICATOR_FREQUENCY,
            HITBOX_INDICATOR_ALPHA_MIN,
            HITBOX_INDICATOR_ALPHA_MAX
        )

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

        glow_surf = pygame.Surface((hb.width + padding * 2, hb.height + padding * 2), pygame.SRCALPHA)
        glow_color = (255, 255, 255, alpha)
        pygame.draw.polygon(glow_surf, glow_color, diamond_points)
        
        surface.blit(glow_surf, (hb.x - padding, hb.y - padding))

    def add_listener(self, listener) -> None:
        if hasattr(listener, 'on_bullet_fired'):
            self._bullet_listeners.append(listener)

    def get_bullets(self) -> List[Bullet]:
        return self._bullets

    def remove_bullet(self, bullet: Bullet) -> None:
        bullet.active = False

    def cleanup_inactive_bullets(self) -> None:
        if not self._bullets:
            return

        i = 0
        while i < len(self._bullets):
            if not self._bullets[i].active:
                self._bullets.pop(i)
            else:
                i += 1

    def take_damage(self, damage: int) -> None:
        if self.is_shielded:
            return
        self.health -= damage
        if self.health <= 0:
            self.health = 0

    def heal(self, amount: int) -> None:
        self.health = min(self.max_health, self.health + amount)

    def activate_shield(self, duration: int) -> None:
        self.is_shielded = True
        self._shield_duration = duration

    def render(self, surface: pygame.Surface) -> None:
        from airwar.utils.sprites import draw_player_ship
        health_ratio = self.health / self.max_health if self.max_health > 0 else 1.0
        draw_player_ship(surface, self.rect.x, self.rect.y, self.rect.width, self.rect.height)
        
        self._render_hitbox_indicator(surface)
        
        for bullet in self._bullets:
            bullet.render(surface)

    def is_colliding_with(self, other) -> bool:
        return self.get_hitbox().colliderect(other.rect)
