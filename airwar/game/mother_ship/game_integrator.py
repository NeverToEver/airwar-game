"""Game integrator — bridges mothership state with game systems."""
from typing import Dict, List, NamedTuple, TYPE_CHECKING
import pygame
import math
from .mother_ship_state import MotherShipState, GameSaveData
from .progress_bar_ui import ProgressBarUI
from .event_bus import (
    EVENT_STATE_CHANGED,
    EVENT_H_RELEASED_EARLY,
    EVENT_ENTERING_COMPLETE,
    EVENT_DOCKING_ANIMATION_COMPLETE,
    EVENT_UNDOCKING_ANIMATION_COMPLETE,
    EVENT_UNDOCK_REQUESTED,
    EVENT_START_ENTERING_ANIMATION,
    EVENT_START_DOCKING_ANIMATION,
    EVENT_UNDOCK_CANCELLED,
    EVENT_START_UNDOCKING_ANIMATION,
    EVENT_COOLDOWN_STARTED,
    EVENT_STAY_STARTED,
    EVENT_GAME_RESUME,
    EVENT_SAVE_GAME_REQUEST,
    EVENT_EXIT_STARTED,
    EVENT_EXIT_PROGRESS_UPDATE,
    EVENT_EXIT_CANCELLED,
)
from airwar.entities.bullet import Bullet
from airwar.entities.base import BulletData
from airwar.config import get_screen_width, get_screen_height

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .input_detector import InputDetector
    from .state_machine import MotherShipStateMachine
    from .persistence_manager import PersistenceManager
    from .mother_ship import MotherShip


class GatlingTurretSpec(NamedTuple):
    name: str
    offset_x: float
    angle_min: float
    angle_max: float
    period: int
    phase_offset: int


