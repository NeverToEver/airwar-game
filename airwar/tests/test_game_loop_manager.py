import pytest
from unittest.mock import MagicMock, Mock, patch
from airwar.game.managers.game_loop_manager import GameLoopManager


class TestGameLoopManager:
    def test_creation(self):
        game_controller = MagicMock()
        game_renderer = MagicMock()
        spawn_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        boss_manager = MagicMock()
        collision_controller = MagicMock()

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            bullet_manager,
            boss_manager,
            collision_controller,
        )

        assert manager._game_controller == game_controller
        assert manager._game_renderer == game_renderer
        assert manager._spawn_controller == spawn_controller

    def test_update_entrance_finishes_animation(self):
        game_controller = MagicMock()
        game_controller.state.entrance_animation = True
        game_controller.state.entrance_timer = 60
        game_controller.state.entrance_duration = 60

        manager = GameLoopManager(
            MagicMock(), MagicMock(), MagicMock(),
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        manager._game_controller = game_controller

        player = MagicMock()

        with patch('airwar.game.managers.game_loop_manager.get_screen_height', return_value=600):
            result = manager.update_entrance(player)

        assert result == False
        assert game_controller.state.entrance_animation == False

    def test_update_entrance_in_progress(self):
        game_controller = MagicMock()
        game_controller.state.entrance_animation = True
        game_controller.state.entrance_timer = 30
        game_controller.state.entrance_duration = 60

        manager = GameLoopManager(
            MagicMock(), MagicMock(), MagicMock(),
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        manager._game_controller = game_controller

        player = MagicMock()
        player.rect = MagicMock()
        player.rect.y = 0

        with patch('airwar.game.managers.game_loop_manager.get_screen_width', return_value=800):
            with patch('airwar.game.managers.game_loop_manager.get_screen_height', return_value=600):
                with patch('airwar.game.managers.game_loop_manager.PlayerConstants') as mock_constants:
                    mock_constants.INITIAL_Y = 0
                    mock_constants.SCREEN_BOTTOM_OFFSET = 100
                    mock_constants.INITIAL_X_OFFSET = 50
                    result = manager.update_entrance(player)

        assert result == True

    def test_update_game_calls_core_updates(self):
        game_controller = MagicMock()
        game_controller.state.running = True
        game_controller.update = MagicMock()
        game_renderer = MagicMock()
        game_renderer.update_death_animation = MagicMock()
        spawn_controller = MagicMock()
        reward_system = MagicMock()
        reward_system.unlocked_buffs = []
        bullet_manager = MagicMock()
        boss_manager = MagicMock()
        collision_controller = MagicMock()

        player = MagicMock()
        player.active = True
        player.update = MagicMock()
        player.auto_fire = MagicMock()
        player.cleanup_inactive_bullets = MagicMock()

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            bullet_manager,
            boss_manager,
            collision_controller,
        )

        result = manager.update_game(player)

        assert result == True
        game_controller.update.assert_called_once()
        player.update.assert_called_once()
        player.auto_fire.assert_called_once()
        bullet_manager.update_all.assert_called_once()

    def test_update_game_handles_exception(self):
        game_controller = MagicMock()
        game_controller.state.running = True
        reward_system = MagicMock()
        reward_system.unlocked_buffs = []

        def raise_error(*args):
            raise Exception("Test error")

        game_controller.update = raise_error
        game_renderer = MagicMock()

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            MagicMock(),
            reward_system,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        player = MagicMock()

        result = manager.update_game(player)

        assert result == False
        assert game_controller.state.running == False

    def test_check_collisions_delegates_to_collision_controller(self):
        game_controller = MagicMock()
        game_controller.state.player_invincible = False
        game_controller.state.score_multiplier = 1.0
        game_renderer = MagicMock()
        spawn_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        boss_manager = MagicMock()
        collision_controller = MagicMock()

        player = MagicMock()
        enemy_bullets = [MagicMock()]
        on_player_hit = MagicMock()

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            bullet_manager,
            boss_manager,
            collision_controller,
        )

        manager.check_collisions(player, enemy_bullets, on_player_hit)

        collision_controller.check_all_collisions.assert_called_once()
        call_kwargs = collision_controller.check_all_collisions.call_args[1]
        assert call_kwargs['player'] == player
        assert call_kwargs['enemy_bullets'] == enemy_bullets
        assert call_kwargs['reward_system'] == reward_system

    def test_is_entrance_playing(self):
        game_controller = MagicMock()
        game_controller.state.entrance_animation = True

        manager = GameLoopManager(
            game_controller, MagicMock(), MagicMock(),
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )

        assert manager.is_entrance_playing() == True

        game_controller.state.entrance_animation = False
        assert manager.is_entrance_playing() == False

    def test_is_game_running(self):
        game_controller = MagicMock()
        game_controller.state.running = True

        manager = GameLoopManager(
            game_controller, MagicMock(), MagicMock(),
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )

        assert manager.is_game_running() == True

        game_controller.state.running = False
        assert manager.is_game_running() == False

    def test_update_enemy_spawning_spawns_boss(self):
        game_controller = MagicMock()
        game_controller.state.boss_kill_count = 1
        game_renderer = MagicMock()
        spawn_controller = MagicMock()
        spawn_controller.update.return_value = True
        spawn_controller.spawn_boss.return_value = MagicMock()
        spawn_controller.spawn_boss.return_value.data.escape_time = 120
        game_controller.show_notification = MagicMock()

        reward_system = MagicMock()
        reward_system.slow_factor = 1.0
        reward_system.base_bullet_damage = 10

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        player = MagicMock()

        manager._update_enemy_spawning(player)

        spawn_controller.spawn_boss.assert_called_once_with(1, 10)
        game_controller.show_notification.assert_called_once()

    def test_update_entities(self):
        game_controller = MagicMock()
        game_renderer = MagicMock()
        spawn_controller = MagicMock()

        enemy1 = MagicMock()
        enemy2 = MagicMock()
        spawn_controller.enemies = [enemy1, enemy2]

        reward_system = MagicMock()
        reward_system.slow_factor = 1.0

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

        manager._update_entities()

        enemy1.update.assert_called_once()
        enemy2.update.assert_called_once()

    def test_update_core_stops_game_when_player_inactive(self):
        game_controller = MagicMock()
        game_controller.state.running = True
        game_controller.update = MagicMock()
        game_renderer = MagicMock()
        game_renderer.update_death_animation = MagicMock()
        spawn_controller = MagicMock()
        reward_system = MagicMock()
        reward_system.unlocked_buffs = []
        bullet_manager = MagicMock()
        boss_manager = MagicMock()
        collision_controller = MagicMock()

        player = MagicMock()
        player.active = False
        player.update = MagicMock()
        player.auto_fire = MagicMock()
        player.cleanup_inactive_bullets = MagicMock()

        manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            bullet_manager,
            boss_manager,
            collision_controller,
        )

        manager._update_core(player)

        assert game_controller.state.running == False
