import pytest
from unittest.mock import MagicMock, patch


class TestBulletManager:
    """BulletManager 单元测试"""

    def test_bullet_manager_creation(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        spawn_controller = MagicMock()
        manager = BulletManager(player, spawn_controller)
        assert manager is not None
        assert manager._player is player
        assert manager._spawn_controller is spawn_controller

    def test_update_all_updates_player_bullets(self):
        """Test that update_all updates player bullets when Rust is not available."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        bullet1 = MagicMock()
        bullet2 = MagicMock()
        player.get_bullets.return_value = [bullet1, bullet2]
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []

        # Mock batch_update_bullets to not be available
        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_all()
            bullet1.update.assert_called_once()
            bullet2.update.assert_called_once()

    def test_update_all_updates_enemy_bullets(self):
        """Test that update_all updates enemy bullets when Rust is not available."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        player.get_bullets.return_value = []
        spawn_controller = MagicMock()
        enemy_bullet1 = MagicMock()
        enemy_bullet2 = MagicMock()
        spawn_controller.enemy_bullets = [enemy_bullet1, enemy_bullet2]

        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_all()
            enemy_bullet1.update.assert_called_once()
            enemy_bullet2.update.assert_called_once()

    def test_update_all_without_cleanup_keeps_inactive_bullets(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        inactive_bullet = MagicMock()
        inactive_bullet.active = False
        player.get_bullets.return_value = [inactive_bullet]
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []

        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_all()
            player.remove_bullet.assert_not_called()

    def test_update_with_cleanup_removes_inactive_player_bullets(self):
        """Test cleanup removes inactive player bullets when Rust is not available."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        active_bullet = MagicMock()
        active_bullet.active = True
        inactive_bullet = MagicMock()
        inactive_bullet.active = False
        player.get_bullets.return_value = [active_bullet, inactive_bullet]
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []

        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_with_cleanup()
            player.remove_bullet.assert_called_once_with(inactive_bullet)

    def test_cleanup_removes_inactive_enemy_bullets(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        spawn_controller = MagicMock()
        active_enemy_bullet = MagicMock()
        active_enemy_bullet.active = True
        inactive_enemy_bullet = MagicMock()
        inactive_enemy_bullet.active = False
        spawn_controller.enemy_bullets = [active_enemy_bullet, inactive_enemy_bullet]
        manager = BulletManager(player, spawn_controller)
        manager.cleanup()
        assert spawn_controller.enemy_bullets == [active_enemy_bullet]

    def test_clear_enemy_bullets_deactivates_all_and_clears_list(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        spawn_controller = MagicMock()
        enemy_bullet1 = MagicMock()
        enemy_bullet2 = MagicMock()
        spawn_controller.enemy_bullets = [enemy_bullet1, enemy_bullet2]
        manager = BulletManager(player, spawn_controller)
        manager.clear_enemy_bullets()
        assert enemy_bullet1.active is False
        assert enemy_bullet2.active is False
        assert spawn_controller.enemy_bullets == []

    def test_update_enemy_bullets_with_cleanup(self):
        """Test enemy bullets update with cleanup when Rust is not available."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        player.get_bullets.return_value = []
        spawn_controller = MagicMock()
        active_enemy = MagicMock()
        active_enemy.active = True
        inactive_enemy = MagicMock()
        inactive_enemy.active = False
        spawn_controller.enemy_bullets = [active_enemy, inactive_enemy]

        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_with_cleanup()
            active_enemy.update.assert_called_once()
            inactive_enemy.update.assert_called_once()

    def test_update_with_cleanup_clears_inactive_enemy_bullets(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        player.get_bullets.return_value = []
        spawn_controller = MagicMock()
        active_enemy = MagicMock()
        active_enemy.active = True
        inactive_enemy = MagicMock()
        inactive_enemy.active = False
        spawn_controller.enemy_bullets = [active_enemy, inactive_enemy]

        # Patch to disable Rust for this test
        with patch('airwar.game.managers.bullet_manager.batch_update_bullets', None):
            manager = BulletManager(player, spawn_controller)
            manager.update_with_cleanup()
        assert spawn_controller.enemy_bullets == [active_enemy]

    def test_cleanup_with_no_inactive_bullets_keeps_all(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        spawn_controller = MagicMock()
        bullet1 = MagicMock()
        bullet1.active = True
        bullet2 = MagicMock()
        bullet2.active = True
        spawn_controller.enemy_bullets = [bullet1, bullet2]
        manager = BulletManager(player, spawn_controller)
        manager.cleanup()
        assert len(spawn_controller.enemy_bullets) == 2

    def test_cleanup_with_empty_enemy_bullets(self):
        from airwar.game.managers import BulletManager
        player = MagicMock()
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []
        manager = BulletManager(player, spawn_controller)
        manager.cleanup()
        assert spawn_controller.enemy_bullets == []

    def test_batch_update_with_rust(self):
        """Test that Rust batch update is used when available."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        bullet = MagicMock()
        bullet.active = True
        bullet.velocity.x = 0.0
        bullet.velocity.y = -10.0
        bullet.data.bullet_type = "single"
        bullet.data.is_laser = False
        bullet.rect.x = 100.0
        bullet.rect.y = 100.0
        bullet.rect.width = 10
        bullet.rect.height = 10
        player.get_bullets.return_value = [bullet]
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []

        # Mock Rust function to return controlled result
        with patch('airwar.game.managers.bullet_manager.batch_update_bullets') as mock_batch:
            mock_batch.return_value = [(id(bullet), 100.0, 90.0, True)]
            manager = BulletManager(player, spawn_controller)
            assert manager._use_rust is True

            # Call update
            manager.update_all()

            # Verify Rust was called
            mock_batch.assert_called_once()

            # Verify position was updated
            assert bullet.rect.x == 100.0
            assert bullet.rect.y == 90.0
            assert bullet.active is True

    def test_batch_update_deactivates_off_screen_bullets(self):
        """Test that Rust batch update deactivates off-screen bullets."""
        from airwar.game.managers import BulletManager

        player = MagicMock()
        bullet = MagicMock()
        bullet.active = True
        bullet.velocity.x = 0.0
        bullet.velocity.y = -10.0
        bullet.data.bullet_type = "single"
        bullet.data.is_laser = False
        bullet.rect.x = 100.0
        bullet.rect.y = 100.0
        bullet.rect.width = 10
        bullet.rect.height = 10
        player.get_bullets.return_value = [bullet]
        spawn_controller = MagicMock()
        spawn_controller.enemy_bullets = []

        # Mock Rust function to return bullet as inactive
        with patch('airwar.game.managers.bullet_manager.batch_update_bullets') as mock_batch:
            mock_batch.return_value = [(id(bullet), 100.0, -30.0, False)]
            manager = BulletManager(player, spawn_controller)
            manager.update_all()

            # Bullet should be deactivated by Rust batch update
            assert bullet.active is False
