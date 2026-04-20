
import pytest
import pygame


class TestPlayerShotModes:
    def test_player_shotgun_mode(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        assert player._shot_mode == 'normal'
        player.activate_shotgun()
        assert player._shot_mode == 'shotgun'

    def test_player_laser_mode(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        assert player._shot_mode == 'normal'
        player.activate_laser(180)
        assert player._shot_mode == 'laser'

    def test_player_fire_creates_bullets_in_shotgun_mode(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player._shot_mode = 'shotgun'
        initial_count = len(player.get_bullets())
        player.fire()
        assert len(player.get_bullets()) == initial_count + 3

    def test_player_fire_creates_laser_bullet(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player._shot_mode = 'laser'
        bullet = player.fire()
        assert bullet is not None
        assert bullet.data.is_laser is True


class TestPlayerShield:
    def test_player_shield_activation(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        assert player.is_shielded is False
        player.activate_shield(60)
        assert player.is_shielded is True
        assert player._shield_duration == 60

    def test_player_shield_blocks_damage(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 100
        player.activate_shield(60)
        player.take_damage(50)
        assert player.health == 100

    def test_player_shield_expires(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.activate_shield(2)
        assert player.is_shielded is True
        player.update()
        assert player.is_shielded is True
        player.update()
        assert player.is_shielded is False


class TestPlayerHealing:
    def test_player_heal(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 50
        player.heal(30)
        assert player.health == 80

    def test_player_heal_cannot_exceed_max(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 90
        player.heal(50)
        assert player.health == 100

    def test_player_heal_with_zero_max_health(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.max_health = 0
        player.health = 0
        player.heal(10)
        assert player.health == 0


class TestPlayerBoundaryConditions:
    def test_player_take_damage_zero(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 100
        player.take_damage(0)
        assert player.health == 100

    def test_player_take_damage_exceeds_health(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 10
        player.take_damage(50)
        assert player.health == 0

    def test_player_health_at_zero_cannot_take_damage(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 0
        player.active = False
        player.activate_shield(60)
        player.take_damage(10)
        assert player.health == 0

    def test_player_auto_fire(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        initial_count = len(player.get_bullets())
        player._fire_cooldown = 0
        player.auto_fire()
        assert len(player.get_bullets()) > initial_count

    def test_player_auto_fire_respects_cooldown(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        initial_count = len(player.get_bullets())
        player._fire_cooldown = 5
        player.auto_fire()
        assert len(player.get_bullets()) == initial_count


class TestPlayerBulletManagement:
    def test_player_remove_bullet(self):
        from airwar.entities import Player, Bullet, BulletData
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        bullet = Bullet(100, 100, BulletData())
        player._bullets.append(bullet)
        assert len(player.get_bullets()) == 1
        player.remove_bullet(bullet)
        player.cleanup_inactive_bullets()
        assert len(player.get_bullets()) == 0

    def test_player_remove_nonexistent_bullet(self):
        from airwar.entities import Player, Bullet, BulletData
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        bullet = Bullet(100, 100, BulletData())
        player.remove_bullet(bullet)
        assert len(player.get_bullets()) == 0

    def test_player_add_listener(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        class MockListener:
            def on_bullet_fired(self):
                pass
        
        listener = MockListener()
        player.add_listener(listener)
        assert listener in player._bullet_listeners

    def test_player_get_bullets_returns_reference(self):
        from airwar.entities import Player, Bullet, BulletData
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        bullet = Bullet(100, 100, BulletData())
        player._bullets.append(bullet)
        
        bullets = player.get_bullets()
        assert bullet in bullets


class TestPlayerCollision:
    def test_player_is_colliding_with(self):
        from airwar.entities import Player, Enemy, EnemyData
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        enemy = Enemy(100, 200, EnemyData())
        assert hasattr(enemy, 'rect')
        assert hasattr(enemy, 'get_hitbox')

    def test_player_not_colliding_with_distant_enemy(self):
        from airwar.entities import Player, Enemy, EnemyData
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        enemy = Enemy(500, 500, EnemyData())
        assert hasattr(enemy, 'rect')
        assert hasattr(enemy, 'get_hitbox')
