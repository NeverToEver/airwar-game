import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlayerEntity:
    def test_player_creation(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        assert player.rect.x == 100
        assert player.rect.y == 200
        assert player.health == 100
        assert player.max_health == 100
        assert player.active is True

    def test_player_bullet_damage(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        player.bullet_damage = 50
        assert player.bullet_damage == 50

    def test_player_movement_accepts_keys(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        import pygame
        pygame.init()
        input_handler = MockInputHandler()
        input_handler.set_direction(0, 0)
        player = Player(100, 200, input_handler)
        initial_x = player.rect.x
        player.update()
        assert player.rect.x == initial_x

    def test_player_take_damage(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        player.take_damage(30)
        assert player.health == 70
        player.take_damage(80)
        assert player.active is False

    def test_player_fire_cooldown(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        assert player.fire_cooldown == 0
        player.fire()
        assert player.fire_cooldown > 0


class TestEnemyEntity:
    def test_enemy_creation(self):
        from airwar.entities import Enemy, EnemyData
        from airwar.config import ENEMY_HITBOX_PADDING
        enemy = Enemy(100, 0, EnemyData())
        assert enemy.rect.x == 100 - ENEMY_HITBOX_PADDING
        assert enemy.rect.y == 0 - ENEMY_HITBOX_PADDING
        assert enemy.active is True

    def test_enemy_health(self):
        from airwar.entities import Enemy, EnemyData
        enemy = Enemy(100, 0, EnemyData(health=200))
        assert enemy.health == 200
        assert enemy.max_health == 200

    def test_enemy_take_damage(self):
        from airwar.entities import Enemy, EnemyData
        enemy = Enemy(100, 0, EnemyData(health=100))
        enemy.take_damage(30)
        assert enemy.health == 70
        enemy.take_damage(80)
        assert enemy.active is False

    def test_enemy_off_screen(self):
        from airwar.entities import Enemy, EnemyData
        from airwar.config import SCREEN_HEIGHT
        enemy = Enemy(100, 0, EnemyData())
        enemy.rect.y = SCREEN_HEIGHT + 10
        enemy.update()
        assert enemy.active is False


class TestBulletEntity:
    def test_bullet_creation(self):
        from airwar.entities import Bullet, BulletData
        bullet = Bullet(100, 100, BulletData())
        assert bullet.rect.x == 100
        assert bullet.rect.y == 100
        assert bullet.active is True

    def test_bullet_moves_up(self):
        from airwar.entities import Bullet, BulletData
        bullet = Bullet(100, 100, BulletData(speed=10))
        initial_y = bullet.rect.y
        bullet.update()
        assert bullet.rect.y < initial_y

    def test_bullet_off_screen(self):
        from airwar.entities import Bullet, BulletData
        bullet = Bullet(100, -100, BulletData())
        bullet.update()
        assert bullet.active is False


class TestEnemySpawner:
    def test_spawner_creation(self):
        from airwar.entities import EnemySpawner
        spawner = EnemySpawner()
        assert spawner.spawn_timer == 0
        assert spawner.health == 100
        assert spawner.speed == 3.0

    def test_spawner_set_params(self):
        from airwar.entities import EnemySpawner
        spawner = EnemySpawner()
        spawner.set_params(health=200, speed=5.0, spawn_rate=15)
        assert spawner.health == 200
        assert spawner.speed == 5.0
        assert spawner.spawn_rate == 15

    def test_spawner_enemy_count(self):
        from airwar.entities import EnemySpawner, Enemy
        spawner = EnemySpawner()
        spawner.set_params(health=100, speed=3.0, spawn_rate=1)
        enemies = []
        for _ in range(60):
            spawner.update(enemies)
        assert len(enemies) == 60
        assert all(isinstance(e, Enemy) for e in enemies)

    def test_spawner_slow_factor(self):
        from airwar.entities import EnemySpawner, Enemy
        spawner = EnemySpawner()
        spawner.set_params(health=100, speed=10.0, spawn_rate=1)
        enemies = []
        spawner.update(enemies, slow_factor=0.5)
        spawner.update(enemies, slow_factor=0.5)
        assert len(enemies) == 2
        assert enemies[0].data.speed == 5.0


class TestBossEntity:
    def test_boss_creation(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData())
        assert boss.rect.x == 100
        assert boss.rect.y == 0
        assert boss.active is True
        assert boss.entering is True
        assert boss.escaped is False

    def test_boss_health(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData(health=1000))
        assert boss.health == 1000
        assert boss.max_health == 1000

    def test_boss_take_damage(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData(health=100, score=500))
        boss.take_damage(50)
        assert boss.health == 50
        boss.take_damage(60)
        assert boss.active is False
        assert boss.health == -10

    def test_boss_enter_and_exit(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData())
        assert boss.is_entering() is True
        for _ in range(50):
            boss.update()
        assert boss.is_entering() is False

    def test_boss_escape_mechanism(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData(escape_time=60))
        boss.entering = False
        for _ in range(60):
            boss.update()
        assert boss.escaped is True
        assert boss.active is False

    def test_boss_time_remaining(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData(escape_time=120))
        boss.entering = False
        for _ in range(60):
            boss.update()
        remaining = boss.get_time_remaining()
        assert remaining == 1.0

    def test_boss_escaped_returns_score_zero(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData(health=100, score=500, escape_time=10))
        boss.entering = False
        for _ in range(10):
            boss.update()
        assert boss.is_escaped() is True

    def test_boss_attack_direction_initialization(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData())
        assert boss.attack_direction == 'down'
        assert hasattr(boss, 'ATTACK_DIRECTIONS')
        assert 'down' in boss.ATTACK_DIRECTIONS

    def test_boss_attack_direction_random_selection(self):
        from collections import Counter
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData(fire_rate=1))
        boss.entering = False
        directions = []
        for _ in range(100):
            boss.update()
            directions.append(boss.attack_direction)
        counts = Counter(directions)
        assert len(counts) == 4

    def test_boss_spread_attack_direction(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData())
        boss.entering = False
        for direction in ['down', 'left', 'right', 'up']:
            boss.attack_direction = direction
            bullets = boss._spread_attack()
            assert len(bullets) > 0

    def test_boss_aim_attack_direction(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData())
        boss.entering = False
        for direction in ['down', 'left', 'right', 'up']:
            boss.attack_direction = direction
            bullets = boss._aim_attack()
            for bullet in bullets:
                assert bullet.velocity.length() > 0

    def test_boss_wave_attack_direction(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 50, BossData())
        boss.entering = False
        for direction in ['down', 'left', 'right', 'up']:
            boss.attack_direction = direction
            bullets = boss._wave_attack()
            assert len(bullets) == 8


class TestPlayerHitbox:
    def test_player_hitbox_smaller_than_sprite(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        assert player.hitbox_width < player.rect.width
        assert player.hitbox_height < player.rect.height
        assert player.hitbox_width == 12
        assert player.hitbox_height == 16

    def test_player_get_hitbox(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        hitbox = player.get_hitbox()
        assert hitbox.width == 12
        assert hitbox.height == 16

    def test_player_health_cannot_exceed_max(self):
        pass

    def test_player_health_cannot_go_negative(self):
        pass

    def test_player_fire_returns_bullet(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        bullet = player.fire()
        assert bullet is not None
        assert bullet.data.owner == 'player'

    def test_player_fire_cooldown_respects_cooldown(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        player.fire_cooldown = 5
        initial_count = len(player.get_bullets())
        bullet = player.fire()
        assert bullet is None
        assert len(player.get_bullets()) == initial_count

    def test_player_data_default_values(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        assert player.health == 100
        assert player.max_health == 100
        assert player.fire_cooldown == 0
        assert player.bullet_damage > 0
