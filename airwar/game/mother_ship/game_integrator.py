"""Game integrator — bridges mothership state with game systems.

F08 god-class split: animation state machines live in
``mothership_animations.py`` and gatling turret logic in
``mothership_gatling.py``. This class keeps the state bridge, save/load,
status data, ammo magazine, warning trigger, and the public API as
1-line forwarders to the extracted components.
"""

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config import get_screen_height, get_screen_width
from airwar.entities.base import BulletData
from airwar.entities.bullet import Bullet
from airwar.game.constants import GAME_CONSTANTS

from ..rendering.entity_renderer import EntityRenderer
from ..systems.lock_manager import LockLayer, LockRequest
from .event_bus import (
    EVENT_STATE_CHANGED,
    EVENT_UNDOCK_REQUESTED,
)
from .mother_ship_state import GameSaveData, MotherShipState
from .mothership_animations import MothershipAnimations
from .mothership_gatling import (
    MOTHERSHIP_GATLING_BARREL_X_OFFSETS,
    MOTHERSHIP_GATLING_BULLET_SPEED,
    MOTHERSHIP_GATLING_BULLET_TYPE,
    MOTHERSHIP_GATLING_DAMAGE,
    MOTHERSHIP_GATLING_FIRE_RATE,
    MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET,
    MOTHERSHIP_GATLING_OVERLAP_DEGREES,
    MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD,
    MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES,
    MOTHERSHIP_GATLING_SWEEP_PERIOD,
    MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES,
    MOTHERSHIP_GATLING_TURRETS,
    GatlingTurretSpec,
    MothershipGatling,
)
from .progress_bar_ui import ProgressBarUI

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .input_detector import InputDetector
    from .mother_ship import MotherShip
    from .persistence_manager import PersistenceManager
    from .state_machine import MotherShipStateMachine


# ── F08 god-class split: re-export public gatling spec / constants ────────
# External callers (including tests) reference these as
# ``GameIntegrator.MOTHERSHIP_GATLING_*``. Re-exporting them here keeps
# the public surface stable after the extraction.
__all__ = ["GameIntegrator", "GatlingTurretSpec"]


