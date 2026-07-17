"""Player weapon component.

Owns: bullet list, fire / auto_fire / cooldown, weapon modifiers
(spread / laser / explosive), muzzle geometry, and bullet creation.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
The component reads the owner's ``rect`` and ``facing_direction`` (via
the ``PlayerAim`` component) and writes to the owner's
``bullet_damage`` for legacy access patterns. Public callers use
``player.get_bullets()`` / ``player.fire()`` / ``player.auto_fire()``,
all of which forward here.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from airwar.config.constants_access import get_game_constants
from airwar.entities.bullet import Bullet, BulletData

if TYPE_CHECKING:
    from airwar.entities.player import Player


class PlayerWeapon:
    """Weapon state: bullet list, cooldown, weapon modifiers.

    Args:
        owner: The Player instance (read ``rect``/``bullet_damage``,
            read ``facing_direction`` from the aim component).
    """

    # Bullet spawn geometry (mirrors legacy class-level constants).
    SPREAD_ANGLES = (-10, 0, 10)
    _SPREAD_TRIG = {angle: (math.cos(math.radians(angle)), math.sin(math.radians(angle))) for angle in SPREAD_ANGLES}
    WING_MUZZLE_X_OFFSETS = (-24, 24)
    WING_MUZZLE_Y_OFFSET = -36

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self._constants = get_game_constants()
        self._bullets: list[Bullet] = []
        self._bullet_listeners: list = []
        # Cooldown
        self._fire_cooldown: int = 0
        self._fire_interval: int = self._constants.PLAYER.FIRE_COOLDOWN
        # Weapon modifiers (set via set_weapon_modifiers or activate_*)
        self._has_spread: bool = False
        self._has_laser: bool = False
        self._has_explosive: bool = False
        # Laser duration countdown (frames)
        self._laser_duration: int = 0

    # ------------------------------------------------------------------
    # Public API called by Player.
    # ------------------------------------------------------------------

    @property
    def bullets(self) -> list[Bullet]:
        return self._bullets

    def get_bullets(self) -> list[Bullet]:
        return self._bullets

    def remove_bullet(self, bullet: Bullet) -> None:
        bullet.active = False

    def cleanup_inactive_bullets(self) -> None:
        if not self._bullets:
            return
        # Filter in-place to avoid allocating a new list each frame
        self._bullets[:] = [b for b in self._bullets if b.active]

    def add_listener(self, listener) -> None:
        if hasattr(listener, "on_bullet_fired"):
            self._bullet_listeners.append(listener)

    def remove_listener(self, listener) -> None:
        if listener in self._bullet_listeners:
            self._bullet_listeners.remove(listener)

    def fire(self) -> Bullet | None:
        """Single-shot fire; returns first bullet (or None on cooldown)."""
        if self._fire_cooldown <= 0:
            self._fire_cooldown = self._fire_interval
            return self._create_bullets_for_shot_mode(return_first=True)
        return None

    def auto_fire(self) -> None:
        """Per-frame auto-fire: emit bullets on cooldown, play SFX.

        Used by the game loop for continuous firing. Caller is
        expected to gate this on ``is_controls_locked``; this method
        does NOT re-check because the legacy Player wraps it before
        calling the component.
        """
        if self._fire_cooldown <= 0:
            self._fire_cooldown = self._fire_interval
            self._create_bullets_for_shot_mode()
            # Lazy import keeps the audio subsystem out of the player
            # import graph until it is needed.
            from airwar.audio import get_sound_manager

            get_sound_manager().play_sfx("bullet_fire")

    def activate_shotgun(self) -> None:
        self._has_spread = True

    def activate_laser(self, duration: int) -> None:
        self._has_laser = True
        self._laser_duration = max(1, duration)

    def activate_explosive(self) -> None:
        self._has_explosive = True

    def set_weapon_modifiers(self, spread: bool, laser: bool, explosive: bool) -> None:
        self._has_spread = spread
        self._has_laser = laser
        self._has_explosive = explosive

    def get_weapon_status(self) -> dict:
        return {
            "spread": self._has_spread,
            "laser": self._has_laser,
            "explosive": self._has_explosive,
        }

    # ------------------------------------------------------------------
    # Per-frame update (cooldown, laser duration)
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self._fire_cooldown > 0:
            self._fire_cooldown -= 1
        if self._laser_duration > 0:
            self._laser_duration -= 1
            if self._laser_duration <= 0:
                self._has_laser = False

    # ------------------------------------------------------------------
    # Bullet creation (private)
    # ------------------------------------------------------------------

    def _create_bullets_for_shot_mode(self, return_first: bool = False) -> Bullet | None:
        owner = self._owner
        first_bullet = None
        aim_dir = owner.get_facing_direction()

        if self._has_spread:
            for muzzle_x, muzzle_y in self._wing_muzzle_positions():
                for angle in self.SPREAD_ANGLES:
                    bullet = self._create_bullet_from_muzzle(
                        muzzle_x,
                        muzzle_y,
                        BulletData(
                            damage=owner.bullet_damage,
                            speed=self._constants.PLAYER.BULLET_SPEED,
                            angle_offset=angle,
                            bullet_type="spread_laser" if self._has_laser else "spread",
                        ),
                    )
                    self._aim_bullet_velocity(bullet, aim_dir, angle)
                    if self._has_laser:
                        bullet.data.is_laser = True
                    if self._has_explosive:
                        bullet.data.is_explosive = True
                    self._bullets.append(bullet)
                    if first_bullet is None:
                        first_bullet = bullet
            return first_bullet if return_first else None

        for muzzle_x, muzzle_y in self._wing_muzzle_positions():
            bullet = self._create_bullet_from_muzzle(
                muzzle_x,
                muzzle_y,
                self._create_primary_bullet_data(),
            )
            self._aim_bullet_velocity(bullet, aim_dir)
            if self._has_explosive:
                bullet.data.is_explosive = True
            self._bullets.append(bullet)
            if first_bullet is None:
                first_bullet = bullet
        return first_bullet

    def _wing_muzzle_positions(self) -> tuple[tuple[float, float], ...]:
        """Compute the wing muzzle world coordinates for this frame.

        The muzzles are offset perpendicular and along the aim direction
        so they follow the ship's facing angle.
        """
        owner = self._owner
        right_x = -owner.get_facing_direction().y
        right_y = owner.get_facing_direction().x
        forward_x = owner.get_facing_direction().x
        forward_y = owner.get_facing_direction().y
        center_x = owner.rect.centerx
        center_y = owner.rect.centery
        return tuple(
            (
                center_x + right_x * offset_x + forward_x * abs(self.WING_MUZZLE_Y_OFFSET),
                center_y + right_y * offset_x + forward_y * abs(self.WING_MUZZLE_Y_OFFSET),
            )
            for offset_x in self.WING_MUZZLE_X_OFFSETS
        )

    def _create_primary_bullet_data(self) -> BulletData:
        owner = self._owner
        if self._has_laser:
            return BulletData(
                damage=owner.bullet_damage,
                speed=self._constants.PLAYER.BULLET_SPEED,
                bullet_type="laser",
                is_laser=True,
            )
        return BulletData(damage=owner.bullet_damage, speed=self._constants.PLAYER.BULLET_SPEED)

    def _create_bullet_from_muzzle(self, muzzle_x: float, muzzle_y: float, data: BulletData) -> Bullet:
        bullet = Bullet(muzzle_x, muzzle_y, data)
        bullet.rect.x = muzzle_x - bullet.rect.width / 2
        bullet.rect.y = muzzle_y - bullet.rect.height / 2
        return bullet

    def _aim_bullet_velocity(self, bullet: Bullet, aim_direction, angle_offset: float = 0.0) -> None:
        direction = aim_direction
        if angle_offset:
            trig = self._SPREAD_TRIG.get(angle_offset)
            if trig is None:
                angle_rad = math.radians(angle_offset)
                trig = (math.cos(angle_rad), math.sin(angle_rad))
            cos_a, sin_a = trig
            direction = type(direction)(
                aim_direction.x * cos_a - aim_direction.y * sin_a,
                aim_direction.x * sin_a + aim_direction.y * cos_a,
            )
        bullet.velocity = direction * bullet.data.speed
