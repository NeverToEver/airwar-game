from typing import Dict, TYPE_CHECKING
from .mother_ship_state import MotherShipState, GameSaveData

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .input_detector import InputDetector
    from .state_machine import MotherShipStateMachine
    from .persistence_manager import PersistenceManager
    from .progress_bar_ui import ProgressBarUI
    from .mother_ship import MotherShip


class GameIntegrator:
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

    def update(self) -> None:
        if self._docking_animation_active:
            self._update_docking_animation()
            return

        if self._undocking_animation_active:
            self._update_undocking_animation()
            return

        self._input_detector.update()

        if hasattr(self, '_progress_bar_ui') and self._progress_bar_ui:
            progress = self._input_detector.get_progress()
            self._progress_bar_ui.update_progress(progress.current_progress)

    def _on_state_changed(self, state, **kwargs) -> None:
        if state == MotherShipState.PRESSING:
            self._mother_ship.show()
            self._progress_bar_ui.show()
            self._player_control_disabled = False
        elif state == MotherShipState.DOCKING:
            self._mother_ship.show()
            self._progress_bar_ui.hide()
            self._player_control_disabled = True
        elif state == MotherShipState.IDLE:
            self._mother_ship.hide()
            self._progress_bar_ui.hide()
            self._player_control_disabled = False
        elif state == MotherShipState.UNDOCKING:
            self._mother_ship.show()
            self._progress_bar_ui.hide()
            self._player_control_disabled = True
        elif state == MotherShipState.DOCKED:
            self._mother_ship.show()
            self._progress_bar_ui.hide()
            self._player_control_disabled = True

    def _on_save_game_request(self, **kwargs) -> None:
        if not self._game_scene:
            return

        save_data = self.create_save_data()
        if save_data:
            self._persistence_manager.save_game(save_data)

    def create_save_data(self) -> 'GameSaveData':
        if not self._game_scene:
            return GameSaveData()

        is_docked = self._state_machine.current_state == MotherShipState.DOCKED

        return GameSaveData(
            score=self._game_scene.score,
            cycle_count=self._game_scene.cycle_count,
            milestone_index=self._game_scene.milestone_index,
            kill_count=self._game_scene.game_controller.state.kill_count,
            boss_kill_count=self._game_scene.game_controller.state.boss_kill_count,
            unlocked_buffs=self._game_scene.unlocked_buffs,
            buff_levels=self._get_buff_levels(),
            player_health=self._game_scene.player.health,
            player_max_health=self._game_scene.player.max_health,
            player_x=int(self._game_scene.player.rect.x),
            player_y=int(self._game_scene.player.rect.y),
            player_bullet_damage=self._game_scene.player.bullet_damage,
            player_fire_interval=self._game_scene.player.shot_cooldown_frames,
            player_shot_mode=self._game_scene.player.shot_mode,
            player_speed=self._game_scene.player.speed,
            difficulty=self._game_scene.difficulty,
            is_in_mothership=is_docked,
            username=self._game_scene.game_controller.state.username,
        )

    def _on_game_resume(self, **kwargs) -> None:
        if self._game_scene:
            self._game_scene.paused = False
        self._reset_input_state()

    def _on_start_docking_animation(self, **kwargs) -> None:
        if not self._game_scene:
            return

        self._clear_all_enemies()
        self._reset_input_state()

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
        self._reset_input_state()

    def _on_undock_cancelled(self, **kwargs) -> None:
        self._progress_bar_ui.hide()
        self._reset_input_state()

    def _set_player_position(self, x: float, y: float) -> None:
        if not self._game_scene or not self._game_scene.player:
            return
        self._game_scene.player.rect.x = int(x)
        self._game_scene.player.rect.y = int(y)

    def _reset_input_state(self) -> None:
        if self._input_detector:
            self._input_detector.reset()

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

        self._set_player_position(current_x, current_y)

        if progress >= 1.0:
            self._docking_animation_active = False
            self._docking_animation_frame = 0
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

        self._set_player_position(current_x, current_y)

        if progress >= 1.0:
            self._undocking_animation_active = False
            self._undocking_animation_frame = 0
            self._event_bus.publish('UNDOCKING_ANIMATION_COMPLETE')

    def _ease_in_out_cubic(self, t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - ((-2 * t + 2) ** 3) / 2

    def _ease_out_quad(self, t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    def _clear_all_enemies(self) -> None:
        if not self._game_scene:
            return

        if hasattr(self._game_scene, 'spawn_controller') and self._game_scene.spawn_controller:
            self._game_scene.spawn_controller.enemies.clear()
            self._game_scene.spawn_controller.enemy_bullets.clear()
            self._game_scene.spawn_controller.boss = None

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
        self._progress_bar_ui.render(surface)

    def resize(self, screen_width: int, screen_height: int) -> None:
        self._mother_ship.resize(screen_width, screen_height)
        self._progress_bar_ui.resize(screen_width, screen_height)

    def is_docking_animation_active(self) -> bool:
        return self._docking_animation_active

    def is_undocking_animation_active(self) -> bool:
        return self._undocking_animation_active

    def is_docked(self) -> bool:
        return self._state_machine.current_state == MotherShipState.DOCKED

    def is_player_control_disabled(self) -> bool:
        return self._player_control_disabled

    def force_docked_state(self) -> None:
        self.restore_docked_state()

    def restore_docked_state(self) -> None:
        self._state_machine._current_state = MotherShipState.DOCKED
        self._mother_ship.show()
        self._progress_bar_ui.hide()
        self._player_control_disabled = True
        self._docking_animation_active = False
        self._undocking_animation_active = False
        self._reset_input_state()
        docking_x, docking_y = self._mother_ship.get_docking_position()
        self._set_player_position(docking_x, docking_y)
