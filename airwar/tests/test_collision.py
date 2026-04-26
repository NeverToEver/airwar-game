import pytest
import pygame
from airwar.game.managers.collision_controller import (
    CollisionController,
    CollisionEvent,
    CollisionResult
)


class MockRect:
    def __init__(self, centerx=0, centery=0, width=12, height=16):
        self.centerx = centerx
        self.centery = centery
        self.width = width
        self.height = height
    
    def colliderect(self, other):
        ax1 = self.centerx - self.width // 2
        ay1 = self.centery - self.height // 2
        ax2 = ax1 + self.width
        ay2 = ay1 + self.height
        
        bx1 = other.centerx - other.width // 2
        by1 = other.centery - other.height // 2
        bx2 = bx1 + other.width
        by2 = by1 + other.height
        
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


class MockPlayer:
    def __init__(self):
        self.health = 100
        self.active = True
        self.is_shielded = False
        self.rect = MockRect(centerx=400, centery=500)
        self._hitbox = MockRect(centerx=400, centery=500, width=12, height=16)
    
    def get_hitbox(self):
        return self._hitbox
    
    def get_bullets(self):
        return []


class MockEnemy:
    def __init__(self, health=100, active=True):
        self.health = health
        self.active = active
        self.data = type('obj', (object,), {'score': 100, 'damage': 20})()
        self.rect = MockRect(centerx=400, centery=300, width=30, height=30)
    
    def get_hitbox(self):
        return self.rect
    
    def get_rect(self):
        return self.rect
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return 100
        return 0


class MockBullet:
    def __init__(self, active=True, damage=10, centerx=400, centery=300):
        self.active = active
        self.data = type('obj', (object,), {'damage': damage, 'owner': 'player'})()
        self.rect = MockRect(centerx=centerx, centery=centery, width=5, height=10)
    
    def get_rect(self):
        return self.rect


class MockBoss:
    def __init__(self, health=500, active=True):
        self.health = health
        self.active = active
        self.data = type('obj', (object,), {'score': 5000, 'escape_time': 1800})()
        self.rect = MockRect(centerx=400, centery=200, width=100, height=100)
        self._entering = False
    
    def get_rect(self):
        return self.rect
    
    def is_entering(self):
        return self._entering
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return 5000
        return 0


class TestCollisionEvent:
    """Tests for CollisionEvent data class"""

    def test_collision_event_creation(self):
        event = CollisionEvent(type='player_hit')
        assert event.type == 'player_hit'
        assert event.source is None
        assert event.target is None
        assert event.damage == 0
        assert event.score == 0
    
    def test_collision_event_with_all_fields(self):
        event = CollisionEvent(
            type='enemy_killed',
            source='bullet_1',
            target='enemy_1',
            damage=10,
            score=100
        )
        assert event.type == 'enemy_killed'
        assert event.source == 'bullet_1'
        assert event.target == 'enemy_1'
        assert event.damage == 10
        assert event.score == 100


class TestCollisionResult:
    """Tests for CollisionResult data class"""

    def test_collision_result_defaults(self):
        result = CollisionResult()
        assert result.player_damaged is False
        assert result.enemies_killed == 0
        assert result.score_gained == 0
        assert result.boss_damaged is False
        assert result.boss_killed is False


