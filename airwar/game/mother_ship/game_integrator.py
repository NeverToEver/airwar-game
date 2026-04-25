from typing import Dict, Any, List, TYPE_CHECKING
import pygame
import math
from .mother_ship_state import MotherShipState, GameSaveData
from .progress_bar_ui import ProgressBarUI
from airwar.entities.bullet import Bullet
from airwar.entities.base import BulletData

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .input_detector import InputDetector
    from .state_machine import MotherShipStateMachine
    from .persistence_manager import PersistenceManager
    from .mother_ship import MotherShip


class GameIntegrator:
    MOTHSHIP_BULLET_DAMAGE = 100
    MOTHSHIP_FIRE_RATE = 30
    MOTHSHIP_BULLET_SPEED = 8

    BAR_TYPE_HOLD = "hold"
    BAR_TYPE_COOLDOWN = "cooldown"
    BAR_TYPE_STAY = "stay"

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

        self._docking_animation_active = False
        self._docking_animation_start = None
        self._docking_animation_target = None
        self._docking_animation_duration = 90
        self._docking_animation_frame = 0
        self._docking_start_position = None

        self._undocking_animation_active = False
        self._undocking_animation_start = None
        self._undocking_animation_target = None
        self._undocking_animation_duration = 60
        self._undocking_animation_frame = 0
        self._undocking_start_position = None

        self._game_scene = None
        self._player_control_disabled = False

        self._mothership_bullets: List['Bullet'] = []
        self._mothership_fire_timer = 0
        self._score_reduction_factor = 1.0 / 3.0

    def attach_game_scene(self, game_scene) -> None:
        self._game_scene = game_scene
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._event_bus.subscribe('STATE_CHANGED', self._on_state_changed)
        self._event_bus.subscribe('SAVE_GAME_REQUEST', self._on_save_game_request)
        self._event_bus.subscribe('GAME_RESUME', self._on_game_resume)
        self._event_bus.subscribe('START_DOCKING_ANIMATION', self._on_start_docking_animation)
        self._event_bus.subscribe('UNDOCK_CANCELLED', self._on_undock_cancelled)
        self._event_bus.subscribe('START_UNDOCKING_ANIMATION', self._on_start_undocking_animation)
        self._event_bus.subscribe('COOLDOWN_STARTED', self._on_cooldown_started)
        self._event_bus.subscribe('STAY_STARTED', self._on_stay_started)
        self._event_bus.subscribe('UNDOCK_REQUESTED', self._on_undock_requested)
        self._event_bus.subscribe('H_RELEASED_EARLY', self._on_h_released_early)
        self._event_bus.subscribe('EXIT_STARTED', self._on_exit_started)
        self._event_bus.subscribe('EXIT_PROGRESS_UPDATE', self._on_exit_progress_update)

    def update(self) -> None:
        self._mother_ship.update()

        if self._docking_animation_active:
            self._update_docking_animation()
            return

        if self._undocking_animation_active:
            self._update_undocking_animation()
            return

        self._input_detector.update()

        current_time = pygame.time.get_ticks() / 1000.0
        self._state_machine.update(current_time)

        if self._state_machine.is_docked():
            self._update_mothership_firing()
            self._update_mothership_bullets()
            self._progress_bar_ui.update_progress(
                self._state_machine.stay_progress.stay_progress,
                (1.0 - self._state_machine.stay_progress.stay_progress) * 20.0
            )
        elif self._state_machine.is_in_cooldown():
            self._progress_bar_ui.update_progress(
                self._state_machine.cooldown.cooldown_progress,
                (1.0 - self._state_machine.cooldown.cooldown_progress) * 120.0
            )
        else:
            progress = self._input_detector.get_progress()
            self._progress_bar_ui.update_progress(progress.current_progress)

    def _update_mothership_firing(self) -> None:
        if not self._game_scene or not self._game_scene.spawn_controller:
            return

        self._mothership_fire_timer += 1
        if self._mothership_fire_timer >= self.MOTHSHIP_FIRE_RATE:
            self._mothership_fire_timer = 0
            self._fire_at_enemies()

    def _fire_at_enemies(self) -> None:
        if not self._game_scene:
            return

        mother_ship_pos = self._mother_ship.get_docking_position()

        enemies = []
        if hasattr(self._game_scene, 'spawn_controller') and self._game_scene.spawn_controller:
            enemies = list(self._game_scene.spawn_controller.enemies)
            if self._game_scene.spawn_controller.boss:
                enemies.append(self._game_scene.spawn_controller.boss)

        if not enemies:
            return

        closest_enemy = None
        closest_dist = float('inf')

        for enemy in enemies:
            if not enemy.active:
                continue
            dist = math.sqrt(
                (enemy.rect.centerx - mother_ship_pos[0]) ** 2 +
                (enemy.rect.centery - mother_ship_pos[1]) ** 2
            )
            if dist < closest_dist:
                closest_dist = dist
                closest_enemy = enemy

        if closest_enemy:
            dx = closest_enemy.rect.centerx - mother_ship_pos[0]
            dy = closest_enemy.rect.centery - mother_ship_pos[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                vx = (dx / dist) * self.MOTHSHIP_BULLET_SPEED
                vy = (dy / dist) * self.MOTHSHIP_BULLET_SPEED

                bullet = Bullet(
                    mother_ship_pos[0],
                    mother_ship_pos[1],
                    BulletData(damage=self.MOTHSHIP_BULLET_DAMAGE, owner="mothership")
                )
                bullet.velocity.x = vx
                bullet.velocity.y = vy
                self._mothership_bullets.append(bullet)

    def _update_mothership_bullets(self) -> None:
        if not self._game_scene or not hasattr(self._game_scene, 'spawn_controller'):
            return

        spawn_controller = self._game_scene.spawn_controller
        screen_height = pygame.display.get_surface().get_height()

        for bullet in self._mothership_bullets[:]:
            bullet.update()

            if not bullet.active:
                continue

            bullet_damage = bullet.data.damage

            for enemy in spawn_controller.enemies[:]:
                if not enemy.active:
                    continue
                if bullet.rect.colliderect(enemy.rect):
                    enemy.take_damage(bullet_damage)
                    bullet.active = False
                    if not enemy.active:
                        self._on_mothership_kill_enemy(enemy)
                    break

            if spawn_controller.boss and spawn_controller.boss.active:
                if bullet.rect.colliderect(spawn_controller.boss.rect):
                    spawn_controller.boss.take_damage(bullet_damage)
                    bullet.active = False
                    if not spawn_controller.boss.active:
                        self._on_mothership_kill_boss(spawn_controller.boss)

            if bullet.rect.y < -50 or bullet.rect.y > screen_height + 50:
                bullet.active = False

        self._mothership_bullets = [b for b in self._mothership_bullets if b.active]

    def _on_mothership_kill_enemy(self, enemy) -> None:
        if not self._game_scene:
            return

        base_score = getattr(enemy, 'score', 100)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.game_controller.state.score += reduced_score
        self._game_scene.game_controller.state.kill_count += 1

        if hasattr(self._game_scene, 'notification_manager'):
            self._game_scene.notification_manager.show(f"+{reduced_score} (MOTHERSHIP)")

    def _on_mothership_kill_boss(self, boss) -> None:
        if not self._game_scene:
            return

        base_score = getattr(boss, 'score', 1000)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.game_controller.state.score += reduced_score
        self._game_scene.game_controller.state.boss_kill_count += 1
        self._game_scene.spawn_controller.boss = None

        if hasattr(self._game_scene, 'notification_manager'):
            self._game_scene.notification_manager.show(f"BOSS +{reduced_score} (MOTHERSHIP)")

    def _on_state_changed(self, state, **kwargs) -> None:
        if state == MotherShipState.PRESSING:
            self._mother_ship.show()
            self._progress_bar_ui.show(self.BAR_TYPE_HOLD, 3.0)
            self._clear_ripple_effects()
        elif state == MotherShipState.IDLE:
            self._mother_ship.hide()
            self._progress_bar_ui.hide()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.COOLDOWN:
            self._mother_ship.hide()
            self._progress_bar_ui.show(self.BAR_TYPE_COOLDOWN, 120.0)
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.UNDOCKING:
            self._mother_ship.show()
            self._progress_bar_ui.show(self.BAR_TYPE_HOLD, 2.0)
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.DOCKED:
            self._mother_ship.show()
            self._progress_bar_ui.show(self.BAR_TYPE_STAY, 20.0)
            self._player_control_disabled = False
            self._activate_invincibility()
            self._clear_ripple_effects()

    def _activate_invincibility(self) -> None:
        if self._game_scene and self._game_scene.game_controller:
            self._game_scene.game_controller.state.player_invincible = True
            self._game_scene.game_controller.state.invincibility_timer = 1200

    def _on_cooldown_started(self, **kwargs) -> None:
        self._progress_bar_ui.show(self.BAR_TYPE_COOLDOWN, 120.0)
        self._deactivate_invincibility()

    def _on_stay_started(self, **kwargs) -> None:
        self._progress_bar_ui.show(self.BAR_TYPE_STAY, 20.0)

    def _on_undock_requested(self, **kwargs) -> None:
        self._progress_bar_ui.show(self.BAR_TYPE_HOLD, 2.0)

    def _on_h_released_early(self, **kwargs) -> None:
        if self._state_machine.is_docked():
            self._progress_bar_ui.show(self.BAR_TYPE_STAY, 20.0)

    def _on_exit_started(self, **kwargs) -> None:
        self._progress_bar_ui.show(self.BAR_TYPE_HOLD, 2.0)

    def _on_exit_progress_update(self, progress=None, **kwargs) -> None:
        if self._input_detector:
            exit_progress = self._input_detector.get_exit_progress()
            remaining = (1.0 - exit_progress) * 2.0
            self._progress_bar_ui.update_progress(exit_progress, remaining)

    def _deactivate_invincibility(self) -> None:
        if self._game_scene and self._game_scene.game_controller:
            self._game_scene.game_controller.state.player_invincible = False
            self._game_scene.game_controller.state.invincibility_timer = 0

    def _on_save_game_request(self, **kwargs) -> None:
        if not self._game_scene:
            return

        save_data = self.create_save_data()
        self._persistence_manager.save_game(save_data)
        self._game_scene.paused = True

    def create_save_data(self) -> 'GameSaveData':
        if not self._game_scene:
            return GameSaveData()

        is_docked = self._state_machine.current_state == MotherShipState.DOCKED

        return GameSaveData(
            score=self._game_scene.score,
            cycle_count=self._game_scene.cycle_count,
            kill_count=self._game_scene.game_controller.state.kill_count,
            boss_kill_count=self._game_scene.game_controller.state.boss_kill_count,
            unlocked_buffs=self._game_scene.unlocked_buffs,
            buff_levels=self._get_buff_levels(),
            player_health=self._game_scene.player.health,
            player_max_health=self._game_scene.player.max_health,
            difficulty=self._game_scene.difficulty,
            is_in_mothership=is_docked,
            username=self._game_scene.game_controller.state.username,
        )

    def _on_game_resume(self, **kwargs) -> None:
        if self._game_scene:
            self._game_scene.paused = False

    def _on_start_docking_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        self._docking_animation_active = True
        self._docking_animation_frame = 0
        self._docking_start_position = (self._game_scene.player.rect.x, self._game_scene.player.rect.y)
        self._docking_animation_target = self._mother_ship.get_docking_position()
        self._player_control_disabled = True

    def _on_start_undocking_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        from airwar.config import get_screen_width

        self._undocking_animation_active = True
        self._undocking_animation_frame = 0
        self._undocking_start_position = self._mother_ship.get_docking_position()
        center_x = get_screen_width() // 2
        self._undocking_animation_target = (center_x, 200)
        self._player_control_disabled = True

    def _on_undock_cancelled(self, **kwargs) -> None:
        if self._state_machine.is_in_cooldown():
            self._progress_bar_ui.show(self.BAR_TYPE_COOLDOWN, 120.0)
        elif self._state_machine.is_docked():
            self._progress_bar_ui.show(self.BAR_TYPE_STAY, 20.0)
        else:
            self._progress_bar_ui.hide()

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

        self._game_scene.player.rect.x = current_x
        self._game_scene.player.rect.y = current_y

        if progress >= 1.0:
            self._docking_animation_active = False
            self._docking_animation_frame = 0
            self._player_control_disabled = False
            self._event_bus.publish('DOCKING_ANIMATION_COMPLETE')

    def _update_undocking_animation(self) -> None:
        if not self._game_scene or not self._undocking_start_position:
            self._undocking_animation_active = False
            return

        self._undocking_animation_frame += 1
        progress = min(self._undocking_animation_frame / self._undocking_animation_duration, 1.0)

        eased_progress = self._ease_out_quad(progress)

        start_x, start_y = self._undocking_start_position
        target_x, target_y = self._undocking_animation_target

        current_x = start_x + (target_x - start_x) * eased_progress
        current_y = start_y + (target_y - start_y) * eased_progress

        self._game_scene.player.rect.x = current_x
        self._game_scene.player.rect.y = current_y

        if progress >= 1.0:
            self._undocking_animation_active = False
            self._undocking_animation_frame = 0
            self._player_control_disabled = False
            self._deactivate_invincibility()
            self._event_bus.publish('UNDOCKING_ANIMATION_COMPLETE')

    def _ease_in_out_cubic(self, t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - ((-2 * t + 2) ** 3) / 2

    def _ease_out_quad(self, t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    def _clear_mothership_bullets(self) -> None:
        self._mothership_bullets.clear()
        self._mothership_fire_timer = 0

    def _clear_ripple_effects(self) -> None:
        if not self._game_scene or not self._game_scene.game_controller:
            return

        self._game_scene.game_controller.state.ripple_effects.clear()

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
        if not self._game_scene or not self._game_scene.reward_system:
            return {}
        return {
            'piercing_level': self._game_scene.reward_system.piercing_level,
            'spread_level': self._game_scene.reward_system.spread_level,
            'explosive_level': self._game_scene.reward_system.explosive_level,
            'armor_level': self._game_scene.reward_system.armor_level,
            'evasion_level': self._game_scene.reward_system.evasion_level,
            'rapid_fire_level': self._game_scene.reward_system.rapid_fire_level,
        }

    def render(self, surface) -> None:
        self._mother_ship.render(surface)
        self._render_mothership_bullets(surface)
        self._progress_bar_ui.render(surface)

    def _render_mothership_bullets(self, surface) -> None:
        for bullet in self._mothership_bullets:
            bullet.render(surface)

    def is_docking_animation_active(self) -> bool:
        return self._docking_animation_active

    def is_undocking_animation_active(self) -> bool:
        return self._undocking_animation_active

    def is_docked(self) -> bool:
        return self._state_machine.current_state == MotherShipState.DOCKED

    def is_in_cooldown(self) -> bool:
        return self._state_machine.is_in_cooldown()

    def is_player_control_disabled(self) -> bool:
        return self._player_control_disabled

    def force_docked_state(self) -> None:
        self._state_machine._current_state = MotherShipState.DOCKED
        self._mother_ship.show()
        self._progress_bar_ui.show(self.BAR_TYPE_STAY, 20.0)
        self._player_control_disabled = False
        self._activate_invincibility()

    def reset_to_idle_with_mothership_visible(self) -> None:
        self._state_machine._current_state = MotherShipState.IDLE
        self._mother_ship.show()
        self._progress_bar_ui.show(self.BAR_TYPE_HOLD, 3.0)
        self._player_control_disabled = False
        self._input_detector._progress.reset()
        self._event_bus.publish('STATE_CHANGED', state=MotherShipState.IDLE)
