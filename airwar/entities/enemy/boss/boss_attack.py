"""Boss attack patterns: spread / aim / wave / enrage snapshot.

Each attack method returns a list of :class:`Bullet` instances ready to
be handed to the bullet spawner. The :class:`Boss` class picks which
attack to run and whether the aim attack should dash first; everything
else lives here.

The muzzle-position helpers (regular and primary) and the muzzle-flash
triggering logic also live in this module because the enrage snapshot
attack is tightly coupled to muzzle geometry.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from airwar.config.constants_access import get_game_constants

from ...base import Vector2
from ...bullet import Bullet, BulletData
from .boss_state import (
    ENRAGE_BULLET_SPEED,
    ENRAGE_LASER_SPEED,
    ENRAGE_MUZZLE_FLASH_DURATION,
    ENRAGE_MUZZLE_FORWARD_SCALE,
    ENRAGE_MUZZLE_SIDE_SCALE,
    ENRAGE_RELEASE_BULLET_SPEED,
    ENRAGE_RELEASE_INTERVAL,
    ENRAGE_RELEASE_LASER_SPEED,
    ENRAGE_SNAPSHOT_LASER_COUNT,
    ENRAGE_SNAPSHOT_RING_COUNT,
)

if TYPE_CHECKING:
    from .boss import Boss


_BOSS_TUNING = get_game_constants().BOSS_TUNING

# Backward-compatible aliases. The values are sourced from
# GAME_CONSTANTS.BOSS_TUNING so boss attack tuning has one definition.
ATTACK_DIRECTIONS = list(_BOSS_TUNING.ATTACK_DIRECTIONS)
SPREAD_DAMAGE_INCREMENT = _BOSS_TUNING.SPREAD_DAMAGE_INCREMENT
AIM_DAMAGE_INCREMENT = _BOSS_TUNING.AIM_DAMAGE_INCREMENT
AIM_BULLET_COUNT = _BOSS_TUNING.AIM_BULLET_COUNT
WAVE_BULLET_COUNT = _BOSS_TUNING.WAVE_BULLET_COUNT


class BossAttackPatterns:
    """Pure attack logic — no state machine, no movement.

    The boss holds an instance of this class; per-frame, the boss's
    ``update`` method calls into it for the current attack pattern and
    also for muzzle geometry (used by the enrage snapshot attack and by
    the muzzle-flash renderer).
    """

    def __init__(self, boss: Boss) -> None:
        self._boss = boss

    # ------------------------------------------------------------------
    # Direction helpers
    # ------------------------------------------------------------------

    def get_direction_offsets(self) -> dict[str, tuple[int, int]]:
        boss = self._boss
        return {
            "down": (-90, boss.rect.bottom),
            "left": (180, boss.rect.centery),
            "right": (0, boss.rect.centery),
            "up": (90, boss.rect.y),
        }

    def get_direction_sources(self) -> dict[str, tuple[int, int]]:
        boss = self._boss
        return {
            "down": (boss.rect.centerx, boss.rect.bottom),
            "left": (boss.rect.left, boss.rect.centery),
            "right": (boss.rect.right, boss.rect.centery),
            "up": (boss.rect.centerx, boss.rect.y),
        }

    def get_target_offsets(self) -> dict[str, tuple[int, int]]:
        d = get_game_constants().BOSS.ATTACK_DISTANCE
        return {"down": (0, d), "left": (-d, 0), "right": (d, 0), "up": (0, -d)}

    def select_attack_direction_for_target(self, player_pos: tuple[float, float]) -> None:
        boss = self._boss
        dx = player_pos[0] - boss.rect.centerx
        dy = player_pos[1] - boss.rect.centery
        if abs(dx) > abs(dy) * 1.2:
            boss.attack_direction = "right" if dx > 0 else "left"
        else:
            boss.attack_direction = "down" if dy >= 0 else "up"

    def choose_attack_direction(self) -> str:
        return random.choice(ATTACK_DIRECTIONS)

    # ------------------------------------------------------------------
    # Regular attacks (no enrage)
    # ------------------------------------------------------------------

    def spread_attack(self) -> list[Bullet]:
        boss = self._boss
        B = get_game_constants().BOSS
        bullets: list[Bullet] = []
        direction_offsets = self.get_direction_offsets()
        base_angle, y_pos = direction_offsets.get(boss.attack_direction, (-90, boss.rect.bottom))
        center_x = boss.rect.centerx
        bullet_count = B.SPREAD_BULLET_COUNT_BASE + boss.phase
        for i in range(bullet_count):
            if boss.attack_direction == "left" or boss.attack_direction == "right":
                angle = base_angle + (B.SIDE_ANGLE_RANGE / (bullet_count - 1)) * i - B.SIDE_ANGLE_OFFSET
            else:
                angle = base_angle + (B.SPREAD_ANGLE_RANGE / (bullet_count - 1)) * i
            rad = math.radians(angle)
            speed = B.SPREAD_SPEED
            vx = math.cos(rad) * speed
            vy = math.sin(rad) * speed
            bullet_data = BulletData(
                damage=B.BULLET_DAMAGE_BASE + boss.phase * SPREAD_DAMAGE_INCREMENT,
                speed=B.SPREAD_SPEED,
                owner="enemy",
                bullet_type="spread",
            )
            bullet = Bullet(center_x, y_pos, bullet_data)
            bullet.velocity = Vector2(vx, vy)
            bullets.append(bullet)
        return bullets

    def aim_attack(self, player_pos: tuple[float, float] | None = None) -> list[Bullet]:
        boss = self._boss
        bullets: list[Bullet] = []
        if player_pos:
            self.select_attack_direction_for_target(player_pos)

        direction_sources = self.get_direction_sources()
        source_x, source_y = direction_sources.get(boss.attack_direction, (boss.rect.centerx, boss.rect.bottom))

        if player_pos:
            aim_dx = player_pos[0] - source_x
            aim_dy = player_pos[1] - source_y
        else:
            target_offsets = self.get_target_offsets()
            aim_dx, aim_dy = target_offsets.get(
                boss.attack_direction,
                (0, get_game_constants().BOSS.ATTACK_DISTANCE),
            )

        aim_vector = Vector2(aim_dx, aim_dy)
        if aim_vector.length() <= 0:
            aim_vector = Vector2(0, get_game_constants().BOSS.ATTACK_DISTANCE)
        aim_vector = aim_vector.normalize()
        spread_axis = Vector2(-aim_vector.y, aim_vector.x)

        bullet_data = BulletData(
            damage=get_game_constants().BOSS.AIM_BULLET_DAMAGE_BASE + boss.phase * AIM_DAMAGE_INCREMENT,
            speed=get_game_constants().BOSS.AIM_SPEED,
            owner="enemy",
            bullet_type="laser",
        )

        for i in range(AIM_BULLET_COUNT):
            offset = (i - (AIM_BULLET_COUNT - 1) / 2) * get_game_constants().BOSS.BULLET_OFFSET_X
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

    def wave_attack(self) -> list[Bullet]:
        boss = self._boss
        bullets: list[Bullet] = []
        direction_sources = self.get_direction_sources()
        center_x, center_y = direction_sources.get(boss.attack_direction, (boss.rect.centerx, boss.rect.centery))
        for i in range(WAVE_BULLET_COUNT):
            if boss.attack_direction == "left":
                angle = 180 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            elif boss.attack_direction == "right":
                angle = 0 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            elif boss.attack_direction == "up":
                angle = 90 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            else:
                angle = -90 + get_game_constants().BOSS.WAVE_ANGLE_INTERVAL * i
            rad = math.radians(angle)
            speed = get_game_constants().BOSS.WAVE_SPEED
            bullet_data = BulletData(
                damage=get_game_constants().BOSS.WAVE_BULLET_DAMAGE,
                speed=speed,
                owner="enemy",
                bullet_type="single",
            )
            bullet = Bullet(center_x, center_y, bullet_data)
            bullet.velocity = Vector2(math.cos(rad) * speed, math.sin(rad) * speed)
            bullets.append(bullet)
        return bullets

    # ------------------------------------------------------------------
    # Enrage snapshot attack
    # ------------------------------------------------------------------

    def create_enrage_snapshot_attack(self, target: tuple[float, float], progress: float) -> list[Bullet]:
        boss = self._boss
        bullets: list[Bullet] = []
        source = self.primary_muzzle_position()
        bullets.extend(self._create_enrage_snapshot_lasers(source, target, progress))
        bullets.extend(self._create_enrage_snapshot_ring_bullets(target, progress))
        release_index = boss._state.enrage_attack_index
        for bullet in bullets:
            bullet.held = True
            bullet.clear_immune = True
            bullet.enrage_release_delay = release_index * ENRAGE_RELEASE_INTERVAL
        return bullets

    def _create_enrage_snapshot_lasers(
        self,
        source: tuple[float, float],
        target: tuple[float, float],
        progress: float,
    ) -> list[Bullet]:
        boss = self._boss
        aim = Vector2(target[0] - source[0], target[1] - source[1])
        if aim.length() <= 0:
            aim = Vector2(0, 1)
        aim = aim.normalize()
        side_axis = Vector2(-aim.y, aim.x)
        burst_axis = 1 if boss._state.enrage_attack_index % 2 == 0 else -1
        bullet_data = BulletData(
            damage=get_game_constants().BOSS.AIM_BULLET_DAMAGE_BASE + boss.phase * AIM_DAMAGE_INCREMENT,
            speed=ENRAGE_LASER_SPEED,
            owner="enemy",
            bullet_type="laser",
        )
        bullets: list[Bullet] = []
        spread = max(boss.rect.width * 0.22, 34)
        for index in range(ENRAGE_SNAPSHOT_LASER_COUNT):
            offset = (index - (ENRAGE_SNAPSHOT_LASER_COUNT - 1) / 2) * spread
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
            bullet.enrage_release_speed = ENRAGE_RELEASE_LASER_SPEED
            bullets.append(bullet)
            self.trigger_muzzle_flash((bullet_x, bullet_y))
        return bullets

    def _create_enrage_snapshot_ring_bullets(self, target: tuple[float, float], progress: float) -> list[Bullet]:
        boss = self._boss
        cx, cy = target
        bullet_data = BulletData(
            damage=get_game_constants().BOSS.WAVE_BULLET_DAMAGE,
            speed=ENRAGE_BULLET_SPEED,
            owner="enemy",
            bullet_type="single",
        )
        bullets: list[Bullet] = []
        muzzles = self.boss_muzzle_positions()
        radius = max(boss.rect.width, boss.rect.height) * (1.65 + 0.25 * math.sin(progress * math.tau * 5))
        base_angle = progress * math.tau * 2.8 + boss._state.enrage_attack_index * 0.47
        gap_index = boss._state.enrage_attack_index % ENRAGE_SNAPSHOT_RING_COUNT
        for index in range(ENRAGE_SNAPSHOT_RING_COUNT):
            if index == gap_index:
                continue
            angle = base_angle + math.tau * index / ENRAGE_SNAPSHOT_RING_COUNT
            bullet_x = cx + math.cos(angle) * radius
            bullet_y = cy + math.sin(angle) * radius * 0.78
            direction = Vector2(cx - bullet_x, cy - bullet_y).normalize()
            if direction.length() <= 0:
                direction = Vector2(0, 1)
            bullet = Bullet(bullet_x, bullet_y, bullet_data)
            bullet.velocity = Vector2(0, 0)
            bullet.release_direction = direction
            bullet.enrage_release_speed = ENRAGE_RELEASE_BULLET_SPEED
            bullets.append(bullet)
            self.trigger_muzzle_flash(muzzles[(len(bullets) - 1) % len(muzzles)])
        return bullets

    # ------------------------------------------------------------------
    # Muzzle geometry
    # ------------------------------------------------------------------

    def facing_vector(self) -> Vector2:
        boss = self._boss
        radians = math.radians(boss._facing_angle)
        return Vector2(math.cos(radians), math.sin(radians))

    def boss_muzzle_positions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        boss = self._boss
        forward = self.facing_vector().normalize()
        if forward.length() <= 0:
            forward = Vector2(0, 1)
        side_axis = Vector2(-forward.y, forward.x)
        muzzle_center_x = boss.rect.centerx + forward.x * boss.rect.height * ENRAGE_MUZZLE_FORWARD_SCALE
        muzzle_center_y = boss.rect.centery + forward.y * boss.rect.height * ENRAGE_MUZZLE_FORWARD_SCALE
        side_offset = boss.rect.width * ENRAGE_MUZZLE_SIDE_SCALE
        return (
            (
                muzzle_center_x + side_axis.x * side_offset,
                muzzle_center_y + side_axis.y * side_offset,
            ),
            (
                muzzle_center_x - side_axis.x * side_offset,
                muzzle_center_y - side_axis.y * side_offset,
            ),
        )

    def primary_muzzle_position(self) -> tuple[float, float]:
        muzzles = self.boss_muzzle_positions()
        return (
            (muzzles[0][0] + muzzles[1][0]) / 2,
            (muzzles[0][1] + muzzles[1][1]) / 2,
        )

    def trigger_muzzle_flash(self, position: tuple[float, float] | None = None) -> None:
        boss = self._boss
        boss._muzzle_flash_timer = ENRAGE_MUZZLE_FLASH_DURATION
        if position is None:
            boss._muzzle_flash_positions = list(self.boss_muzzle_positions())
            return
        boss._muzzle_flash_positions.append(position)

    def tick_muzzle_flash(self) -> None:
        boss = self._boss
        if boss._muzzle_flash_timer <= 0:
            return
        boss._muzzle_flash_timer -= 1
        if boss._muzzle_flash_timer <= 0:
            boss._muzzle_flash_positions = []


__all__ = [
    "AIM_BULLET_COUNT",
    "AIM_DAMAGE_INCREMENT",
    "ATTACK_DIRECTIONS",
    "SPREAD_DAMAGE_INCREMENT",
    "WAVE_BULLET_COUNT",
    "BossAttackPatterns",
]
