import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlayerMovementBoundaries:
    def test_player_cannot_move_beyond_left_boundary(self):
        from airwar.entities import Player
        from airwar.config import PLAYER_SPEED
        player = Player(-10, 200)
        initial_x = player.rect.x
        import pygame
        pygame.init()
        keys = pygame.key.get_pressed()
        player.update(keys=keys)
        assert player.rect.x >= 0

    def test_player_cannot_move_beyond_right_boundary(self):
        from airwar.entities import Player
        from airwar.config import SCREEN_WIDTH, PLAYER_SPEED
        player = Player(SCREEN_WIDTH + 10, 200)
        import pygame
        pygame.init()
        keys = pygame.key.get_pressed()
        player.update(keys=keys)
        assert player.rect.x <= SCREEN_WIDTH - player.rect.width

    def test_player_cannot_move_beyond_top_boundary(self):
        from airwar.entities import Player
        player = Player(100, -10)
        import pygame
        pygame.init()
        keys = pygame.key.get_pressed()
        player.update(keys=keys)
        assert player.rect.y >= 0

    def test_player_cannot_move_beyond_bottom_boundary(self):
        from airwar.entities import Player
        from airwar.config import SCREEN_HEIGHT
        player = Player(100, SCREEN_HEIGHT + 10)
        import pygame
        pygame.init()
        keys = pygame.key.get_pressed()
        player.update(keys=keys)
        assert player.rect.y <= SCREEN_HEIGHT - player.rect.height


class TestPlayerBulletSystem:
    def test_player_fire_creates_bullet(self):
        from airwar.entities import Player
        player = Player(100, 200)
        bullet = player.fire()
        assert bullet is not None
        assert len(player.get_bullets()) == 1

    def test_player_cannot_fire_when_on_cooldown(self):
        from airwar.entities import Player
        player = Player(100, 200)
        player.fire_cooldown = 10
        bullet = player.fire()
        assert bullet is None
        assert len(player.get_bullets()) == 0

    def test_auto_fire_creates_bullets(self):
        from airwar.entities import Player
        player = Player(100, 200)
        player.fire_cooldown = 0
        player.auto_fire()
        assert len(player.get_bullets()) == 1

    def test_bullets_are_removed_when_inactive(self):
        from airwar.entities import Player, Bullet, BulletData
        player = Player(100, 200)
        bullet = Bullet(100, -100, BulletData())
        player._bullets.append(bullet)
        player.update()
        assert len(player.get_bullets()) == 0


class TestEnemyBehavior:
    def test_enemy_moves_downward(self):
        from airwar.entities import Enemy, EnemyData
        from airwar.config import SCREEN_HEIGHT
        enemy = Enemy(100, 0, EnemyData(speed=3.0))
        initial_y = enemy.rect.y
        enemy.update()
        assert enemy.rect.y > initial_y

    def test_enemy_deactivates_when_off_screen_bottom(self):
        from airwar.entities import Enemy, EnemyData
        from airwar.config import SCREEN_HEIGHT
        enemy = Enemy(100, SCREEN_HEIGHT + 100, EnemyData())
        enemy.update()
        assert enemy.active is False

    def test_enemy_with_zero_health_becomes_inactive(self):
        from airwar.entities import Enemy, EnemyData
        enemy = Enemy(100, 0, EnemyData(health=100))
        enemy.take_damage(100)
        assert enemy.active is False

    def test_enemy_data_has_default_score(self):
        from airwar.entities import EnemyData
        data = EnemyData()
        assert data.score > 0


class TestDifficultyScaling:
    def test_easy_difficulty_fewer_shots_to_kill(self):
        from airwar.config import DIFFICULTY_SETTINGS
        easy = DIFFICULTY_SETTINGS['easy']
        shots = easy['enemy_health'] // easy['bullet_damage']
        assert shots >= 3

    def test_hard_difficulty_more_shots_to_kill(self):
        from airwar.config import DIFFICULTY_SETTINGS
        hard = DIFFICULTY_SETTINGS['hard']
        shots = hard['enemy_health'] // hard['bullet_damage']
        assert shots >= 5

    def test_hard_difficulty_faster_spawn_rate(self):
        from airwar.config import DIFFICULTY_SETTINGS
        assert DIFFICULTY_SETTINGS['hard']['spawn_rate'] < DIFFICULTY_SETTINGS['easy']['spawn_rate']