class GameIntegrator:
    """Game integrator — bridges mothership state with game systems.

    Coordinates between game state and mothership docking flow,
    updating entity states and UI during the docking process.

    F08 split:
    - Animation state machines live in :class:`MothershipAnimations`.
    - Gatling turret logic lives in :class:`MothershipGatling`.
    This class keeps the orchestration, save/load, and the public API
    (1-line forwarders for animation and gatling methods).
    """

    # Bullet / explosion damage constants (unchanged)
    MOTHERSHIP_BULLET_DAMAGE = 250
    MOTHERSHIP_FIRE_RATE = 18  # ~3.3 shots/sec at 60fps — heavy missile cadence
    MOTHERSHIP_BULLET_SPEED = 10
    MOTHERSHIP_TARGET_COUNT = 5  # fire at up to 5 closest enemies per volley
    MOTHERSHIP_EXPLOSION_RADIUS = 80
    MOTHERSHIP_EXPLOSION_DAMAGE = 60

    # Gatling constants re-exported from mothership_gatling so the
    # ``integrator.MOTHERSHIP_GATLING_*`` test access pattern keeps working.
    MOTHERSHIP_GATLING_DAMAGE = MOTHERSHIP_GATLING_DAMAGE
    MOTHERSHIP_GATLING_FIRE_RATE = MOTHERSHIP_GATLING_FIRE_RATE
    MOTHERSHIP_GATLING_BULLET_SPEED = MOTHERSHIP_GATLING_BULLET_SPEED
    MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES = MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES
    MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES = MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES
    MOTHERSHIP_GATLING_OVERLAP_DEGREES = MOTHERSHIP_GATLING_OVERLAP_DEGREES
    MOTHERSHIP_GATLING_SWEEP_PERIOD = MOTHERSHIP_GATLING_SWEEP_PERIOD
    MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD = MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD
    MOTHERSHIP_GATLING_BARREL_X_OFFSETS = MOTHERSHIP_GATLING_BARREL_X_OFFSETS
    MOTHERSHIP_GATLING_TURRETS = MOTHERSHIP_GATLING_TURRETS
    MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET = MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET
    MOTHERSHIP_GATLING_BULLET_TYPE = MOTHERSHIP_GATLING_BULLET_TYPE

    MOTHERSHIP_BULLET_DESPAWN_MARGIN = 80
    AMMO_CELL_COUNT = 10.0
    # F04 M2: link to GAME_CONSTANTS (was bare 1200)
    DOCKING_INVINCIBILITY_FRAMES = GAME_CONSTANTS.PERSISTENCE.DOCKING_INVINCIBILITY_FRAMES

    BAR_TYPE_HOLD = "hold"
    BAR_TYPE_COOLDOWN = "cooldown"
    BAR_TYPE_STAY = "stay"
    BAR_TYPE_EXIT = "exit"

    def __init__(
        self,
        event_bus: "EventBus",
        input_detector: "InputDetector",
        state_machine: "MotherShipStateMachine",
        persistence_manager: "PersistenceManager",
        progress_bar_ui: "ProgressBarUI",
        mother_ship: "MotherShip",
    ):
        self._event_bus = event_bus
        self._input_detector = input_detector
        self._state_machine = state_machine
        self._persistence_manager = persistence_manager
        self._progress_bar_ui = progress_bar_ui
        self._mother_ship = mother_ship

        # ── F08: extracted components (must come before attribute init) ──
        # The animation / gatling properties below forward to these, so
        # the components must exist before any property write happens.
        self._animations = MothershipAnimations(self)
        self._gatling = MothershipGatling(self)

        # Animation state aliases (forwarded via properties to _animations).
        # These lines exist so legacy callers that read these attributes
        # via ``self`` (rare — the integrator itself never sets them
        # after init) keep a sane default.
        self._entering_duration = self._animations.ENTERING_DURATION
        self._docking_animation_duration = self._animations.DOCKING_DURATION
        self._undocking_animation_duration = self._animations.UNDOCKING_EJECT_DURATION
        self._undocking_eject_duration = self._animations.UNDOCKING_EJECT_DURATION
        self._undocking_flyaway_duration = self._animations.UNDOCKING_FLYAWAY_DURATION

        self._undocking_cooldown_multiplier = 1.0

        self._game_scene = None
        self._player_control_disabled = False

        self._mothership_bullets: list[Bullet] = []
        self._entity_renderer = EntityRenderer()
        self._mothership_fire_timer = 0
        self._score_reduction_factor = 1.0 / 3.0

    # ── F08: animation state forwarders (preserved attribute names) ───────
    # These properties route reads/writes through ``self._animations`` so
    # the legacy ``integrator._entering_animation_active`` (etc.) names
    # keep working for tests and external callers.

    @property
    def _entering_animation_active(self) -> bool:
        return self._animations._entering_animation_active

    @_entering_animation_active.setter
    def _entering_animation_active(self, value: bool) -> None:
        self._animations._entering_animation_active = value

    @property
    def _entering_animation_frame(self) -> int:
        return self._animations._entering_animation_frame

    @_entering_animation_frame.setter
    def _entering_animation_frame(self, value: int) -> None:
        self._animations._entering_animation_frame = value

    @property
    def _entering_start_y(self) -> float:
        return self._animations._entering_start_y

    @_entering_start_y.setter
    def _entering_start_y(self, value: float) -> None:
        self._animations._entering_start_y = value

    @property
    def _entering_target_y(self) -> float:
        return self._animations._entering_target_y

    @_entering_target_y.setter
    def _entering_target_y(self, value: float) -> None:
        self._animations._entering_target_y = value

    @property
    def _entering_target_x(self) -> float:
        return self._animations._entering_target_x

    @_entering_target_x.setter
    def _entering_target_x(self, value: float) -> None:
        self._animations._entering_target_x = value

    @property
    def _docking_animation_active(self) -> bool:
        return self._animations._docking_animation_active

    @_docking_animation_active.setter
    def _docking_animation_active(self, value: bool) -> None:
        self._animations._docking_animation_active = value

    @property
    def _docking_animation_start(self):
        return self._animations._docking_animation_start

    @_docking_animation_start.setter
    def _docking_animation_start(self, value) -> None:
        self._animations._docking_animation_start = value

    @property
    def _docking_animation_target(self):
        return self._animations._docking_animation_target

    @_docking_animation_target.setter
    def _docking_animation_target(self, value) -> None:
        self._animations._docking_animation_target = value

    @property
    def _docking_animation_frame(self) -> int:
        return self._animations._docking_animation_frame

    @_docking_animation_frame.setter
    def _docking_animation_frame(self, value: int) -> None:
        self._animations._docking_animation_frame = value

    @property
    def _docking_start_position(self):
        return self._animations._docking_start_position

    @_docking_start_position.setter
    def _docking_start_position(self, value) -> None:
        self._animations._docking_start_position = value

    @property
    def _undocking_animation_active(self) -> bool:
        return self._animations._undocking_animation_active

    @_undocking_animation_active.setter
    def _undocking_animation_active(self, value: bool) -> None:
        self._animations._undocking_animation_active = value

    @property
    def _undocking_animation_start(self):
        return self._animations._undocking_animation_start

    @_undocking_animation_start.setter
    def _undocking_animation_start(self, value) -> None:
        self._animations._undocking_animation_start = value

    @property
    def _undocking_animation_target(self):
        return self._animations._undocking_animation_target

    @_undocking_animation_target.setter
    def _undocking_animation_target(self, value) -> None:
        self._animations._undocking_animation_target = value

    @property
    def _undocking_animation_frame(self) -> int:
        return self._animations._undocking_animation_frame

    @_undocking_animation_frame.setter
    def _undocking_animation_frame(self, value: int) -> None:
        self._animations._undocking_animation_frame = value

    @property
    def _undocking_start_position(self):
        return self._animations._undocking_start_position

    @_undocking_start_position.setter
    def _undocking_start_position(self, value) -> None:
        self._animations._undocking_start_position = value

    @property
    def _undocking_eject_target(self):
        return self._animations._undocking_eject_target

    @_undocking_eject_target.setter
    def _undocking_eject_target(self, value) -> None:
        self._animations._undocking_eject_target = value

    @property
    def _undocking_phase(self) -> int:
        return self._animations._undocking_phase

    @_undocking_phase.setter
    def _undocking_phase(self, value: int) -> None:
        self._animations._undocking_phase = value

    # ── F08: gatling state forwarders ─────────────────────────────────────
    @property
    def _mothership_gatling_timer(self) -> int:
        return self._gatling._mothership_gatling_timer

    @_mothership_gatling_timer.setter
    def _mothership_gatling_timer(self, value: int) -> None:
        self._gatling._mothership_gatling_timer = value

    @property
    def _mothership_gatling_sweep_frame(self) -> int:
        return self._gatling._mothership_gatling_sweep_frame

    @_mothership_gatling_sweep_frame.setter
    def _mothership_gatling_sweep_frame(self, value: int) -> None:
        self._gatling._mothership_gatling_sweep_frame = value

    # ── F08: animation / gatling method forwarders (1-liners) ─────────────
    def _update_entering_animation(self) -> None:
        self._animations.tick_entering()

    def _update_docking_animation(self) -> None:
        self._animations.tick_docking()

    def _update_undocking_animation(self) -> None:
        self._animations.tick_undocking()

    def _update_mothership_gatling(self) -> None:
        self._gatling.tick()

    def _fire_gatling_sweep(self) -> None:
        self._gatling._fire_gatling_sweep()

    def _current_gatling_sweep_angle(self, turret: str | GatlingTurretSpec = "left") -> float:
        return self._gatling._current_gatling_sweep_angle(turret)

    def _get_gatling_turret(self, turret):
        return MothershipGatling._get_gatling_turret(turret)

    # ── Event handler that triggers the entering animation ────────────────
    def _on_start_entering_animation(self, **kwargs) -> None:
        self._animations.start_entering()

    def _on_start_docking_animation(self, **kwargs) -> None:
        self._animations.start_docking()

    def _on_start_undocking_animation(self, **kwargs) -> None:
        self._animations.start_undocking()

    def attach_game_scene(self, game_scene) -> None:
        self._game_scene = game_scene
        self._register_handlers()

    def _register_handlers(self) -> None:
        """F07 god-class split: delegate to MothershipEventHub.

        The 14+ inline subscribe() calls were extracted to
        ``airwar.game.mother_ship.event_hub``. This method is now a
        1-line forwarder for backward compatibility.
        """
        from .event_hub import MothershipEventHub

        MothershipEventHub(self).register_all()

    def _update_mothership_input(self) -> None:
        # Mothership movement is only allowed while docked
        if not self._mother_ship.is_visible() or not self._state_machine.is_docked():
            self._mother_ship.set_player_input(0, 0)
            return

        keys = pygame.key.get_pressed()
        x_input = 0
        y_input = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            x_input = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            x_input = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            y_input = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            y_input = 1

        self._mother_ship.set_player_input(x_input, y_input)

    def update(self) -> None:
        self._update_mothership_input()

        # Run animations without blocking the game loop
        if self._entering_animation_active:
            self._update_entering_animation()

        if self._docking_animation_active:
            self._update_docking_animation()

        if self._undocking_animation_active:
            self._update_undocking_animation()

        # Always update input detector and state machine so the
        # game loop continues running during animations
        self._input_detector.update()
        current_time = pygame.time.get_ticks() / 1000.0
        self._state_machine.update(current_time)
        self._mother_ship.update()

        if self._state_machine.is_docked():
            self._update_mothership_firing()
            self._update_mothership_bullets()
            dock_pos = self._mother_ship.get_docking_position()
            self._game_scene.set_player_position(dock_pos[0], dock_pos[1])
        elif self._state_machine.is_entering():
            self._update_mothership_bullets()

    def _update_mothership_firing(self) -> None:
        if not self._game_scene or not self._game_scene.spawn_controller:
            return

        # Frame-based timing (not delta-time): consistent with other firing logic, assumes stable 60fps.
        # Fire rate drops when framerate drops — an acceptable trade-off.
        self._mothership_fire_timer += 1
        if self._mothership_fire_timer >= self.MOTHERSHIP_FIRE_RATE:
            self._mothership_fire_timer = 0
            self._fire_at_enemies()
        self._update_mothership_gatling()

    def _fire_at_enemies(self) -> None:
        if not self._game_scene:
            return

        mother_ship_pos = self._mother_ship.get_docking_position()
        targets = self._get_mothership_targets()
        if not targets:
            return

        # Sort by distance and target the N closest
        active_enemies = [
            (math.sqrt((e.rect.centerx - mother_ship_pos[0]) ** 2 + (e.rect.centery - mother_ship_pos[1]) ** 2), e)
            for e in targets
        ]
        active_enemies.sort(key=lambda x: x[0])

        for dist, target in active_enemies[: self.MOTHERSHIP_TARGET_COUNT]:
            if dist > 0:
                vx = (target.rect.centerx - mother_ship_pos[0]) / dist * self.MOTHERSHIP_BULLET_SPEED
                vy = (target.rect.centery - mother_ship_pos[1]) / dist * self.MOTHERSHIP_BULLET_SPEED

                bullet = Bullet(
                    mother_ship_pos[0],
                    mother_ship_pos[1],
                    BulletData(
                        damage=self.MOTHERSHIP_BULLET_DAMAGE,
                        speed=self.MOTHERSHIP_BULLET_SPEED,
                        owner="mothership",
                        bullet_type="explosive_missile",
                        is_explosive=True,
                    ),
                )
                bullet.velocity.x = vx
                bullet.velocity.y = vy
                self._mothership_bullets.append(bullet)

    def _get_mothership_targets(self) -> list:
        if not self._game_scene:
            return []

        targets = list(self._game_scene.get_enemies())
        boss = self._game_scene.get_boss()
        if boss:
            targets.append(boss)
        return [target for target in targets if getattr(target, "active", False)]

    def _update_mothership_bullets(self) -> None:
        if not self._game_scene:
            return

        enemies = self._game_scene.get_enemies()
        boss = self._game_scene.get_boss()
        screen_width = get_screen_width()
        screen_height = get_screen_height()

        for bullet in self._mothership_bullets[:]:
            bullet.update()

            if not bullet.active:
                continue

            bullet_damage = bullet.data.damage
            hit = False
            hit_x, hit_y = bullet.rect.centerx, bullet.rect.centery

            for enemy in enemies:
                if not enemy.active:
                    continue
                if bullet.rect.colliderect(self._entity_collision_rect(enemy)):
                    enemy.take_damage(bullet_damage)
                    if not enemy.active:
                        self._on_mothership_kill_enemy(enemy)
                    hit = True
                    break

            if not hit and boss and boss.active and bullet.rect.colliderect(self._entity_collision_rect(boss)):
                boss.take_damage(bullet_damage)
                if not boss.active:
                    self._on_mothership_kill_boss(boss)
                hit = True

            if hit:
                bullet.active = False
                if bullet.data.is_explosive:
                    # Trigger explosion at hit point
                    self._trigger_explosion(hit_x, hit_y)
                    # AoE damage to all nearby enemies
                    self._apply_missile_splash(hit_x, hit_y, enemies, boss)

            margin = self.MOTHERSHIP_BULLET_DESPAWN_MARGIN
            if (
                bullet.rect.x < -margin
                or bullet.rect.x > screen_width + margin
                or bullet.rect.y < -margin
                or bullet.rect.y > screen_height + margin
            ):
                bullet.active = False

        self._mothership_bullets = [b for b in self._mothership_bullets if b.active]

    def _entity_collision_rect(self, entity):
        if hasattr(entity, "get_hitbox"):
            return entity.get_hitbox()
        return entity.rect

    def _trigger_explosion(self, x: float, y: float) -> None:
        """Trigger explosion visual effect at position."""
        if self._game_scene and hasattr(self._game_scene, "trigger_explosion"):
            self._game_scene.trigger_explosion(x, y, self.MOTHERSHIP_EXPLOSION_RADIUS)

    def _apply_missile_splash(self, x: float, y: float, enemies, boss) -> None:
        """Apply AoE damage to enemies within explosion radius."""
        radius_sq = self.MOTHERSHIP_EXPLOSION_RADIUS**2
        explosion_damage = self.MOTHERSHIP_EXPLOSION_DAMAGE

        for enemy in enemies:
            if not enemy.active:
                continue
            dx = x - enemy.rect.centerx
            dy = y - enemy.rect.centery
            if dx * dx + dy * dy <= radius_sq:
                enemy.take_damage(explosion_damage)
                if not enemy.active and self._game_scene:
                    self._game_scene.add_score(self._get_entity_score(enemy, 100) // 3)
                    self._game_scene.add_kill()

        if boss and boss.active:
            dx = x - boss.rect.centerx
            dy = y - boss.rect.centery
            if dx * dx + dy * dy <= radius_sq:
                boss.take_damage(explosion_damage)
                if not boss.active:
                    self._on_mothership_kill_boss(boss)

    def _on_mothership_kill_enemy(self, enemy) -> None:
        if not self._game_scene:
            return

        base_score = getattr(enemy, "score", 100)
        base_score = self._get_entity_score(enemy, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.add_score(reduced_score)
        self._game_scene.add_kill()
        self._game_scene.show_notification(f"+{reduced_score} (mothership)")

    def _on_mothership_kill_boss(self, boss) -> None:
        if not self._game_scene:
            return

        base_score = getattr(boss, "score", 1000)
        base_score = self._get_entity_score(boss, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        # Route through GameController for RP award and difficulty scaling
        gc = getattr(self._game_scene, "game_controller", None)
        if gc:
            gc.on_boss_killed(reduced_score)
        else:
            self._game_scene.add_score(reduced_score)
            self._game_scene.add_boss_kill()
        if hasattr(self._game_scene, "trigger_boss_death_explosion"):
            self._game_scene.trigger_boss_death_explosion(boss)
        self._game_scene.clear_boss()
        self._game_scene.show_notification(f"BOSS +{reduced_score} (mothership)")

    def _on_state_changed(self, state, **kwargs) -> None:
        if state == MotherShipState.PRESSING:
            self._mother_ship.show_phantom()
            self._clear_ripple_effects()
        elif state == MotherShipState.IDLE:
            self._mother_ship.hide_phantom()
            self._mother_ship.hide()
            self._clear_undocking_cooldown_modifier()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.ENTERING:
            self._mother_ship.hide_phantom()
            self._clear_ripple_effects()
        elif state == MotherShipState.COOLDOWN:
            self._mother_ship.hide()
            self._clear_undocking_cooldown_modifier()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.UNDOCKING:
            self._mother_ship.show()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.DOCKED:
            self._mother_ship.show()
            self._player_control_disabled = False
            self._activate_invincibility()
            self._clear_ripple_effects()

    def _activate_invincibility(self) -> None:
        if self._game_scene and hasattr(self._game_scene, "acquire_lock"):
            self._game_scene.acquire_lock(
                LockLayer.MOTHERSHIP,
                LockRequest(
                    invincible=True,
                    lock_controls=True,
                    is_silent_invincible=True,
                    invincibility_duration=GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES,
                ),
            )
        elif self._game_scene:
            if hasattr(self._game_scene, "set_player_invincible"):
                self._game_scene.set_player_invincible(
                    True,
                    GAME_CONSTANTS.PERSISTENCE.DOCKING_INVINCIBILITY_FRAMES,
                    silent=True,
                )
            if getattr(self._game_scene, "player", None):
                self._game_scene.player.is_controls_locked = True

    def _on_cooldown_started(self, **kwargs) -> None:
        self._deactivate_invincibility()

    def _on_stay_started(self, **kwargs) -> None:
        pass

    def _on_undock_requested(self, **kwargs) -> None:
        pass

    def _on_exit_started(self, timestamp=None, **kwargs) -> None:
        self._input_detector.start_exit_hold(timestamp)
        self._progress_bar_ui.show(self.BAR_TYPE_EXIT, getattr(self._input_detector, "_exit_required_duration", 2.0))

    def _on_exit_progress_update(self, progress=None, **kwargs) -> None:
        self._progress_bar_ui.update_progress(progress or 0.0)

    def _on_exit_cancelled(self, **kwargs) -> None:
        self._progress_bar_ui.hide()

    def _deactivate_invincibility(self) -> None:
        if self._game_scene and hasattr(self._game_scene, "release_lock"):
            self._game_scene.release_lock(LockLayer.MOTHERSHIP)
        elif self._game_scene:
            if hasattr(self._game_scene, "set_player_invincible"):
                self._game_scene.set_player_invincible(False, 0, silent=False)
            if getattr(self._game_scene, "player", None):
                self._game_scene.player.is_controls_locked = False

    def _apply_cooldown_multiplier_from_player(self) -> None:
        """Read player's Mothership Recall buff and apply to cooldown."""
        if self._game_scene and self._game_scene.player:
            mult = getattr(self._game_scene.player, "mothership_cooldown_mult", 1.0)
            self._state_machine.cooldown.cooldown_multiplier = mult * self._undocking_cooldown_multiplier

    def _clear_undocking_cooldown_modifier(self) -> None:
        self._undocking_cooldown_multiplier = 1.0

    def _calculate_undocking_cooldown_multiplier(self) -> float:
        stay_progress = 1.0
        if self._state_machine and self._state_machine.stay_progress:
            stay_progress = self._state_machine.stay_progress.stay_progress
        remaining_ratio = max(0.0, min(1.0, 1.0 - stay_progress))
        return max(0.6, 1.0 - remaining_ratio * 0.4)

    def create_save_data(self) -> "GameSaveData":
        if not self._game_scene:
            return GameSaveData()

        is_docked = self._state_machine.current_state == MotherShipState.DOCKED

        sm = self._state_machine
        mothership_state = sm.current_state.value
        cooldown_progress = sm.cooldown.cooldown_progress if sm.current_state == MotherShipState.COOLDOWN else 0.0
        stay_progress = sm.stay_progress.stay_progress if is_docked else 0.0

        player = self._game_scene.player
        return GameSaveData(
            score=self._game_scene.get_score(),
            cycle_count=self._game_scene.get_cycle_count(),
            kill_count=self._game_scene.get_kill_count(),
            boss_kill_count=self._game_scene.get_boss_kill_count(),
            unlocked_buffs=self._game_scene.get_unlocked_buffs(),
            buff_levels=self._get_buff_levels(),
            earned_buff_levels=self._get_earned_buff_levels(),
            talent_loadout=self._get_talent_loadout(),
            player_health=self._game_scene.get_player_health(),
            player_max_health=self._game_scene.get_player_max_health(),
            difficulty=self._game_scene.get_difficulty(),
            player_x=player.rect.x if player else 0,
            player_y=player.rect.y if player else 0,
            is_in_mothership=is_docked,
            mothership_state=mothership_state,
            mothership_cooldown_progress=cooldown_progress,
            mothership_stay_progress=stay_progress,
            username=self._game_scene.get_username(),
            requisition_points=(
                self._game_scene.game_controller.state.requisition_points if self._game_scene.game_controller else 0
            ),
        )

    def _on_game_resume(self, **kwargs) -> None:
        if self._game_scene:
            self._game_scene.set_paused(False)

    def _on_undock_cancelled(self, **kwargs) -> None:
        pass

    def _clear_mothership_bullets(self) -> None:
        self._mothership_bullets.clear()
        self._mothership_fire_timer = 0
        self._gatling.reset_timers()

    def _get_entity_score(self, entity, fallback: int) -> int:
        data = getattr(entity, "data", None)
        return getattr(data, "score", getattr(entity, "score", fallback))

    def _clear_ripple_effects(self) -> None:
        if not self._game_scene:
            return

        self._game_scene.clear_ripple_effects()

    def get_docking_animation_progress(self) -> float:
        if not self._docking_animation_active:
            return 0.0
        return self._docking_animation_frame / self._docking_animation_duration

    def get_docking_animation_start(self) -> tuple:
        return self._docking_start_position if self._docking_start_position else (0, 0)

    def get_undocking_animation_progress(self) -> float:
        if not self._undocking_animation_active:
            return 0.0
        return self._undocking_animation_frame / self._undocking_animation_duration

    def get_undocking_animation_start(self) -> tuple:
        return self._undocking_start_position if self._undocking_start_position else (0, 0)

    def _get_buff_levels(self) -> dict[str, int]:
        if not self._game_scene:
            return {}
        return self._game_scene.get_buff_levels()

    def _get_earned_buff_levels(self) -> dict[str, int]:
        if not self._game_scene or not hasattr(self._game_scene, "get_earned_buff_levels"):
            return self._get_buff_levels()
        return self._game_scene.get_earned_buff_levels()

    def _get_talent_loadout(self) -> dict[str, str]:
        if not self._game_scene or not hasattr(self._game_scene, "get_talent_loadout"):
            return {}
        return self._game_scene.get_talent_loadout()

    def get_status_data(self) -> dict:
        """Return mothership state data for the ammo magazine and warning UI."""
        state = self._state_machine.current_state
        cd = self._state_machine.cooldown
        stay = self._state_machine.stay_progress
        stay.update_stay(pygame.time.get_ticks() / 1000.0)  # Ensure progress is fresh

        # Compute ammo count based on state
        is_present = state in (
            MotherShipState.PRESSING,
            MotherShipState.ENTERING,
            MotherShipState.DOCKING,
            MotherShipState.DOCKED,
            MotherShipState.UNDOCKING,
        )
        is_cooldown = self._state_machine.is_in_cooldown()
        is_docked = state == MotherShipState.DOCKED

        if is_cooldown:
            ammo_count = cd.cooldown_progress * self.AMMO_CELL_COUNT
        elif is_docked:
            ammo_count = (1.0 - stay.stay_progress) * self.AMMO_CELL_COUNT
        elif state in (
            MotherShipState.IDLE,
            MotherShipState.PRESSING,
            MotherShipState.ENTERING,
            MotherShipState.DOCKING,
        ):
            ammo_count = self.AMMO_CELL_COUNT
        else:
            ammo_count = 0.0

        ammo_warning = is_docked and ammo_count <= 4.0

        return {
            "state": state,
            "is_present": is_present,
            "is_in_cooldown": is_cooldown,
            "is_docked": is_docked,
            "cooldown_progress": cd.cooldown_progress,
            "cooldown_remaining": cd.get_remaining_time(),
            "cooldown_duration": cd.cooldown_duration,
            "cooldown_base_duration": cd.BASE_COOLDOWN,
            "cooldown_multiplier": cd.cooldown_multiplier,
            "cooldown_reduction": max(0.0, 1.0 - cd.cooldown_multiplier),
            "hold_progress": (
                self._input_detector.get_progress().current_progress if state == MotherShipState.PRESSING else 0.0
            ),
            "stay_progress": stay.stay_progress,
            "stay_remaining": (
                max(0.0, stay.stay_duration - (pygame.time.get_ticks() / 1000.0 - stay.stay_start_time))
                if stay.is_staying
                else 0.0
            ),
            "stay_duration": stay.stay_duration,
            "ammo_count": ammo_count,
            "ammo_max": self.AMMO_CELL_COUNT,
            "ammo_warning": ammo_warning,
        }

    def render(self, surface) -> None:
        self._mother_ship.render(surface)
        self._render_mothership_bullets(surface)

    def _render_mothership_bullets(self, surface) -> None:
        for bullet in self._mothership_bullets:
            self._entity_renderer.render_bullet(surface, bullet)

    def is_entering_animation_active(self) -> bool:
        return self._entering_animation_active

    def is_docking_animation_active(self) -> bool:
        return self._docking_animation_active

    def is_undocking_animation_active(self) -> bool:
        return self._undocking_animation_active

    def is_docked(self) -> bool:
        return self._state_machine.current_state == MotherShipState.DOCKED

    @property
    def event_bus(self) -> "EventBus":
        """Expose the mothership event bus for external subscribers.

        Callers must not mutate the returned bus's internal
        subscriber lists; they may subscribe to events via the
        public :meth:`EventBus.subscribe` API. The bus is owned by
        the integrator and outlives this property accessor.
        """
        return self._event_bus

    def get_current_state(self) -> MotherShipState:
        """Return the current mothership state machine state."""
        return self._state_machine.current_state

    def is_in_cooldown(self) -> bool:
        return self._state_machine.is_in_cooldown()

    def request_undock(self) -> None:
        """Publish UNDOCK_REQUESTED to the internal event bus."""
        self._event_bus.publish(EVENT_UNDOCK_REQUESTED)

    def is_player_control_disabled(self) -> bool:
        return self._player_control_disabled

    def get_docking_position(self) -> tuple:
        return self._mother_ship.get_docking_position()

    def force_docked_state(self, stay_progress: float = 0.0) -> None:
        self._state_machine.restore_docked_state(stay_progress)
        self._mother_ship.show()
        self._player_control_disabled = False
        self._activate_invincibility()

    def reset_to_idle_with_mothership_visible(self) -> None:
        self._state_machine.force_state(MotherShipState.IDLE)
        self._mother_ship.show()
        self._player_control_disabled = False
        self._input_detector.reset_progress()
        self._event_bus.publish(EVENT_STATE_CHANGED, state=MotherShipState.IDLE)
