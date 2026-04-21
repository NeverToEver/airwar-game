import pytest
from unittest.mock import MagicMock


class TestBossManager:
    """BossManager 单元测试"""

    def test_boss_manager_creation(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        assert manager is not None
        assert manager._spawn_controller is spawn_controller
        assert manager._game_controller is game_controller
        assert manager._reward_system is reward_system
        assert manager._bullet_manager is bullet_manager

    def test_update_with_no_boss_does_nothing(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        spawn_controller.boss = None
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        player = MagicMock()
        manager.update(player)
        player.rect.centerx.assert_not_called()

    def test_update_calls_boss_update(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        boss = MagicMock()
        spawn_controller.boss = boss
        spawn_controller.enemies = []
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        player = MagicMock()
        player.rect.centerx = 400
        player.rect.centery = 500
        manager.update(player)
        boss.update.assert_called_once()

    def test_handle_boss_escape_shows_notification_when_boss_escaped(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        boss = MagicMock()
        boss.active = False
        boss.is_escaped.return_value = True
        spawn_controller.boss = boss
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        manager._handle_boss_escape(boss)
        game_controller.show_notification.assert_called_once_with("BOSS ESCAPED! (+0)")

    def test_handle_boss_escape_does_nothing_when_boss_active(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        boss = MagicMock()
        boss.active = True
        spawn_controller.boss = boss
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        manager._handle_boss_escape(boss)
        game_controller.show_notification.assert_not_called()

    def test_on_boss_hit_updates_score(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        game_controller = MagicMock()
        game_controller.state.score = 100
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        manager.on_boss_hit(50)
        assert game_controller.state.score == 150
        game_controller.show_notification.assert_called_once_with("+50 BOSS SCORE!")

    def test_on_boss_killed_when_boss_not_active(self):
        from airwar.game.managers import BossManager
        from unittest.mock import PropertyMock
        spawn_controller = MagicMock()
        boss = MagicMock()
        boss.active = False
        boss.data.score = 1000
        spawn_controller.boss = boss
        spawn_controller.player = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        manager.on_boss_hit(50)
        reward_system.apply_lifesteal.assert_called_once()
        bullet_manager.clear_enemy_bullets.assert_called_once()

    def test_on_boss_hit_does_not_trigger_kill_when_boss_still_active(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        boss = MagicMock()
        boss.active = True
        spawn_controller.boss = boss
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        manager.on_boss_hit(50)
        bullet_manager.clear_enemy_bullets.assert_not_called()

    def test_has_boss_returns_true_when_boss_exists(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        spawn_controller.boss = MagicMock()
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        assert manager.has_boss is True

    def test_has_boss_returns_false_when_no_boss(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        spawn_controller.boss = None
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        assert manager.has_boss is False

    def test_boss_property_returns_boss_instance(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        boss = MagicMock()
        spawn_controller.boss = boss
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        assert manager.boss is boss

    def test_boss_property_returns_none_when_no_boss(self):
        from airwar.game.managers import BossManager
        spawn_controller = MagicMock()
        spawn_controller.boss = None
        game_controller = MagicMock()
        reward_system = MagicMock()
        bullet_manager = MagicMock()
        manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        assert manager.boss is None
