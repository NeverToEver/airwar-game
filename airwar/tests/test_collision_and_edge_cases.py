
import pytest
import pygame


class TestCollisionController:
    def test_collision_controller_creation(self):
        from airwar.game.controllers.collision_controller import CollisionController
        controller = CollisionController()
        assert controller is not None

    def test_check_player_bullets_vs_enemies(self):
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData
        import pygame
        
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
        from airwar.game.controllers.collision_controller import CollisionController
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
        from airwar.game.controllers.collision_controller import CollisionController
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
        from airwar.game.controllers.collision_controller import CollisionController
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
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Enemy, EnemyData
        import pygame
        
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
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData
        import pygame
        
        controller = CollisionController()
        
        class MockPlayer:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayer()
        
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
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Boss, BossData
        import pygame
        
        controller = CollisionController()
        
        class MockPlayer:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayer()
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
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Boss, BossData
        import pygame
        
        controller = CollisionController()
        
        class MockPlayer:
            def __init__(self):
                self.hitbox = pygame.Rect(100, 100, 50, 50)
            def get_hitbox(self):
                return self.hitbox
        
        player = MockPlayer()
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


class TestBoundaryConditions:
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
        assert player.health < 0
        assert player.active is False

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
        threshold = scene._get_current_threshold(0)
        assert threshold == 1500
        
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
        threshold = scene._get_current_threshold(0)
        assert threshold == 1500


class TestExceptionHandling:
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
    def test_empty_enemy_list(self):
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_empty_bullet_list(self):
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Enemy, EnemyData
        
        controller = CollisionController()
        enemy = Enemy(100, 100, EnemyData())
        
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [], [enemy], 1, 0
        )
        
        assert score_gained == 0
        assert enemies_killed == 0

    def test_inactive_bullet(self):
        from airwar.game.controllers.collision_controller import CollisionController
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
        from airwar.game.controllers.collision_controller import CollisionController
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
        from airwar.game.controllers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData
        
        controller = CollisionController()
        bullet = Bullet(100, 100, BulletData(damage=50))
        
        score_gained, boss_killed = controller.check_player_bullets_vs_boss(
            [bullet], None, 0
        )
        
        assert score_gained == 0
        assert boss_killed is False