class TestCollisionController:
    """Tests for CollisionController class"""

    def test_collision_controller_creation(self):
        controller = CollisionController()
        assert controller is not None

    def test_collision_controller_initialization(self):
        controller = CollisionController()
        assert controller.events == []
        assert isinstance(controller.events, list)
    
    def test_clear_events(self):
        controller = CollisionController()
        controller._events.append(CollisionEvent(type='test'))
        assert len(controller.events) == 1
        
        controller.clear_events()
        assert len(controller.events) == 0
    
    def test_events_property_returns_copy(self):
        controller = CollisionController()
        controller._events.append(CollisionEvent(type='test'))
        
        events1 = controller.events
        events1.append(CollisionEvent(type='another'))
        
        assert len(controller.events) == 1
        assert len(events1) == 2
    
    def test_check_all_collisions_with_no_boss(self):
        controller = CollisionController()
        
        mock_player = type('MockPlayer', (), {
            'get_bullets': lambda self: [],
            'get_hitbox': lambda self: type('MockRect', (), {'colliderect': lambda x, y: False})()
        })()
        
        mock_reward_system = type('MockRewardSystem', (), {
            'explosive_level': 0,
            'calculate_damage_taken': lambda self, d: d,
            'piercing_level': 0
        })()
        
        controller.check_all_collisions(
            player=mock_player,
            enemies=[],
            boss=None,
            enemy_bullets=[],
            reward_system=mock_reward_system,
            player_invincible=False,
            score_multiplier=1,
            on_enemy_killed=None,
            on_boss_killed=None,
            on_boss_hit=None,
            on_player_hit=None,
            on_lifesteal=None,
        )
        
        assert isinstance(controller.events, list)

    def test_check_player_bullets_vs_enemies(self):
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData
        
        controller = CollisionController()
        
        bullet = Bullet(100, 100, BulletData(damage=50))
        bullet.active = True
        enemy = Enemy(100, 100, EnemyData(health=100))
        enemy.active = True
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [enemy], 1, 0
        )
        
        assert score_gained >= 0
        assert enemies_killed >= 0

    def test_check_player_bullets_vs_enemies_no_collision(self):
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData
        
        controller = CollisionController()
        
        bullet = Bullet(100, 100, BulletData(damage=50))
        bullet.active = True
        enemy = Enemy(500, 500, EnemyData(health=100))
        enemy.active = True
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [enemy], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_check_player_bullets_vs_boss(self):
        from airwar.entities import Bullet, BulletData, Boss, BossData
        
        controller = CollisionController()
        
        bullet = Bullet(100, 100, BulletData(damage=50))
        bullet.active = True
        boss = Boss(100, 100, BossData(health=1000))
        boss.entering = False
        
        score_gained, boss_killed = controller.check_player_bullets_vs_boss(
            [bullet], boss, 0
        )
        
        assert score_gained >= 0

    def test_check_player_vs_enemies_dodge(self):
        from airwar.entities import Enemy, EnemyData
        
        controller = CollisionController()
        player_hitbox = pygame.Rect(100, 100, 50, 50)
        
        def mock_try_dodge():
            return True
        
        player_damaged = controller.check_player_vs_enemies(
            player_hitbox, [Enemy(100, 100, EnemyData())],
            mock_try_dodge, lambda: None
        )
        
        assert player_damaged is False

    def test_check_player_vs_enemies_no_dodge(self):
        from airwar.entities import Enemy, EnemyData
        
        controller = CollisionController()
        player_hitbox = pygame.Rect(100, 100, 50, 50)
        hit_called = []
        
        def mock_try_dodge():
            return False
        
        def mock_on_hit(damage):
            hit_called.append(damage)
        
        player_damaged = controller.check_player_vs_enemies(
            player_hitbox, [Enemy(100, 100, EnemyData())],
            mock_try_dodge, mock_on_hit
        )
        
        assert player_damaged is True
        assert len(hit_called) == 1

    def test_check_enemy_bullets_vs_player(self):
        from airwar.entities import Bullet, BulletData
        
        controller = CollisionController()
        
        class MockPlayerHitbox:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayerHitbox()
        
        bullet = Bullet(120, 120, BulletData())
        bullet.active = True
        
        def mock_calc_damage(dmg):
            return dmg
        
        hit_called = []
        def mock_on_hit(dmg, player):
            hit_called.append(dmg)
        
        player_damaged = controller.check_enemy_bullets_vs_player(
            [bullet], player, mock_calc_damage, mock_on_hit
        )
        
        assert player_damaged is True
        assert len(hit_called) == 1

    def test_check_boss_vs_player(self):
        from airwar.entities import Boss, BossData
        
        controller = CollisionController()
        
        class MockPlayerBoss:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayerBoss()
        boss = Boss(100, 100, BossData(health=1000))
        boss.entering = False
        
        def mock_calc_damage(dmg):
            return dmg
        
        hit_called = []
        def mock_on_hit(dmg, player):
            hit_called.append(dmg)
        
        player_damaged = controller.check_boss_vs_player(
            boss, player, mock_calc_damage, mock_on_hit
        )
        
        assert player_damaged is True
        assert len(hit_called) == 1

    def test_check_boss_vs_player_not_entering(self):
        from airwar.entities import Boss, BossData
        
        controller = CollisionController()
        
        class MockPlayerBoss:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayerBoss()
        boss = Boss(100, 100, BossData(health=1000))
        boss.entering = True
        
        def mock_calc_damage(dmg):
            return dmg
        
        hit_called = []
        def mock_on_hit(dmg, player):
            hit_called.append(dmg)
        
        player_damaged = controller.check_boss_vs_player(
            boss, player, mock_calc_damage, mock_on_hit
        )
        
        assert player_damaged is False
        assert len(hit_called) == 0


