import pytest
from unittest.mock import Mock, MagicMock, patch
import pygame


class TestGameController:
    def test_game_controller_creation(self):
        from airwar.game.controllers.game_controller import GameController
        from airwar.config import DIFFICULTY_SETTINGS

        settings = DIFFICULTY_SETTINGS['medium']
        controller = GameController('medium', settings)

        assert controller.state.difficulty == 'medium'
        assert controller.state.score == 0

    def test_game_controller_state_paused(self):
        from airwar.game.controllers.game_controller import GameController
        from airwar.config import DIFFICULTY_SETTINGS

        settings = DIFFICULTY_SETTINGS['medium']
        controller = GameController('medium', settings)

        assert controller.state.paused is False
        controller.state.paused = True
        assert controller.state.paused is True


class TestSpawnController:
    def test_spawn_controller_creation(self):
        from airwar.game.controllers.spawn_controller import SpawnController
        from airwar.config import DIFFICULTY_SETTINGS

        settings = DIFFICULTY_SETTINGS['medium']
        controller = SpawnController(settings)

        assert controller.enemies == []
        assert controller.boss is None

    def test_spawn_controller_init_bullet_system(self):
        from airwar.game.controllers.spawn_controller import SpawnController
        from airwar.config import DIFFICULTY_SETTINGS

        settings = DIFFICULTY_SETTINGS['medium']
        controller = SpawnController(settings)
        controller.init_bullet_system()

        assert hasattr(controller, 'enemy_bullets')
        assert isinstance(controller.enemy_bullets, list)


class TestHealthSystem:
    def test_health_system_creation_easy(self):
        from airwar.game.systems.health_system import HealthSystem

        hs = HealthSystem('easy')
        assert hs._difficulty == 'easy'

    def test_health_system_creation_medium(self):
        from airwar.game.systems.health_system import HealthSystem

        hs = HealthSystem('medium')
        assert hs._difficulty == 'medium'

    def test_health_system_creation_hard(self):
        from airwar.game.systems.health_system import HealthSystem

        hs = HealthSystem('hard')
        assert hs._difficulty == 'hard'

    def test_health_system_regen_config_easy(self):
        from airwar.game.systems.health_system import HealthSystem

        hs = HealthSystem('easy')
        config = hs._difficulty_settings['easy']

        assert config['delay'] == 180
        assert config['rate'] == 3
        assert config['interval'] == 45

    def test_health_system_regen_config_medium(self):
        from airwar.game.systems.health_system import HealthSystem

        hs = HealthSystem('medium')
        config = hs._difficulty_settings['medium']

        assert config['delay'] == 240
        assert config['rate'] == 2
        assert config['interval'] == 60


class TestNotificationManager:
    def test_notification_manager_creation(self):
        from airwar.game.systems.notification_manager import NotificationManager

        nm = NotificationManager()
        assert nm.current_notification is None

    def test_notification_manager_show(self):
        from airwar.game.systems.notification_manager import NotificationManager

        nm = NotificationManager()
        nm.show("Test Message", 60)

        assert nm.current_notification == "Test Message"
        assert nm.timer == 60

    def test_notification_manager_update(self):
        from airwar.game.systems.notification_manager import NotificationManager

        nm = NotificationManager()
        nm.show("Test", 60)
        initial_timer = nm.timer

        nm.update()

        assert nm.timer < initial_timer


class TestHUDRenderer:
    def test_hud_renderer_creation(self):
        from airwar.game.systems.hud_renderer import HUDRenderer

        renderer = HUDRenderer()
        assert renderer is not None

    def test_hud_renderer_has_render_method(self):
        from airwar.game.systems.hud_renderer import HUDRenderer

        renderer = HUDRenderer()
        assert hasattr(renderer, 'render_hud')
        assert callable(renderer.render_hud)


class TestInputHandler:
    def test_pygame_input_handler_get_movement_direction(self):
        from airwar.input.input_handler import PygameInputHandler

        handler = PygameInputHandler()
        direction = handler.get_movement_direction()

        assert hasattr(direction, 'x')
        assert hasattr(direction, 'y')
        assert isinstance(direction.x, int)
        assert isinstance(direction.y, int)

    def test_pygame_input_handler_is_pause_pressed(self):
        from airwar.input.input_handler import PygameInputHandler

        handler = PygameInputHandler()
        result = handler.is_pause_pressed()

        assert isinstance(result, bool)

    def test_mock_input_handler(self):
        from airwar.input.input_handler import MockInputHandler

        handler = MockInputHandler()
        direction = handler.get_movement_direction()

        assert hasattr(direction, 'x')
        assert hasattr(direction, 'y')
        assert direction.x == 0
        assert direction.y == 0

    def test_mock_input_handler_pause(self):
        from airwar.input.input_handler import MockInputHandler

        handler = MockInputHandler()
        assert handler.is_pause_pressed() is False


def test_buff_registry_exists():
    from airwar.game.buffs import buff_registry
    assert hasattr(buff_registry, 'BUFF_REGISTRY')


def test_buff_registry_has_buffs():
    from airwar.game.buffs import buff_registry
    assert len(buff_registry.BUFF_REGISTRY) >= 15


def test_create_buff_function():
    from airwar.game.buffs import buff_registry
    from airwar.game.buffs.base_buff import Buff

    buff = buff_registry.create_buff("Power Shot")
    assert isinstance(buff, Buff)


class TestRewardSelector:
    def test_reward_selector_creation(self):
        from airwar.ui.reward_selector import RewardSelector

        selector = RewardSelector()
        assert selector.visible is False

    def test_reward_selector_show_with_params(self):
        from airwar.ui.reward_selector import RewardSelector

        selector = RewardSelector()
        callback = Mock()
        options = [Mock(), Mock(), Mock()]
        selector.show(options, callback)

        assert selector.visible is True
        assert selector.on_select == callback

    def test_reward_selector_hide(self):
        from airwar.ui.reward_selector import RewardSelector

        selector = RewardSelector()
        callback = Mock()
        options = [Mock(), Mock()]
        selector.show(options, callback)
        selector.hide()

        assert selector.visible is False


class TestGameRenderer:
    def test_game_renderer_creation(self):
        from airwar.game.rendering.game_renderer import GameRenderer

        renderer = GameRenderer()
        assert renderer is not None

    def test_game_renderer_has_hud_method(self):
        from airwar.game.rendering.game_renderer import GameRenderer

        renderer = GameRenderer()
        assert hasattr(renderer, 'render_hud')
        assert callable(renderer.render_hud)


class TestEnemyBulletSpawner:
    def test_enemy_bullet_spawner_creation(self):
        from airwar.game.spawners.enemy_bullet_spawner import EnemyBulletSpawner

        bullets = []
        spawner = EnemyBulletSpawner(bullets)

        assert spawner is not None
        assert hasattr(spawner, 'bullet_list')

    def test_enemy_bullet_spawner_get_bullets(self):
        from airwar.game.spawners.enemy_bullet_spawner import EnemyBulletSpawner

        bullets = []
        spawner = EnemyBulletSpawner(bullets)

        result = spawner.get_bullets()
        assert result == bullets