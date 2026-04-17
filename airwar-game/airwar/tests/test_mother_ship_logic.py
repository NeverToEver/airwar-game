from airwar.game.mother_ship.event_bus import EventBus
from airwar.game.mother_ship.game_integrator import GameIntegrator
from airwar.game.mother_ship.mother_ship_state import GameSaveData, MotherShipState
from airwar.game.mother_ship.state_machine import MotherShipStateMachine


class DummyInputDetector:
    def __init__(self):
        self.reset_called = 0
        self.updated = 0
        self._progress = type('Progress', (), {'current_progress': 0.0})()

    def update(self) -> None:
        self.updated += 1

    def reset(self) -> None:
        self.reset_called += 1
        self._progress.current_progress = 0.0

    def get_progress(self):
        return self._progress


class DummyPersistenceManager:
    def __init__(self):
        self.saved_data = None

    def save_game(self, data):
        self.saved_data = data
        return True


class DummyProgressBarUI:
    def __init__(self):
        self.visible = False
        self.progress = 0.0
        self.size = (0, 0)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def update_progress(self, progress: float) -> None:
        self.progress = progress

    def play_complete_animation(self) -> None:
        pass

    def resize(self, screen_width: int, screen_height: int) -> None:
        self.size = (screen_width, screen_height)

    def render(self, surface) -> None:
        pass


class DummyMotherShip:
    def __init__(self):
        self.visible = False
        self.size = (0, 0)
        self.docking_position = (320, 120)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def resize(self, screen_width: int, screen_height: int) -> None:
        self.size = (screen_width, screen_height)

    def get_docking_position(self) -> tuple:
        return self.docking_position

    def render(self, surface) -> None:
        pass


class DummyPlayer:
    def __init__(self):
        self.rect = type('Rect', (), {'x': 40, 'y': 60})()
        self.health = 88
        self.max_health = 140
        self.bullet_damage = 77
        self.shot_cooldown_frames = 5
        self.shot_mode = 'laser'
        self.speed = 6.5


class DummyRewardSystem:
    def __init__(self):
        self.piercing_level = 2
        self.spread_level = 1
        self.explosive_level = 3
        self.armor_level = 1
        self.evasion_level = 2
        self.rapid_fire_level = 4


class DummyGameState:
    def __init__(self):
        self.kill_count = 13
        self.boss_kill_count = 2
        self.username = 'Pilot'


class DummyGameController:
    def __init__(self):
        self.state = DummyGameState()


class DummySpawnController:
    def __init__(self):
        self.enemies = ['enemy']
        self.enemy_bullets = ['bullet']
        self.boss = 'boss'


class DummyGameScene:
    def __init__(self):
        self.score = 999
        self.cycle_count = 4
        self.milestone_index = 3
        self.unlocked_buffs = ['Laser', 'Armor']
        self.player = DummyPlayer()
        self.reward_system = DummyRewardSystem()
        self.game_controller = DummyGameController()
        self.difficulty = 'hard'
        self.spawn_controller = DummySpawnController()
        self.paused = False


def build_integrator():
    event_bus = EventBus()
    input_detector = DummyInputDetector()
    persistence_manager = DummyPersistenceManager()
    progress_bar_ui = DummyProgressBarUI()
    mother_ship = DummyMotherShip()
    state_machine = MotherShipStateMachine(event_bus)

    integrator = GameIntegrator(
        event_bus=event_bus,
        input_detector=input_detector,
        state_machine=state_machine,
        persistence_manager=persistence_manager,
        progress_bar_ui=progress_bar_ui,
        mother_ship=mother_ship,
    )
    scene = DummyGameScene()
    integrator.attach_game_scene(scene)
    return integrator, scene, input_detector, persistence_manager, progress_bar_ui, mother_ship, state_machine


def test_game_save_data_from_dict_sanitizes_invalid_values():
    save_data = GameSaveData.from_dict({
        'score': '-10',
        'cycle_count': '4',
        'milestone_index': '2',
        'kill_count': '8',
        'boss_kill_count': '1',
        'player_health': '999',
        'player_max_health': '150',
        'player_bullet_damage': '66',
        'player_fire_interval': '0',
        'player_shot_mode': 'invalid',
        'player_speed': '0',
        'difficulty': 'unknown',
        'is_in_mothership': 'false',
        'unlocked_buffs': ['Laser'],
        'buff_levels': {'rapid_fire_level': '3'},
    })

    assert save_data.score == 0
    assert save_data.cycle_count == 4
    assert save_data.milestone_index == 2
    assert save_data.player_health == 150
    assert save_data.player_fire_interval == 1
    assert save_data.player_shot_mode == 'normal'
    assert save_data.player_speed == 1.0
    assert save_data.difficulty == 'medium'
    assert save_data.is_in_mothership is False
    assert save_data.buff_levels['rapid_fire_level'] == 3


def test_state_machine_ignores_h_release_during_undocking():
    event_bus = EventBus()
    state_machine = MotherShipStateMachine(event_bus)

    state_machine._current_state = MotherShipState.DOCKED
    state_machine.transition('H_PRESSED')
    assert state_machine.current_state == MotherShipState.UNDOCKING

    state_machine.transition('H_RELEASED')
    assert state_machine.current_state == MotherShipState.UNDOCKING


def test_game_integrator_create_save_data_captures_runtime_state():
    integrator, scene, _, _, _, _, state_machine = build_integrator()
    state_machine._current_state = MotherShipState.DOCKED

    save_data = integrator.create_save_data()

    assert save_data.score == scene.score
    assert save_data.cycle_count == scene.cycle_count
    assert save_data.milestone_index == scene.milestone_index
    assert save_data.kill_count == scene.game_controller.state.kill_count
    assert save_data.boss_kill_count == scene.game_controller.state.boss_kill_count
    assert save_data.player_bullet_damage == scene.player.bullet_damage
    assert save_data.player_fire_interval == scene.player.shot_cooldown_frames
    assert save_data.player_shot_mode == scene.player.shot_mode
    assert save_data.player_speed == scene.player.speed
    assert save_data.is_in_mothership is True


def test_game_integrator_restore_docked_state_syncs_player_and_control():
    integrator, scene, input_detector, _, progress_bar_ui, mother_ship, state_machine = build_integrator()

    integrator.restore_docked_state()

    assert state_machine.current_state == MotherShipState.DOCKED
    assert mother_ship.visible is True
    assert progress_bar_ui.visible is False
    assert integrator.is_player_control_disabled() is True
    assert (scene.player.rect.x, scene.player.rect.y) == mother_ship.get_docking_position()
    assert input_detector.reset_called == 1


def test_game_integrator_clears_spawn_controller_boss_without_property_assignment():
    integrator, scene, _, _, _, _, _ = build_integrator()

    integrator._clear_all_enemies()

    assert scene.spawn_controller.enemies == []
    assert scene.spawn_controller.enemy_bullets == []
    assert scene.spawn_controller.boss is None
