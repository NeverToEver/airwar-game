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
    @pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard'])
    def test_health_system_creation(self, difficulty):
        from airwar.game.systems.health_system import HealthSystem
        hs = HealthSystem(difficulty)
        assert hs._difficulty == difficulty

    @pytest.mark.parametrize('difficulty,expected_delay,expected_rate,expected_interval', [
        ('easy', 180, 3, 45),
        ('medium', 240, 2, 60),
        ('hard', 300, 1, 90),
    ])
    def test_health_system_regen_config(self, difficulty, expected_delay, expected_rate, expected_interval):
        from airwar.game.systems.health_system import HealthSystem
        hs = HealthSystem(difficulty)
        config = hs._difficulty_settings[difficulty]
        assert config['delay'] == expected_delay
        assert config['rate'] == expected_rate
        assert config['interval'] == expected_interval


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
