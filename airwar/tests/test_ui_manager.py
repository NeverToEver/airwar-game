import pytest
from unittest.mock import MagicMock, Mock
from airwar.game.managers.ui_manager import UIManager


class TestUIManager:
    def test_creation(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        assert manager._game_renderer == game_renderer
        assert manager._game_controller == game_controller
        assert manager._reward_system == reward_system

    def test_render_game_creates_entities(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        player = MagicMock()
        enemies = [MagicMock(), MagicMock()]
        boss = MagicMock()
        surface = MagicMock()

        manager.render_game(surface, player, enemies, boss)

        game_renderer.render.assert_called_once()
        call_args = game_renderer.render.call_args
        assert call_args[0][0] == surface
        assert call_args[0][1] == game_controller.state
        assert call_args[0][2].player == player
        assert call_args[0][2].enemies == enemies
        assert call_args[0][2].boss == boss

    def test_render_bullets(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        player = MagicMock()
        player_bullet = MagicMock()
        player.get_bullets.return_value = [player_bullet]

        enemy_bullet = MagicMock()
        enemy_bullets = [enemy_bullet]

        surface = MagicMock()

        manager.render_bullets(surface, player, enemy_bullets)

        player_bullet.render.assert_called_once_with(surface)
        enemy_bullet.render.assert_called_once_with(surface)

    def test_render_hud(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        game_controller.state.score = 1000
        game_controller.state.difficulty = 'hard'
        game_controller.state.kill_count = 50
        game_controller.state.boss_kill_count = 0
        game_controller.get_next_progress.return_value = 50
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        player = MagicMock()
        player.health = 80
        player.max_health = 100

        surface = MagicMock()

        manager.render_hud(surface, player)

        game_renderer.render_hud.assert_called_once()

    def test_render_notification(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        game_controller.state.notification = "BOSS APPROACHING!"
        game_controller.state.notification_timer = 30
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        surface = MagicMock()

        manager.render_notification(surface)

        game_renderer.render_notification.assert_called_once_with(
            surface, "BOSS APPROACHING!", 30
        )

    def test_render_buff_stats_panel(self):
        game_renderer = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()

        manager = UIManager(game_renderer, game_controller, reward_system)

        player = MagicMock()
        surface = MagicMock()

        manager.render_buff_stats_panel(surface, player)

        game_renderer.render_buff_stats_panel.assert_called_once_with(
            surface, reward_system, player
        )