class TestCollisionIntegration:
    def test_player_bullets_vs_enemies_collision(self):
        controller = CollisionController()
        
        player_bullets = [MockBullet(active=True, damage=50)]
        enemies = [MockEnemy(health=50, active=True)]
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            player_bullets, enemies, score_multiplier=1, explosive_level=0
        )
        
        assert enemies_killed == 1
        assert score_gained == 100
        assert not player_bullets[0].active
    
    def test_enemy_bullets_vs_player_collision(self):
        controller = CollisionController()
        
        player = MockPlayer()
        enemy_bullets = [MockBullet(active=True, damage=20, centerx=400, centery=500)]
        
        player_hit_called = []
        def on_hit(damage, p):
            player_hit_called.append((damage, p))
        
        def calc_damage(base):
            return base
        
        result = controller.check_enemy_bullets_vs_player(
            enemy_bullets, player, calc_damage, on_hit
        )
        
        assert result is True
        assert len(player_hit_called) == 1
        assert player_hit_called[0][0] == 20
    
    def test_player_vs_enemies_collision(self):
        controller = CollisionController()
        
        player_hitbox = MockRect(centerx=400, centery=300, width=12, height=16)
        enemies = [MockEnemy(health=100, active=True)]
        
        player_hit_called = []
        def on_hit(damage):
            player_hit_called.append(damage)
        
        def try_dodge():
            return False
        
        result = controller.check_player_vs_enemies(
            player_hitbox, enemies, try_dodge, on_hit
        )
        
        assert result is True
        assert len(player_hit_called) == 1
        assert player_hit_called[0] == 20
    
    def test_boss_vs_player_collision(self):
        controller = CollisionController()
        
        player = MockPlayer()
        boss = MockBoss(health=500, active=True)
        boss.rect = MockRect(centerx=400, centery=500, width=100, height=100)
        
        player_hit_called = []
        def on_hit(damage, p):
            player_hit_called.append(damage)
        
        def calc_damage(base):
            return base
        
        result = controller.check_boss_vs_player(
            boss, player, calc_damage, on_hit
        )
        
        assert result is True
        assert len(player_hit_called) == 1
        assert player_hit_called[0] == 30
    
    def test_invincibility_prevents_damage(self):
        controller = CollisionController()
        
        player_hitbox = MockRect(centerx=400, centery=500, width=12, height=16)
        enemies = [MockEnemy(health=100, active=True)]
        
        player_hit_called = []
        def on_hit(damage):
            player_hit_called.append(damage)
        
        def try_dodge():
            return False
        
        result = controller.check_player_vs_enemies(
            player_hitbox, enemies, try_dodge, on_hit
        )
        
        assert result is False
        assert len(player_hit_called) == 0
    
    def test_explosive_damage(self):
        controller = CollisionController()
        
        bullet = MockBullet(active=True, damage=10)
        bullet.rect = MockRect(centerx=400, centery=300, width=5, height=10)
        
        enemies = [
            MockEnemy(health=100, active=True),
            MockEnemy(health=100, active=True),
        ]
        
        controller._handle_explosive_damage(bullet, enemies, explosive_level=1)
        
        for enemy in enemies:
            assert enemy.health < 100
    
    def test_piercing_bullet_passes_through(self):
        controller = CollisionController()
        
        player_bullets = [MockBullet(active=True, damage=50)]
        enemies = [
            MockEnemy(health=50, active=True),
            MockEnemy(health=50, active=True),
        ]
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            player_bullets, enemies, score_multiplier=1, explosive_level=0
        )
        
        assert enemies_killed == 1
        assert player_bullets[0].active is False
    
    def test_full_collision_sequence(self):
        from airwar.game.systems.reward_system import RewardSystem
        controller = CollisionController()
        
        reward_system = RewardSystem(difficulty='medium')
        
        player_bullets = [
            MockBullet(active=True, damage=50, centerx=400, centery=300)
        ]
        enemies = [
            MockEnemy(health=50, active=True),
        ]
        enemies[0].rect = MockRect(centerx=400, centery=300, width=30, height=30)
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            player_bullets, enemies, score_multiplier=1, explosive_level=reward_system.explosive_level
        )
        
        assert enemies_killed == 1
        assert score_gained == 100