class GameIntegrator:
    """Game integrator — bridges mothership state with game systems.
    
        Coordinates between game state and mothership docking flow,
        updating entity states and UI during the docking process.
        """
    MOTHERSHIP_BULLET_DAMAGE = 250
    MOTHERSHIP_FIRE_RATE = 18       # ~3.3 shots/sec at 60fps — heavy missile cadence
    MOTHERSHIP_BULLET_SPEED = 10
    MOTHERSHIP_TARGET_COUNT = 5     # fire at up to 5 closest enemies per volley
    MOTHERSHIP_EXPLOSION_RADIUS = 80
    MOTHERSHIP_EXPLOSION_DAMAGE = 60
    MOTHERSHIP_GATLING_DAMAGE = 24
    MOTHERSHIP_GATLING_FIRE_RATE = 3
    MOTHERSHIP_GATLING_BULLET_SPEED = 18
    MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES = 120
    MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES = 80
    MOTHERSHIP_GATLING_OVERLAP_DEGREES = 40
    MOTHERSHIP_GATLING_SWEEP_PERIOD = 96
    MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD = 108
    MOTHERSHIP_GATLING_BARREL_X_OFFSETS = (-56, 56)
    MOTHERSHIP_GATLING_TURRETS = (
        GatlingTurretSpec(
            "left", MOTHERSHIP_GATLING_BARREL_X_OFFSETS[0],
            -60.0, 20.0, MOTHERSHIP_GATLING_SWEEP_PERIOD, 0
        ),
        GatlingTurretSpec(
            "right", MOTHERSHIP_GATLING_BARREL_X_OFFSETS[1],
            -20.0, 60.0, MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD, 21
        ),
    )
    MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET = -64
    MOTHERSHIP_GATLING_BULLET_TYPE = "mothership_gatling"
    MOTHERSHIP_BULLET_DESPAWN_MARGIN = 80
    AMMO_CELL_COUNT = 10.0

    BAR_TYPE_HOLD = "hold"
    BAR_TYPE_COOLDOWN = "cooldown"
    BAR_TYPE_STAY = "stay"
    BAR_TYPE_EXIT = "exit"

    def __init__(
        self,
        event_bus: 'EventBus',
        input_detector: 'InputDetector',
        state_machine: 'MotherShipStateMachine',
        persistence_manager: 'PersistenceManager',
        progress_bar_ui: 'ProgressBarUI',
        mother_ship: 'MotherShip',
    ):
        self._event_bus = event_bus
        self._input_detector = input_detector
        self._state_machine = state_machine
        self._persistence_manager = persistence_manager
        self._progress_bar_ui = progress_bar_ui
        self._mother_ship = mother_ship

        self._entering_animation_active = False
        self._entering_animation_frame = 0
        self._entering_duration = 75  # ~1.25s fly-in
        self._entering_start_y: float = 0.0
        self._entering_target_y: float = 0.0
        self._entering_target_x: float = 0.0

        self._docking_animation_active = False
        self._docking_animation_start = None
        self._docking_animation_target = None
        self._docking_animation_duration = 90
        self._docking_animation_frame = 0
        self._docking_start_position = None

        self._undocking_animation_active = False
        self._undocking_animation_start = None
        self._undocking_animation_target = None
        self._undocking_animation_frame = 0
        self._undocking_start_position = None
        self._undocking_eject_target = None
        self._undocking_phase = 1
        self._undocking_eject_duration = 30
        self._undocking_flyaway_duration = 90
        self._undocking_cooldown_multiplier = 1.0

        self._game_scene = None
        self._player_control_disabled = False

        self._mothership_bullets: List['Bullet'] = []
        self._mothership_fire_timer = 0
        self._mothership_gatling_timer = 0
        self._mothership_gatling_sweep_frame = 0
        self._score_reduction_factor = 1.0 / 3.0

    def attach_game_scene(self, game_scene) -> None:
        self._game_scene = game_scene
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._event_bus.subscribe(EVENT_STATE_CHANGED, self._on_state_changed)
        self._event_bus.subscribe(EVENT_SAVE_GAME_REQUEST, self._on_save_game_request)
        self._event_bus.subscribe(EVENT_GAME_RESUME, self._on_game_resume)
        self._event_bus.subscribe(EVENT_START_ENTERING_ANIMATION, self._on_start_entering_animation)
        self._event_bus.subscribe(EVENT_START_DOCKING_ANIMATION, self._on_start_docking_animation)
        self._event_bus.subscribe(EVENT_UNDOCK_CANCELLED, self._on_undock_cancelled)
        self._event_bus.subscribe(EVENT_START_UNDOCKING_ANIMATION, self._on_start_undocking_animation)
        self._event_bus.subscribe(EVENT_COOLDOWN_STARTED, self._on_cooldown_started)
        self._event_bus.subscribe(EVENT_STAY_STARTED, self._on_stay_started)
        self._event_bus.subscribe(EVENT_UNDOCK_REQUESTED, self._on_undock_requested)
        self._event_bus.subscribe(EVENT_H_RELEASED_EARLY, self._on_h_released_early)
        self._event_bus.subscribe(EVENT_EXIT_STARTED, self._on_exit_started)
        self._event_bus.subscribe(EVENT_EXIT_PROGRESS_UPDATE, self._on_exit_progress_update)
        self._event_bus.subscribe(EVENT_EXIT_CANCELLED, self._on_exit_cancelled)

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

        # 帧计数而非 delta-time：与项目其他开火逻辑一致，假定稳定 60fps。
        # 帧率下降时开火速度随之下降，可接受的 trade-off。
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
        active_enemies = [(math.sqrt(
            (e.rect.centerx - mother_ship_pos[0]) ** 2 +
            (e.rect.centery - mother_ship_pos[1]) ** 2
        ), e) for e in targets]
        active_enemies.sort(key=lambda x: x[0])

        for dist, target in active_enemies[:self.MOTHERSHIP_TARGET_COUNT]:
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
                    )
                )
                bullet.velocity.x = vx
                bullet.velocity.y = vy
                self._mothership_bullets.append(bullet)

    def _update_mothership_gatling(self) -> None:
        self._mothership_gatling_sweep_frame += 1
        self._mothership_gatling_timer += 1
        if self._mothership_gatling_timer >= self.MOTHERSHIP_GATLING_FIRE_RATE:
            self._mothership_gatling_timer = 0
            self._fire_gatling_sweep()

    def _fire_gatling_sweep(self) -> None:
        if not self._game_scene or not self._get_mothership_targets():
            return

        mother_ship_pos = self._mother_ship.get_docking_position()
        for turret in self.MOTHERSHIP_GATLING_TURRETS:
            angle_rad = math.radians(self._current_gatling_sweep_angle(turret))
            vx = math.sin(angle_rad) * self.MOTHERSHIP_GATLING_BULLET_SPEED
            vy = -math.cos(angle_rad) * self.MOTHERSHIP_GATLING_BULLET_SPEED
            bullet = Bullet(
                mother_ship_pos[0] + turret.offset_x,
                mother_ship_pos[1] + self.MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET,
                BulletData(
                    damage=self.MOTHERSHIP_GATLING_DAMAGE,
                    speed=self.MOTHERSHIP_GATLING_BULLET_SPEED,
                    owner="mothership",
                    bullet_type=self.MOTHERSHIP_GATLING_BULLET_TYPE,
                )
            )
            bullet.rect.width = 6
            bullet.rect.height = 14
            bullet.velocity.x = vx
            bullet.velocity.y = vy
            self._mothership_bullets.append(bullet)

    def _current_gatling_sweep_angle(self, turret: str | GatlingTurretSpec = "left") -> float:
        spec = self._get_gatling_turret(turret)
        period = max(2, spec.period)
        phase = ((self._mothership_gatling_sweep_frame + spec.phase_offset) % period) / period
        sweep_t = phase * 2 if phase <= 0.5 else (1.0 - phase) * 2
        return spec.angle_min + (spec.angle_max - spec.angle_min) * sweep_t

    def _get_gatling_turret(self, turret: str | GatlingTurretSpec) -> GatlingTurretSpec:
        if isinstance(turret, GatlingTurretSpec):
            return turret
        for spec in self.MOTHERSHIP_GATLING_TURRETS:
            if spec.name == turret:
                return spec
        return self.MOTHERSHIP_GATLING_TURRETS[0]

    def _get_mothership_targets(self) -> List:
        if not self._game_scene:
            return []

        targets = list(self._game_scene.get_enemies())
        boss = self._game_scene.get_boss()
        if boss:
            targets.append(boss)
        return [target for target in targets if getattr(target, 'active', False)]

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
        if hasattr(entity, 'get_hitbox'):
            return entity.get_hitbox()
        return entity.rect

    def _trigger_explosion(self, x: float, y: float) -> None:
        """Trigger explosion visual effect at position."""
        if self._game_scene and hasattr(self._game_scene, 'trigger_explosion'):
            self._game_scene.trigger_explosion(x, y, self.MOTHERSHIP_EXPLOSION_RADIUS)

    def _apply_missile_splash(self, x: float, y: float, enemies, boss) -> None:
        """Apply AoE damage to enemies within explosion radius."""
        radius_sq = self.MOTHERSHIP_EXPLOSION_RADIUS ** 2
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

        base_score = getattr(enemy, 'score', 100)
        base_score = self._get_entity_score(enemy, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.add_score(reduced_score)
        self._game_scene.add_kill()
        self._game_scene.show_notification(f"+{reduced_score} (母舰)")

    def _on_mothership_kill_boss(self, boss) -> None:
        if not self._game_scene:
            return

        base_score = getattr(boss, 'score', 1000)
        base_score = self._get_entity_score(boss, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.add_score(reduced_score)
        self._game_scene.add_boss_kill()
        self._game_scene.clear_boss()
        self._game_scene.show_notification(f"BOSS +{reduced_score} (母舰)")

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
        if self._game_scene:
            self._game_scene.set_player_invincible(True, 1200, silent=True)
            if self._game_scene.player:
                self._game_scene.player.controls_locked = True

    def _on_cooldown_started(self, **kwargs) -> None:
        self._deactivate_invincibility()

    def _on_stay_started(self, **kwargs) -> None:
        pass

    def _on_undock_requested(self, **kwargs) -> None:
        pass

    def _on_h_released_early(self, **kwargs) -> None:
        pass

    def _on_exit_started(self, timestamp=None, **kwargs) -> None:
        self._input_detector.start_exit_hold(timestamp)
        self._progress_bar_ui.show(self.BAR_TYPE_EXIT, getattr(self._input_detector, "_exit_required_duration", 2.0))

    def _on_exit_progress_update(self, progress=None, **kwargs) -> None:
        self._progress_bar_ui.update_progress(progress or 0.0)

    def _on_exit_cancelled(self, **kwargs) -> None:
        self._progress_bar_ui.hide()

    def _deactivate_invincibility(self) -> None:
        if self._game_scene:
            self._game_scene.set_player_invincible(False, 0, silent=False)
            if self._game_scene.player:
                self._game_scene.player.controls_locked = False

    def _apply_cooldown_multiplier_from_player(self) -> None:
        """Read player's Mothership Recall buff and apply to cooldown."""
        if self._game_scene and self._game_scene.player:
            mult = getattr(self._game_scene.player, 'mothership_cooldown_mult', 1.0)
            self._state_machine.cooldown.cooldown_multiplier = mult * self._undocking_cooldown_multiplier

    def _clear_undocking_cooldown_modifier(self) -> None:
        self._undocking_cooldown_multiplier = 1.0

    def _calculate_undocking_cooldown_multiplier(self) -> float:
        stay_progress = 1.0
        if self._state_machine and self._state_machine.stay_progress:
            stay_progress = self._state_machine.stay_progress.stay_progress
        remaining_ratio = max(0.0, min(1.0, 1.0 - stay_progress))
        return max(0.6, 1.0 - remaining_ratio * 0.4)

    def _on_save_game_request(self, **kwargs) -> None:
        if not self._game_scene:
            return

        save_data = self.create_save_data()
        self._persistence_manager.save_game(save_data)
        self._game_scene.set_paused(True)

    def create_save_data(self) -> 'GameSaveData':
        if not self._game_scene:
            return GameSaveData()

        is_docked = self._state_machine.current_state == MotherShipState.DOCKED

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
            username=self._game_scene.get_username(),
        )

    def _on_game_resume(self, **kwargs) -> None:
        if self._game_scene:
            self._game_scene.set_paused(False)

    def _on_start_entering_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        target_x = screen_width // 2
        target_y = int(screen_height * 0.35)
        start_y = screen_height + 200

        self._entering_animation_active = True
        self._entering_animation_frame = 0
        self._entering_target_x = target_x
        self._entering_target_y = target_y
        self._entering_start_y = start_y

        self._mother_ship.set_position(target_x, start_y)
        self._mother_ship.show()

    def _on_start_docking_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        self._docking_animation_active = True
        self._docking_animation_frame = 0
        self._docking_start_position = (
            self._game_scene.player.rect.x,
            self._game_scene.player.rect.y,
        )
        # Convert docking bay center to topleft for set_player_position_topleft
        dock_center = self._mother_ship.get_docking_position()
        pw = self._game_scene.player.rect.width
        ph = self._game_scene.player.rect.height
        self._docking_animation_target = (
            dock_center[0] - pw // 2,
            dock_center[1] - ph // 2,
        )
        self._player_control_disabled = True
        self._activate_invincibility()

    def _on_start_undocking_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        self._undocking_animation_active = True
        self._undocking_animation_frame = 0
        self._undocking_phase = 1
        self._undocking_cooldown_multiplier = self._calculate_undocking_cooldown_multiplier()
        self._progress_bar_ui.hide()

        dock_pos = self._mother_ship.get_docking_position()
        # Convert docking position (center) to topleft for player rect
        pw = self._game_scene.player.rect.width
        ph = self._game_scene.player.rect.height
        start_x = dock_pos[0] - pw // 2
        start_y = dock_pos[1] - ph // 2

        self._undocking_start_position = (start_x, start_y)
        # Eject target: backward and downward from the mothership
        self._undocking_eject_target = (start_x, start_y + 140)

        self._player_control_disabled = True

    def _on_undock_cancelled(self, **kwargs) -> None:
        pass

    def _update_entering_animation(self) -> None:
        self._entering_animation_frame += 1
        progress = min(self._entering_animation_frame / self._entering_duration, 1.0)
        eased = self._ease_out_cubic(progress)

        current_y = self._entering_start_y + (self._entering_target_y - self._entering_start_y) * eased
        self._mother_ship.set_position(int(self._entering_target_x), int(current_y))

        # Fire missiles during fly-in for cover
        self._update_mothership_firing()
        self._update_mothership_bullets()

        if progress >= 1.0:
            self._entering_animation_active = False
            self._event_bus.publish(EVENT_ENTERING_COMPLETE)

    def _update_docking_animation(self) -> None:
        if not self._game_scene or not self._docking_start_position:
            self._docking_animation_active = False
            return

        self._docking_animation_frame += 1
        progress = min(self._docking_animation_frame / self._docking_animation_duration, 1.0)

        eased_progress = self._ease_in_out_cubic(progress)

        start_x, start_y = self._docking_start_position
        target_x, target_y = self._docking_animation_target

        current_x = start_x + (target_x - start_x) * eased_progress
        current_y = start_y + (target_y - start_y) * eased_progress

        self._game_scene.set_player_position_topleft(current_x, current_y)

        # Continue firing during docking animation for cover fire
        self._update_mothership_firing()
        self._update_mothership_bullets()

        if progress >= 1.0:
            self._docking_animation_active = False
            self._docking_animation_frame = 0
            self._player_control_disabled = False
            self._event_bus.publish(EVENT_DOCKING_ANIMATION_COMPLETE)

    def _update_undocking_animation(self) -> None:
        if not self._game_scene or not self._undocking_start_position:
            self._undocking_animation_active = False
            return

        self._undocking_animation_frame += 1

        if self._undocking_phase == 1:
            # Phase 1: eject player backward from docking bay
            progress = min(
                self._undocking_animation_frame / self._undocking_eject_duration, 1.0)
            eased = self._ease_out_quad(progress)

            sx, sy = self._undocking_start_position
            tx, ty = self._undocking_eject_target
            cx = sx + (tx - sx) * eased
            cy = sy + (ty - sy) * eased
            self._game_scene.set_player_position_topleft(cx, cy)

            if progress >= 1.0:
                # Phase 1 complete — start mothership flyaway
                self._undocking_animation_frame = 0
                self._undocking_phase = 2
                self._player_control_disabled = False
                self._deactivate_invincibility()
                self._mother_ship.activate_flyaway()

        elif self._undocking_phase == 2:
            # Phase 2: mothership flies away upward; player is free
            # Keep updating mothership so flyaway motion continues
            self._mother_ship.update()

            if not self._mother_ship.is_visible():
                # Mothership has flown off screen — animation complete
                self._undocking_animation_active = False
                self._undocking_animation_frame = 0
                self._undocking_phase = 1
                self._mother_ship.deactivate_flyaway()
                self._apply_cooldown_multiplier_from_player()
                self._event_bus.publish(EVENT_UNDOCKING_ANIMATION_COMPLETE)
                self._clear_undocking_cooldown_modifier()

    def _ease_in_out_cubic(self, t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - ((-2 * t + 2) ** 3) / 2

    def _ease_out_quad(self, t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    def _ease_out_cubic(self, t: float) -> float:
        return 1 - (1 - t) ** 3

    def _clear_mothership_bullets(self) -> None:
        self._mothership_bullets.clear()
        self._mothership_fire_timer = 0
        self._mothership_gatling_timer = 0
        self._mothership_gatling_sweep_frame = 0

    def _get_entity_score(self, entity, fallback: int) -> int:
        data = getattr(entity, 'data', None)
        return getattr(data, 'score', getattr(entity, 'score', fallback))

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

    def _get_buff_levels(self) -> Dict[str, int]:
        if not self._game_scene:
            return {}
        return self._game_scene.get_buff_levels()

    def _get_earned_buff_levels(self) -> Dict[str, int]:
        if not self._game_scene or not hasattr(self._game_scene, "get_earned_buff_levels"):
            return self._get_buff_levels()
        return self._game_scene.get_earned_buff_levels()

    def _get_talent_loadout(self) -> Dict[str, str]:
        if not self._game_scene or not hasattr(self._game_scene, "get_talent_loadout"):
            return {}
        return self._game_scene.get_talent_loadout()

    def get_status_data(self) -> dict:
        """Return mothership state data for the ammo magazine and warning UI."""
        state = self._state_machine.current_state
        cd = self._state_machine.cooldown
        stay = self._state_machine.stay_progress

        # Compute ammo count based on state
        is_present = state in (MotherShipState.PRESSING, MotherShipState.ENTERING,
                               MotherShipState.DOCKING, MotherShipState.DOCKED,
                               MotherShipState.UNDOCKING)
        is_cooldown = self._state_machine.is_in_cooldown()
        is_docked = state == MotherShipState.DOCKED

        if is_cooldown:
            ammo_count = cd.cooldown_progress * self.AMMO_CELL_COUNT
        elif is_docked:
            ammo_count = (1.0 - stay.stay_progress) * self.AMMO_CELL_COUNT
        elif state in (MotherShipState.IDLE, MotherShipState.PRESSING,
                       MotherShipState.ENTERING, MotherShipState.DOCKING):
            ammo_count = self.AMMO_CELL_COUNT
        else:
            ammo_count = 0.0

        ammo_warning = is_docked and ammo_count <= 4.0

        return {
            'state': state,
            'is_present': is_present,
            'is_in_cooldown': is_cooldown,
            'is_docked': is_docked,
            'cooldown_progress': cd.cooldown_progress,
            'cooldown_remaining': cd.get_remaining_time(),
            'cooldown_duration': cd.cooldown_duration,
            'cooldown_base_duration': cd.BASE_COOLDOWN,
            'cooldown_multiplier': cd.cooldown_multiplier,
            'cooldown_reduction': max(0.0, 1.0 - cd.cooldown_multiplier),
            'hold_progress': self._input_detector.get_progress().current_progress if state == MotherShipState.PRESSING else 0.0,
            'stay_progress': stay.stay_progress,
            'stay_remaining': max(0.0, stay.stay_duration - (pygame.time.get_ticks() / 1000.0 - stay.stay_start_time)) if stay.is_staying else 0.0,
            'stay_duration': stay.stay_duration,
            'ammo_count': ammo_count,
            'ammo_max': self.AMMO_CELL_COUNT,
            'ammo_warning': ammo_warning,
        }

    def render(self, surface) -> None:
        self._mother_ship.render(surface)
        self._render_mothership_bullets(surface)

    def _render_mothership_bullets(self, surface) -> None:
        for bullet in self._mothership_bullets:
            bullet.render(surface)

    def is_entering_animation_active(self) -> bool:
        return self._entering_animation_active

    def is_docking_animation_active(self) -> bool:
        return self._docking_animation_active

    def is_undocking_animation_active(self) -> bool:
        return self._undocking_animation_active

    def is_docked(self) -> bool:
        return self._state_machine.current_state == MotherShipState.DOCKED

    def is_in_cooldown(self) -> bool:
        return self._state_machine.is_in_cooldown()

    def request_undock(self) -> None:
        """Publish UNDOCK_REQUESTED to the internal event bus."""
        self._event_bus.publish(EVENT_UNDOCK_REQUESTED)

    def is_player_control_disabled(self) -> bool:
        return self._player_control_disabled

    def get_docking_position(self) -> tuple:
        return self._mother_ship.get_docking_position()

    def force_docked_state(self) -> None:
        self._state_machine.force_state(MotherShipState.DOCKED)
        self._mother_ship.show()
        self._player_control_disabled = False
        self._activate_invincibility()

    def reset_to_idle_with_mothership_visible(self) -> None:
        self._state_machine.force_state(MotherShipState.IDLE)
        self._mother_ship.show()
        self._player_control_disabled = False
        self._input_detector.reset_progress()
        self._event_bus.publish(EVENT_STATE_CHANGED, state=MotherShipState.IDLE)
