"""Boss entity — thin coordinator over four components.

The class is a coordinator over four components in the ``boss/`` subpackage:

* :class:`BossStateMachine` (in :mod:`.boss_state`) — lifecycle, enrage
  timers, damage-lock policy
* :class:`BossMovement` (in :mod:`.boss_movement`) — 4-phase patrol,
  aim-dash, enrage path
* :class:`BossAttackPatterns` (in :mod:`.boss_attack`) — spread/aim/
  wave/snapshot attacks
* :class:`BossRenderer` (in :mod:`.boss_render`) — sprite blit, facing
  angle, trail

The class is intentionally a coordinator; public gameplay behavior is
delegated to the component that owns it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from airwar.config import (
    get_screen_height,
    get_screen_width,
)
from airwar.config.constants_access import get_game_constants

from ...base import Entity, Vector2
from ...bullet import Bullet
from ...interfaces import IBulletSpawner
from . import boss_attack, boss_movement, boss_render, boss_state

if TYPE_CHECKING:
    from .enemy import Enemy


_BOSS_TUNING = get_game_constants().BOSS_TUNING


@dataclass
class BossData:
    """Data class for Boss entity configuration.

    Attributes:
        health: Maximum health points.
        speed: Movement speed in pixels per frame.
        score: Score awarded when points are defeated.
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
    """Boss entity with phase-based attacks and enrage sub-machine.

    After the Phase 1 refactor (boss class split), this class is a thin
    coordinator over four components:

    * :class:`BossStateMachine` -- lifecycle, enrage timers, damage-lock
    * :class:`BossMovement`     -- 4-phase patrol, aim-dash, enrage path
    * :class:`BossAttackPatterns` -- spread/aim/wave/snapshot attacks
    * :class:`BossRenderer`     -- sprite blit, facing angle, trail

    Public gameplay behavior is delegated to the component that owns it.
    """

    # Re-exported tuning constants so legacy ``Boss.ENRAGE_DURATION``
    # style imports continue to work after the split. Values are sourced
    # from GAME_CONSTANTS.BOSS_TUNING / BOSS_ENRAGE.
    ATTACK_DIRECTIONS = boss_attack.ATTACK_DIRECTIONS
    DEFAULT_PHASE_DURATION = boss_movement.DEFAULT_PHASE_DURATION
    ENTRY_SPEED = boss_movement.ENTRY_SPEED
    ESCAPE_DRIFT = boss_movement.ESCAPE_DRIFT
    LERP_FACTOR = boss_movement.LERP_FACTOR
    MIN_Y = boss_movement.MIN_Y
    CENTER_OFFSET = boss_movement.CENTER_OFFSET
    SPREAD_DAMAGE_INCREMENT = boss_attack.SPREAD_DAMAGE_INCREMENT
    AIM_DAMAGE_INCREMENT = boss_attack.AIM_DAMAGE_INCREMENT
    AIM_BULLET_COUNT = boss_attack.AIM_BULLET_COUNT
    WAVE_BULLET_COUNT = boss_attack.WAVE_BULLET_COUNT
    HITBOX_WIDTH_SCALE = _BOSS_TUNING.HITBOX_WIDTH_SCALE
    HITBOX_HEIGHT_SCALE = _BOSS_TUNING.HITBOX_HEIGHT_SCALE
    AIM_DASH_DISTANCE = boss_movement.AIM_DASH_DISTANCE
    AIM_DASH_PHASE_BONUS = boss_movement.AIM_DASH_PHASE_BONUS
    AIM_DASH_MAX_DISTANCE_RATIO = boss_movement.AIM_DASH_MAX_DISTANCE_RATIO
    AIM_DASH_DURATION = boss_movement.AIM_DASH_DURATION
    ENRAGE_TRIGGER_RATIO = boss_state.ENRAGE_TRIGGER_RATIO
    ENRAGE_DURATION = boss_state.ENRAGE_DURATION
    ENRAGE_TRANSITION_DURATION = boss_state.ENRAGE_TRANSITION_DURATION
    ENRAGE_SLOW_FACTOR = boss_state.ENRAGE_SLOW_FACTOR
    ENRAGE_BULLET_SPEED = boss_state.ENRAGE_BULLET_SPEED
    ENRAGE_LASER_SPEED = boss_state.ENRAGE_LASER_SPEED
    ENRAGE_RELEASE_BULLET_SPEED = boss_state.ENRAGE_RELEASE_BULLET_SPEED
    ENRAGE_RELEASE_LASER_SPEED = boss_state.ENRAGE_RELEASE_LASER_SPEED
    ENRAGE_ATTACK_INTERVAL = boss_state.ENRAGE_ATTACK_INTERVAL
    ENRAGE_ATTACK_WINDUP = boss_state.ENRAGE_ATTACK_WINDUP
    ENRAGE_RELEASE_INTERVAL = boss_state.ENRAGE_RELEASE_INTERVAL
    ENRAGE_SNAPSHOT_LASER_COUNT = boss_state.ENRAGE_SNAPSHOT_LASER_COUNT
    ENRAGE_SNAPSHOT_RING_COUNT = boss_state.ENRAGE_SNAPSHOT_RING_COUNT
    ENRAGE_PATH_RADIUS_SCALE = boss_state.ENRAGE_PATH_RADIUS_SCALE
    ENRAGE_SQUARE_PATH_RATIO = boss_state.ENRAGE_SQUARE_PATH_RATIO
    ENRAGE_TRAIL_LENGTH = boss_state.ENRAGE_TRAIL_LENGTH
    ENRAGE_TRAIL_RENDER_MAX = boss_state.ENRAGE_TRAIL_RENDER_MAX
    ENRAGE_TRAIL_FINAL_SCALE = boss_state.ENRAGE_TRAIL_FINAL_SCALE
    ENRAGE_TRAIL_SCALE = boss_state.ENRAGE_TRAIL_SCALE
    ENRAGE_TRAIL_BLUR_PASSES = boss_state.ENRAGE_TRAIL_BLUR_PASSES
    ENRAGE_EXIT_BACK_OFFSET = boss_state.ENRAGE_EXIT_BACK_OFFSET
    ENRAGE_MUZZLE_FLASH_DURATION = boss_state.ENRAGE_MUZZLE_FLASH_DURATION
    ENRAGE_MUZZLE_FLASH_PULSES = boss_state.ENRAGE_MUZZLE_FLASH_PULSES
    ENRAGE_MUZZLE_FORWARD_SCALE = boss_state.ENRAGE_MUZZLE_FORWARD_SCALE
    ENRAGE_MUZZLE_SIDE_SCALE = boss_state.ENRAGE_MUZZLE_SIDE_SCALE
    ENRAGE_RELEASE_HOLD_DURATION = boss_state.ENRAGE_RELEASE_HOLD_DURATION
    ENRAGE_RETURN_DURATION = boss_state.ENRAGE_RETURN_DURATION
    ENRAGE_CORE_COLOR = boss_state.ENRAGE_CORE_COLOR
    ENRAGE_DANGER_COLOR = boss_state.ENRAGE_DANGER_COLOR
    ENRAGE_TRAIL_TINT = boss_state.ENRAGE_TRAIL_TINT

    def __init__(self, x: float, y: float, data: BossData):
        super().__init__(x, y, data.width, data.height)
        self.data = data
        self.health = data.health
        self.max_health = data.health
        self.fire_timer = 0
        self.phase_timer = 0
        self.attack_pattern = 0
        self.attack_direction = "down"
        self.is_entering = True
        self.entry_y = y
        self.target_y = 180
        # Movement phase system
        self._move_phase = 0
        self._move_phase_timer = 0
        self._move_phase_duration = self.DEFAULT_PHASE_DURATION
        self._target_x: float = float(x)
        self._target_y: float = 180.0
        self.survival_timer = 0
        self.is_escaped = False
        self._escape_notified = False
        self._death_consumed = False
        self._show_escape_warning = False
        self.phase = data.phase
        self._bullet_spawner: IBulletSpawner | None = None
        self.entity_id = id(self)
        self._hitbox = pygame.Rect(0, 0, 0, 0)
        # Aim-dash state used by movement and attacks.
        self._aim_dash_elapsed = 0
        self._aim_dash_duration = 0
        self._aim_dash_start_x = 0.0
        self._aim_dash_start_y = 0.0
        self._aim_dash_target_x = 0.0
        self._aim_dash_target_y = 0.0
        self._aim_fire_target: tuple[float, float] | None = None
        # Enrage render-only state
        self._facing_angle = 90.0
        self._muzzle_flash_timer = 0
        self._muzzle_flash_positions: list[tuple[float, float]] = []
        self._enrage_trail: list[tuple[float, float]] = []
        self._enrage_trail_ghost: pygame.Surface | None = None
        self._enrage_trail_ghost_key: tuple[int, int, int, int] | None = None
        self._enrage_trail_render_ghost: pygame.Surface | None = None
        self._enrage_trail_render_ghost_key: tuple[int, int, int] | None = None
        self._enrage_bullets: list[Bullet] = []
        # ---- Components (Phase 1 split) ----
        self._state = boss_state.BossStateMachine(self)
        self._movement = boss_movement.BossMovement(self)
        self._attack = boss_attack.BossAttackPatterns(self)
        self._renderer = boss_render.BossRenderer(self)
        self.sync_hitbox()

    # ------------------------------------------------------------------
    # Hitbox
    # ------------------------------------------------------------------

    def sync_hitbox(self) -> None:
        self._hitbox.width = int(self.rect.width * self.HITBOX_WIDTH_SCALE)
        self._hitbox.height = int(self.rect.height * self.HITBOX_HEIGHT_SCALE)
        self._hitbox.center = (int(self.rect.centerx), int(self.rect.centery))

    def get_hitbox(self) -> pygame.Rect:
        self.sync_hitbox()
        return self._hitbox

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def update(
        self,
        enemies: list[Enemy] | None = None,
        slow_factor: float = 1.0,
        player_pos: tuple[int, int] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Update boss state each frame.

        After the Phase 1 split, this method is the single per-frame
        entry point. The explicit state→movement→attack ordering is
        preserved by consulting :class:`BossStateMachine` first and only
        running movement/attack when appropriate.
        """
        if not self.active:
            return
        # 1. Entrance animation
        if self.is_entering:
            if self._movement.tick_entry(slow_factor):
                self.is_entering = False
                self._state.finish_entry()
            return

        player = kwargs.get("player")

        # 2. Enrage trigger (idempotent, may transition the state machine)
        self._trigger_enrage_if_needed(player_pos, player)

        # 3. Enrage sub-state dispatch
        if self._state.is_enrage_transitioning():
            self._movement.tick_enrage_transition()
            target = self._state.enrage_snapshot_target
            if target is not None:
                self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_transition_timer()
            if self._state.enrage_transition_timer <= 0:
                self._state.finish_enrage_transition()
            return

        if self._state.is_enrage_active():
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_timer()
            target = self._state.enrage_snapshot_target
            if target is not None:
                self._renderer.record_enrage_trail()
                progress = self._state.enrage_progress()
                self._movement.tick_enrage_active()
                self._renderer.face_target(target)
                self._update_enrage_snapshot_attacks(target, progress)
            if self._state.enrage_timer <= 0:
                fallback_target = target or (get_screen_width() / 2, get_screen_height() / 2)
                self._move_behind_player_after_enrage(fallback_target)
                self._release_enrage_bullets(fallback_target)
            return

        if self._state.is_enrage_release_holding():
            target = (
                self._current_player_target(player, player_pos)
                or self._state.enrage_snapshot_target
                or (get_screen_width() / 2, get_screen_height() / 2)
            )
            self._movement.tick_enrage_release_hold()
            self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_release_hold_timer()
            if self._state.enrage_release_hold_timer <= 0:
                self._movement.start_enrage_return()
            return

        if self._state.is_enrage_returning():
            target = self._current_player_target(player, player_pos) or self._state.enrage_snapshot_target
            self._movement.tick_enrage_return()
            if target is not None:
                self._renderer.face_target(target)
            self._attack.tick_muzzle_flash()
            self._state.tick_enrage_return_timer()
            if self._state.enrage_return_timer <= 0:
                self._state.finish_enrage_return()
                self.fire_timer = 0
            return

        # 4. Active (non-enrage) frame
        self.survival_timer += 1
        if self.survival_timer >= self.data.escape_time:
            self.is_escaped = True
            self.active = False
            self._state.mark_escaped()
            return

        if self._movement.is_aim_dashing():
            if self._movement.tick_aim_dash():
                self._finish_aim_dash()
            return

        self._movement.tick_active(player_pos, slow_factor)

        self.phase_timer += 1
        if self.phase_timer >= get_game_constants().BOSS.PHASE_INTERVAL and self.phase < 3:
            self.phase_timer = 0
            self.phase += 1

        self.fire_timer += 1
        if self.fire_timer >= self.data.fire_rate:
            self.fire_timer = 0
            self._fire(player_pos)

    # ------------------------------------------------------------------
    # Damage & death
    # ------------------------------------------------------------------

    def take_damage(self, damage: int) -> int:
        """Apply damage to the boss. Returns score value if killed."""
        new_health, score_delta = self._state.compute_take_damage(damage)
        if new_health != self.health:
            self.health = new_health
        if score_delta:
            self.active = False
            self._state.mark_dead()
        return score_delta

    def is_death_consumed(self) -> bool:
        return getattr(self, "_death_consumed", False)

    def consume_death(self) -> None:
        self._death_consumed = True

    # ------------------------------------------------------------------
    # Public enrage predicates (delegate to state machine)
    # ------------------------------------------------------------------

    def should_lock_player_movement(self) -> bool:
        return self._state.should_lock_player_movement()

    def enrage_slow_factor(self) -> float:
        return self._state.enrage_slow_factor()

    def enrage_visual_intensity(self) -> float:
        return self._state.enrage_visual_intensity()

    # ------------------------------------------------------------------
    # Read-only public properties for rendering / external observers
    # ------------------------------------------------------------------

    @property
    def enrage_timer(self) -> int:
        return self._state.enrage_timer

    @property
    def show_escape_warning(self) -> bool:
        return getattr(self, "_show_escape_warning", False)

    @property
    def facing_angle(self) -> float:
        return getattr(self, "_facing_angle", 90.0)

    @property
    def enrage_snapshot_target(self) -> tuple[float, float] | None:
        return self._state.enrage_snapshot_target

    @property
    def muzzle_flash_timer(self) -> int:
        return getattr(self, "_muzzle_flash_timer", 0)

    @property
    def muzzle_flash_positions(self) -> list[tuple[float, float]]:
        return getattr(self, "_muzzle_flash_positions", [])

    @property
    def enrage_trail(self) -> list[tuple[float, float]]:
        return getattr(self, "_enrage_trail", [])

    @property
    def enrage_trail_ghost(self) -> pygame.Surface | None:
        return getattr(self, "_enrage_trail_ghost", None)

    @property
    def enrage_trail_ghost_key(self) -> tuple[int, int, int, int] | None:
        return getattr(self, "_enrage_trail_ghost_key", None)

    @property
    def enrage_transition_timer(self) -> int:
        return self._state.enrage_transition_timer

    # ------------------------------------------------------------------
    # Renderer-bug-fix shims (Phase 5-β)
    #
    # ``airwar.game.rendering.entity_renderer`` reads three enrage
    # fields directly off the Boss instance (lines 134, 193-194,
    # 324-326). The Phase 1 split moved these to BossStateMachine but
    # the renderer was never updated, so the read raised AttributeError
    # during enrage. These three read-only shims restore the legacy
    # access path. The fields live on BossStateMachine (and ultimately
    # on EnrageSubMachine post-Phase 5-β); they are *not* set on Boss
    # itself.
    # ------------------------------------------------------------------

    @property
    def _enrage_transition_timer(self) -> int:
        return self._state.enrage_transition_timer

    # ------------------------------------------------------------------
    # Component entry points used by the Boss update flow.
    # ------------------------------------------------------------------

    def _fire(self, player_pos: tuple[float, float] | None = None) -> None:
        self.attack_direction = self._attack.choose_attack_direction()
        bullets: list[Bullet] = []
        if self.attack_pattern == 0:
            bullets = self._attack.spread_attack()
        elif self.attack_pattern == 1:
            if player_pos and self._movement.start_aim_dash(player_pos):
                self._aim_fire_target = (float(player_pos[0]), float(player_pos[1]))
                self.fire_timer = 0
                return
            bullets = self._attack.aim_attack(player_pos)
        else:
            bullets = self._attack.wave_attack()
        self._spawn_bullets(bullets)
        self.attack_pattern = (self.attack_pattern + 1) % 3

    def _spawn_bullets(self, bullets: list[Bullet]) -> None:
        if self._bullet_spawner:
            for bullet in bullets:
                self._bullet_spawner.spawn_bullet(bullet)

    def _facing_vector(self):
        return self._renderer.facing_vector()

    def _finish_aim_dash(self) -> None:
        self._movement.finish_aim_dash()
        bullets = self._attack.aim_attack(self._aim_fire_target)
        self._aim_fire_target = None
        self._spawn_bullets(bullets)
        self.attack_pattern = (self.attack_pattern + 1) % 3

    # ------------------------------------------------------------------
    # Enrage orchestration
    # ------------------------------------------------------------------

    def _trigger_enrage_if_needed(
        self,
        player_pos: tuple[int, int] | None = None,
        player=None,
    ) -> None:
        if self._state.enraged or self.max_health <= 0:
            return
        if self.health / self.max_health > self.ENRAGE_TRIGGER_RATIO:
            return
        target = self._center_player_for_enrage(player, player_pos)
        self._state.trigger_enrage(target)
        self._renderer.face_target(target)
        self._attack.trigger_muzzle_flash()
        self._renderer.clear_enrage_trail()

    def _center_player_for_enrage(
        self,
        player=None,
        player_pos: tuple[float, float] | tuple[int, int] | None = None,
    ) -> tuple[float, float]:
        target = (get_screen_width() / 2, get_screen_height() / 2)
        if player is not None:
            rect = player.rect
            new_x = max(0, min(target[0] - rect.width / 2, get_screen_width() - rect.width))
            new_y = max(0, min(target[1] - rect.height / 2, get_screen_height() - rect.height))
            rect.x, rect.y = new_x, new_y
            if hasattr(player, "sync_hitbox"):
                player.sync_hitbox()
            return target
        if player_pos:
            return (float(player_pos[0]), float(player_pos[1]))
        return target

    def _update_enrage_snapshot_attacks(
        self,
        target: tuple[float, float],
        progress: float,
    ) -> None:
        if not self._bullet_spawner or self._state.enrage_timer <= 1:
            return
        self._state.tick_enrage_attack_timer()
        if self._state.enrage_attack_timer > 0:
            return
        bullets = self._attack.create_enrage_snapshot_attack(target, progress)
        self._enrage_bullets.extend(bullets)
        self._spawn_bullets(bullets)
        self._state.reset_enrage_attack_timer()

    def _release_enrage_bullets(self, target: tuple[float, float]) -> None:
        for bullet in self._enrage_bullets:
            if not getattr(bullet, "clear_immune", False) or not getattr(bullet, "held", False):
                continue
            direction = getattr(bullet, "release_direction", None)
            if direction is None or direction.length() <= 0:
                direction = Vector2(target[0] - bullet.rect.centerx, target[1] - bullet.rect.centery)
                direction = direction.normalize() if direction.length() > 0 else Vector2(0, 1)
            bullet.release_direction = direction
            bullet.enrage_release_pending = True
            bullet.enrage_release_delay = max(0, getattr(bullet, "enrage_release_delay", 0))
        self._enrage_bullets.clear()
        # Compute the release anchor by walking the path all the way to 1.0.
        behind_center_x, behind_center_y = self._movement.enrage_path_center(target, 1.0)
        self._state.begin_enrage_release_hold((behind_center_x, behind_center_y))
        self._renderer.clear_enrage_trail()

    def _move_behind_player_after_enrage(self, target: tuple[float, float]) -> None:
        behind_center_x, behind_center_y = self._movement.enrage_path_center(target, 1.0)
        self.rect.x = behind_center_x - self.rect.width / 2
        self.rect.y = behind_center_y - self.rect.height / 2
        self._target_x = self.rect.x
        self._target_y = self.rect.y
        self.sync_hitbox()
        if target is not None:
            self._renderer.face_target(target)

    def _current_player_target(
        self, player=None, player_pos: tuple[int, int] | None = None
    ) -> tuple[float, float] | None:
        if player is not None:
            rect = player.rect
            if hasattr(rect, "centerx") and hasattr(rect, "centery"):
                return (float(rect.centerx), float(rect.centery))
            if all(hasattr(rect, attr) for attr in ("x", "y", "width", "height")):
                return (float(rect.x + rect.width / 2), float(rect.y + rect.height / 2))
        if player_pos:
            return (float(player_pos[0]), float(player_pos[1]))
        return None

    def _enrage_path_center(self, target: tuple[float, float], progress: float) -> tuple[float, float]:
        return self._movement.enrage_path_center(target, progress)

    # ------------------------------------------------------------------
    # Renderer
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        self._renderer.draw(surface)

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        self._bullet_spawner = spawner

    def get_time_remaining(self) -> float:
        remaining = self.data.escape_time - self.survival_timer
        return max(0, remaining) / 60.0

    def get_survival_progress(self) -> float:
        return min(1.0, self.survival_timer / self.data.escape_time)


__all__ = ["Boss", "BossData"]