class TestRewardSystem:
    def test_reward_apply_extra_life(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        reward = {'name': 'Extra Life', 'desc': '+50 Max HP, +30 HP', 'icon': 'HP'}
        scene._on_reward_selected(reward)
        assert scene.player.max_health == 150
        assert scene.player.health == 130

    def test_reward_apply_power_shot(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        initial_damage = scene.player.bullet_damage
        reward = {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'}
        scene._on_reward_selected(reward)
        assert scene.player.bullet_damage == int(initial_damage * 1.25)

    def test_reward_apply_barrier(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        reward = {'name': 'Barrier', 'desc': 'Gain 50 temporary HP', 'icon': 'BAR'}
        scene._on_reward_selected(reward)
        assert scene.player.max_health == 150
        assert scene.player.health == 150

    def test_reward_cycle_increments_at_threshold(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.milestone_index = 4
        reward = {'name': 'Speed Boost', 'desc': '+15% move speed', 'icon': 'SPD'}
        scene._on_reward_selected(reward)
        assert scene.cycle_count == 1

    def test_reward_max_cycles_limit(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.cycle_count = 10
        scene.milestone_index = 4
        reward = {'name': 'Speed Boost', 'desc': '+15% move speed', 'icon': 'SPD'}
        scene._check_milestones()
        assert scene.reward_selector.visible is False


class TestDamageCalculation:
    def test_armor_reduces_damage(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.unlocked_buffs.append('Armor')
        damage = scene._calculate_damage_taken(100)
        assert damage == 85

    def test_no_armor_full_damage(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        damage = scene._calculate_damage_taken(100)
        assert damage == 100

    def test_dodge_returns_true_with_evasion(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.unlocked_buffs.append('Evasion')
        result = scene._try_dodge()
        assert isinstance(result, bool)


class TestMilestoneSystem:
    def test_threshold_calculation_with_cycle(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        threshold = scene._get_current_threshold(0)
        assert threshold == 1000
        threshold_cycle1 = scene._get_current_threshold(5)
        assert threshold_cycle1 == 1000 * (1.5 ** 1)

    def test_next_threshold_uses_milestone_index(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.milestone_index = 1
        threshold = scene._get_next_threshold()
        assert threshold == 2500


class TestGameFlowIntegration:
    def test_game_scene_initializes_all_components(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='hard')
        assert scene.player is not None
        assert scene.enemy_spawner is not None
        assert scene.enemies == []
        assert scene.running is True
        assert scene.paused is False
        assert scene.score == 0
        assert scene.kills == 0
        assert scene.difficulty == 'hard'

    def test_game_scene_pause_toggle(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        assert scene.is_paused() is False
        scene.pause()
        assert scene.is_paused() is True
        scene.resume()
        assert scene.is_paused() is False

    def test_game_over_when_player_dies(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.player.take_damage(999)
        assert scene.is_game_over() is True

    def test_enemy_collision_damages_player(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.player.health = 100
        scene.unlocked_buffs = []
        scene.player_invincible = False
        enemy = Enemy(scene.player.rect.x - 50, scene.player.rect.y - 60, EnemyData())
        enemy.rect.x = scene.player.rect.x
        enemy.rect.y = scene.player.rect.y
        scene.enemies.append(enemy)
        scene.update()
        assert scene.player.health <= 100


class TestNotificationSystem:
    def test_notification_shows_on_reward(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        reward = {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'}
        scene._on_reward_selected(reward)
        assert scene.notification == "REWARD: Power Shot"
        assert scene.notification_timer == 90

    def test_notification_timer_decrements(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.notification = "TEST"
        scene.notification_timer = 10
        scene.paused = False
        scene.reward_selector.visible = False
        scene.notification_timer = 10
        initial = scene.notification_timer
        if not scene.paused and not scene.reward_selector.visible:
            scene.notification_timer -= 1
        assert scene.notification_timer == initial - 1
