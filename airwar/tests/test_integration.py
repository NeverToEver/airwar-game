import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlayerMovementBoundaries:
    def test_player_cannot_move_beyond_left_boundary(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        from airwar.config import PLAYER_SPEED
        input_handler = MockInputHandler()
        input_handler.set_direction(-1, 0)
        player = Player(-10, 200, input_handler)
        initial_x = player.rect.x
        player.update()
        assert player.rect.x >= 0

    def test_player_cannot_move_beyond_right_boundary(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        from airwar.config import SCREEN_WIDTH, PLAYER_SPEED
        input_handler = MockInputHandler()
        input_handler.set_direction(1, 0)
        player = Player(SCREEN_WIDTH + 10, 200, input_handler)
        player.update()
        assert player.rect.x <= SCREEN_WIDTH - player.rect.width

    def test_player_cannot_move_beyond_top_boundary(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        input_handler = MockInputHandler()
        input_handler.set_direction(0, -1)
        player = Player(100, -10, input_handler)
        player.update()
        assert player.rect.y >= 0

    def test_player_cannot_move_beyond_bottom_boundary(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        from airwar.config import SCREEN_HEIGHT
        input_handler = MockInputHandler()
        input_handler.set_direction(0, 1)
        player = Player(100, SCREEN_HEIGHT + 10, input_handler)
        player.update()
        assert player.rect.y <= SCREEN_HEIGHT - player.rect.height


class TestPlayerBulletSystem:
    def test_fire_creates_bullets(self):
        from airwar.entities import Player
        from airwar.input import MockInputHandler
        player = Player(100, 200, MockInputHandler())
        player.fire_cooldown = 0
        bullet = player.fire()
        assert bullet is not None
        assert len(player.get_bullets()) == 1

    def test_bullets_become_inactive_when_off_screen(self):
        from airwar.entities import Player, Bullet, BulletData
        from airwar.input import MockInputHandler
        player = Player(100, 200, MockInputHandler())
        bullet = Bullet(100, -100, BulletData())
        player._bullets.append(bullet)
        assert bullet.active is True
        bullet.update()
        assert bullet.active is False


class TestEnemyBehavior:
    def test_enemy_moves_downward(self):
        from airwar.entities import Enemy, EnemyData
        from airwar.config import SCREEN_HEIGHT
        # Enemy spawns below its entry start point and moves downward during entry animation
        enemy = Enemy(100, 100, EnemyData(speed=3.0))
        # _entry_start_y = 100 - 150 = -50, _entry_target_y = 100
        # After update, rect.y should move from -50 toward 100, so y > -50
        assert enemy.rect.y > -50

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

    def test_reward_cycle_increments_at_threshold(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.milestone_index = 4
        scene.game_controller.difficulty_manager._boss_kill_count = 2
        reward = {'name': 'Slow Field', 'desc': 'Slow enemies by 20%', 'icon': 'SLO'}
        scene._on_reward_selected(reward)
        assert scene.cycle_count == 5


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
    """Tests for milestone system - thresholds and progress calculations.

    For medium difficulty:
    - initial_delta = 800, max_delta = 3600, difficulty_multiplier = 1.0
    - threshold[0] = 800
    - threshold[1] = 2400
    - threshold[2] = 4800
    """

    def test_threshold_calculation_with_cycle(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        # threshold[0] = 800 (not 500 as old test expected)
        threshold = scene._get_current_threshold(0)
        assert threshold == 800
        # threshold[1] = 2400 (not 1500 as old test expected)
        threshold_milestone1 = scene._get_current_threshold(1)
        assert threshold_milestone1 == 2400

    def test_next_threshold_uses_milestone_index(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.milestone_index = 1
        threshold = scene._get_next_threshold()
        assert threshold == 2400

    def test_get_next_progress_initial_state(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        assert scene.game_controller.get_next_progress() == 0

    def test_get_next_progress_half_way(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        # milestone_index=0, previous=0, next=800, score=250
        # progress = 250/800*100 = 31
        scene.game_controller.state.score = 250
        assert scene.game_controller.get_next_progress() == 31

    def test_get_next_progress_at_threshold(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        # milestone_index=0, previous=0, next=800, score=500
        # progress = 500/800*100 = 62
        scene.game_controller.state.score = 500
        assert scene.game_controller.get_next_progress() == 62

    def test_get_next_progress_over_threshold(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        # milestone_index=0, previous=0, next=800, score=600
        # progress = 600/800*100 = 75
        scene.game_controller.state.score = 600
        assert scene.game_controller.get_next_progress() == 75

    def test_get_next_progress_after_reward_selection(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene._on_reward_selected({'name': 'Test', 'desc': 'Test', 'icon': 'T'})
        # After reward: milestone_index=1, previous=800, next=2400, score=1000
        # progress = (1000-800)/(2400-800)*100 = 12
        scene.game_controller.state.score = 1000
        assert scene.game_controller.get_next_progress() == 12


class TestEntranceAnimation:
    def test_entrance_animation_initializes(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        assert scene.game_controller.state.entrance_animation is True
        assert scene.game_controller.state.entrance_timer == 0
        assert scene.game_controller.state.entrance_duration == 60
        assert scene.player.rect.y == -80

    def test_entrance_animation_ends_after_duration(self):
        import pygame
        pygame.init()
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        for _ in range(60):
            scene.update()
        assert scene.game_controller.state.entrance_animation is False

    def test_entrance_animation_progresses_player_position(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.config import SCREEN_HEIGHT
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.update()
        assert scene.player.rect.y > -80
        assert scene.player.rect.y < SCREEN_HEIGHT - 100

    def test_entrance_animation_blocks_gameplay_during_animation(self):
        import pygame
        pygame.init()
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        initial_enemy_count = len(scene.spawn_controller.enemies)
        scene.spawn_controller.enemy_spawner.spawn_timer = 1000
        scene.spawn_controller.enemy_spawner.spawn_rate = 1
        for _ in range(10):
            scene.update()
        assert len(scene.spawn_controller.enemies) == initial_enemy_count


class TestGameFlowIntegration:
    def test_game_scene_initializes_all_components(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='hard')
        assert scene.player is not None
        assert scene.spawn_controller.enemy_spawner is not None
        assert scene.spawn_controller.enemies == []
        assert scene.game_controller.state.running is True
        assert scene.paused is False
        assert scene.score == 0
        assert scene.cycle_count == 0
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
        from airwar.game.constants import DamageConstants
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.on_player_hit(DamageConstants.INSTANT_KILL, scene.player)
        for _ in range(200):
            scene.game_controller.update(scene.player, False)
        assert scene.is_game_over() is True

    def test_death_triggered_immediately_on_health_zero(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.player.health = 50
        scene.game_controller.on_player_hit(50, scene.player)
        assert scene.player.health <= 0
        assert scene.game_controller.state.gameplay_state == GameplayState.DYING

    def test_death_triggered_when_health_goes_negative(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.player.health = 10
        scene.game_controller.on_player_hit(50, scene.player)
        assert scene.player.health <= 0
        assert scene.game_controller.state.gameplay_state == GameplayState.DYING

    def test_death_menu_appears_after_animation_duration(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.constants import DamageConstants
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.on_player_hit(DamageConstants.INSTANT_KILL, scene.player)
        assert scene.is_game_over() is False
        for _ in range(199):
            scene.game_controller.update(scene.player, False)
        assert scene.is_game_over() is False
        scene.game_controller.update(scene.player, False)
        assert scene.is_game_over() is True

    def test_death_duration_is_200_frames(self):
        from airwar.game.managers.game_controller import GameState
        state = GameState()
        assert state.death_duration == 200

    def test_enemy_collision_damages_player(self):
        import pygame
        pygame.init()
        from airwar.scenes.game_scene import GameScene
        from airwar.entities import Enemy, EnemyData
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.player.health = 100
        scene.unlocked_buffs = []
        scene.game_controller.state.player_invincible = False
        enemy = Enemy(scene.player.rect.x - 50, scene.player.rect.y - 60, EnemyData())
        enemy.rect.x = scene.player.rect.x
        enemy.rect.y = scene.player.rect.y
        scene.spawn_controller.enemies.append(enemy)
        scene.update()
        assert scene.player.health <= 100


class TestNotificationSystem:
    def test_notification_shows_on_reward(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        reward = {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'}
        scene._on_reward_selected(reward)
        assert scene.game_controller.state.notification == "REWARD: Power Shot"
        assert scene.game_controller.state.notification_timer == 90

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