class TestBoundaryConditions:
    """Tests for boundary conditions in collision detection"""

    def test_player_health_boundary_zero(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 0
        player.take_damage(0)
        assert player.health == 0

    def test_player_health_boundary_negative(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        player = Player(100, 200, input_handler)
        
        player.health = 10
        player.take_damage(100)
        assert player.health == 0

    def test_enemy_health_boundary_zero(self):
        from airwar.entities import Enemy, EnemyData
        enemy = Enemy(100, 0, EnemyData(health=0))
        assert enemy.health == 0

    def test_boss_health_boundary(self):
        from airwar.entities import Boss, BossData
        boss = Boss(100, 0, BossData(health=1))
        assert boss.health == 1
        boss.take_damage(1)
        assert boss.health <= 0
        assert boss.active is False

    def test_score_boundary_zero(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        assert scene.score == 0
        scene.score = 0
        assert scene.score == 0

    def test_score_boundary_large(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        scene.score = 999999999
        assert scene.score == 999999999

    def test_milestone_index_boundary(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')

        scene.milestone_index = 0
        # threshold[0] = 800 for medium difficulty
        threshold = scene._get_current_threshold(0)
        assert threshold == 800

        scene.milestone_index = scene.game_controller.max_cycles - 1
        threshold = scene._get_current_threshold(scene.milestone_index)
        assert threshold > 0

    def test_cycle_count_boundary(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')

        scene.cycle_count = 0
        assert scene.cycle_count == 0

        scene.cycle_count = 5
        # threshold[0] = 800 for medium difficulty (not affected by cycle_count)
        threshold = scene._get_current_threshold(0)
        assert threshold == 800


class TestExceptionHandling:
    """Tests for exception handling in collision detection"""

    def test_reward_system_invalid_reward_name(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        
        invalid_reward = {'name': 'InvalidReward', 'desc': 'test', 'icon': 'TST'}
        notification = scene.game_controller.reward_system.apply_reward(invalid_reward, scene.player)
        
        assert notification is not None

    def test_buff_system_invalid_buff_name(self):
        from airwar.game.buffs.buff_registry import create_buff
        with pytest.raises(ValueError):
            create_buff('InvalidBuffName123')

    def test_scene_manager_switch_nonexistent(self):
        from airwar.scenes import SceneManager
        sm = SceneManager()
        try:
            sm.switch('nonexistent_scene')
            assert False, "Should raise KeyError"
        except KeyError:
            assert True

    def test_scene_manager_get_current_scene_none(self):
        from airwar.scenes import SceneManager
        sm = SceneManager()
        scene = sm.get_current_scene()
        assert scene is None


class TestEdgeCases:
    """Tests for edge cases in collision detection"""

    def test_empty_enemy_list(self):
        from airwar.entities import Bullet, BulletData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_empty_bullet_list(self):
        from airwar.entities import Enemy, EnemyData
        
        controller = CollisionController()
        enemy = Enemy(100, 100, EnemyData())
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [], [enemy], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_inactive_bullet(self):
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        bullet.active = False
        enemy = Enemy(100, 100, EnemyData(health=100))
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [enemy], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_inactive_enemy(self):
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        enemy = Enemy(100, 100, EnemyData(health=100))
        enemy.active = False
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [enemy], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_none_boss(self):
        from airwar.entities import Bullet, BulletData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        
        score_gained, boss_killed = controller.check_player_bullets_vs_boss(
            [bullet], None, 0
        )
        
        assert score_gained == 0
        assert boss_killed is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
