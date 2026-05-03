"""Core smoke tests — entity lifecycle, collision, buffs, config, game state."""
import pytest
from unittest.mock import MagicMock
import pygame


@pytest.fixture(scope="session", autouse=True)
def _init_pygame():
    pygame.init()
    pygame.display.set_mode((800, 600))
    yield


# ── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_difficulty_settings_present(self):
        from airwar.config import DIFFICULTY_SETTINGS, VALID_DIFFICULTIES
        for d in VALID_DIFFICULTIES:
            s = DIFFICULTY_SETTINGS[d]
            assert s['enemy_health'] > 0
            assert s['bullet_damage'] > 0

    def test_screen_dimensions(self):
        from airwar.config import SCREEN_WIDTH, SCREEN_HEIGHT
        assert SCREEN_WIDTH == 1920
        assert SCREEN_HEIGHT == 1080


# ── Entities ─────────────────────────────────────────────────────────────────

class TestPlayer:
    def test_player_creation(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        ih = PygameInputHandler()
        p = Player(400, 900, ih)
        assert p.health > 0
        assert p.active is True

    def test_player_fires_when_cooldown_ready(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        p = Player(400, 900, PygameInputHandler())
        p._fire_cooldown = 0
        p.auto_fire()
        assert len(p.get_bullets()) == 2

    def test_player_takes_damage(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        p = Player(400, 900, PygameInputHandler())
        initial = p.health
        p.take_damage(20)
        assert p.health == initial - 20

    def test_player_dies_at_zero_health(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        p = Player(400, 900, PygameInputHandler())
        p.take_damage(p.health)
        assert p.health == 0

    def test_player_shield_blocks_damage(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        p = Player(400, 900, PygameInputHandler())
        p.activate_shield(60)
        p.take_damage(50)
        assert p.health == p.max_health


class TestEnemy:
    def test_enemy_creation(self):
        from airwar.entities import Enemy, EnemyData
        e = Enemy(400, 100, EnemyData())
        assert e.active is True
        assert e.health > 0

    def test_enemy_take_damage(self):
        from airwar.entities import Enemy, EnemyData
        e = Enemy(400, 100, EnemyData(health=500))
        e.take_damage(100)
        assert e.health == 400

    def test_enemy_dies(self):
        from airwar.entities import Enemy, EnemyData
        e = Enemy(400, 100, EnemyData(health=100))
        e.take_damage(200)
        assert e.active is False


class TestBoss:
    def test_boss_creation(self):
        from airwar.entities import Boss, BossData
        b = Boss(400, 200, BossData())
        assert b.entering is True
        assert b.health > 0

    def test_boss_take_damage_returns_score(self):
        from airwar.entities import Boss, BossData
        b = Boss(400, 200, BossData(health=1000, score=500))
        score = b.take_damage(100)
        assert score == 0  # not dead yet
        score = b.take_damage(b.health)
        assert score == 500  # score returned on kill
        assert b.active is False

    def test_boss_enter_animation(self):
        from airwar.entities import Boss, BossData
        b = Boss(400, 0, BossData())
        assert b.is_entering() is True
        for _ in range(200):
            b.update()
        assert b.is_entering() is False


class TestBullet:
    def test_bullet_movement(self):
        from airwar.entities import Bullet, BulletData
        b = Bullet(400, 900, BulletData(speed=14))
        b.update()
        assert b.rect.y < 900  # moves upward
        assert b.active is True

    def test_bullet_deactivates_offscreen(self):
        from airwar.entities import Bullet, BulletData
        b = Bullet(400, -100, BulletData(speed=14))
        b.update()
        assert b.active is False


# ── Collision ────────────────────────────────────────────────────────────────

class TestCollision:
    def test_entity_rect_collision(self):
        from airwar.entities.base import Rect
        a = Rect(0, 0, 50, 50)
        b = Rect(25, 25, 50, 50)
        assert a.colliderect(b) is True

    def test_entity_rect_no_collision(self):
        from airwar.entities.base import Rect
        a = Rect(0, 0, 10, 10)
        b = Rect(100, 100, 10, 10)
        assert a.colliderect(b) is False


# ── Buffs ────────────────────────────────────────────────────────────────────

class TestBuffs:
    def test_buff_creation(self):
        from airwar.game.buffs.buff_registry import create_buff
        for name in ['Power Shot', 'Rapid Fire', 'Armor', 'Extra Life', 'Phase Dash']:
            b = create_buff(name)
            assert b is not None
            assert b.get_notification(1) is not None

    def test_reward_pool_structure(self):
        from airwar.game.systems.reward_system import REWARD_POOL
        assert 'health' in REWARD_POOL
        assert 'offense' in REWARD_POOL
        assert 'defense' in REWARD_POOL
        assert len(REWARD_POOL['offense']) >= 3


# ── Game State ───────────────────────────────────────────────────────────────

class TestGameState:
    def test_game_controller_init(self):
        from airwar.game.managers.game_controller import GameController
        gc = GameController('medium', 'TestPlayer')
        assert gc.state.difficulty == 'medium'
        assert gc.state.running is True

    def test_game_state_transitions_to_dying(self):
        from airwar.entities import Player
        from airwar.input import PygameInputHandler
        from airwar.game.managers.game_controller import GameController, GameplayState
        gc = GameController('medium', 'test')
        p = Player(400, 900, PygameInputHandler())
        gc.on_player_hit(p.health, p)
        assert gc.state.gameplay_state == GameplayState.DYING


# ── Reward System ────────────────────────────────────────────────────────────

class TestRewardSystem:
    def test_apply_reward_increases_buff_level(self):
        from airwar.game.systems.reward_system import RewardSystem
        rs = RewardSystem('medium')
        reward = {'name': 'Armor'}
        rs.apply_reward(reward, MagicMock())
        assert rs.buff_levels['Armor'] == 1

    def test_armor_reduces_damage(self):
        from airwar.game.systems.reward_system import RewardSystem
        rs = RewardSystem('medium')
        rs.unlocked_buffs.append('Armor')
        assert rs.calculate_damage_taken(100) == 85  # -15%


# ── Difficulty Manager ───────────────────────────────────────────────────────

class TestDifficultyManager:
    def test_manager_starts_at_base_multiplier(self):
        from airwar.game.systems.difficulty_manager import DifficultyManager
        dm = DifficultyManager('medium')
        assert dm.get_current_multiplier() == 1.0

    def test_boss_kill_increases_multiplier(self):
        from airwar.game.systems.difficulty_manager import DifficultyManager
        dm = DifficultyManager('medium')
        initial = dm.get_current_multiplier()
        dm.on_boss_killed()
        assert dm.get_current_multiplier() > initial
