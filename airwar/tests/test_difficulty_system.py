import pytest
import pygame
from unittest.mock import Mock, MagicMock
from airwar.game.systems.difficulty_manager import DifficultyManager, DifficultyListener
from airwar.game.systems.difficulty_strategies import (
    EasyStrategy,
    MediumStrategy,
    HardStrategy,
    DifficultyStrategyFactory,
)
from airwar.game.systems.movement_pattern_generator import MovementPatternGenerator
from airwar.game.rendering.difficulty_indicator import DifficultyIndicator


class TestDifficultyStrategies:
    def test_easy_strategy_values(self):
        strategy = EasyStrategy()
        assert strategy.GROWTH_RATE == 0.5
        assert strategy.BASE_MULTIPLIER == 0.8
        assert strategy.MAX_MULTIPLIER == 3.0

    def test_medium_strategy_values(self):
        strategy = MediumStrategy()
        assert strategy.GROWTH_RATE == 1.0
        assert strategy.BASE_MULTIPLIER == 1.0
        assert strategy.MAX_MULTIPLIER == 5.0

    def test_hard_strategy_values(self):
        strategy = HardStrategy()
        assert strategy.GROWTH_RATE == 1.5
        assert strategy.BASE_MULTIPLIER == 1.2
        assert strategy.MAX_MULTIPLIER == 8.0

    def test_strategy_factory_easy(self):
        strategy = DifficultyStrategyFactory.create('easy')
        assert isinstance(strategy, EasyStrategy)

    def test_strategy_factory_medium(self):
        strategy = DifficultyStrategyFactory.create('medium')
        assert isinstance(strategy, MediumStrategy)

    def test_strategy_factory_hard(self):
        strategy = DifficultyStrategyFactory.create('hard')
        assert isinstance(strategy, HardStrategy)

    def test_strategy_factory_invalid_defaults_to_medium(self):
        strategy = DifficultyStrategyFactory.create('invalid')
        assert isinstance(strategy, MediumStrategy)


class TestDifficultyManager:
    def test_initialization(self):
        manager = DifficultyManager('medium')
        assert manager.get_current_multiplier() == 1.0
        assert manager.get_boss_kill_count() == 0

    def test_boss_killed_updates_count(self):
        manager = DifficultyManager('medium')
        manager.on_boss_killed()
        assert manager.get_boss_kill_count() == 1

    def test_exponential_growth(self):
        manager = DifficultyManager('medium')

        manager.on_boss_killed()
        assert manager.get_current_multiplier() == 2.0

        manager.on_boss_killed()
        assert manager.get_current_multiplier() == 4.0

        manager.on_boss_killed()
        assert manager.get_current_multiplier() == 5.0

    def test_max_multiplier_cap(self):
        manager = DifficultyManager('easy')

        for _ in range(10):
            manager.on_boss_killed()

        assert manager.get_current_multiplier() == 3.0

    def test_negative_count_raises_error(self):
        manager = DifficultyManager('medium')

        with pytest.raises(ValueError):
            manager.set_boss_kill_count(-1)

    def test_params_caching(self):
        manager = DifficultyManager('medium')
        params1 = manager.get_current_params()
        params2 = manager.get_current_params()
        assert params1 == params2

        manager.on_boss_killed()
        params3 = manager.get_current_params()
        assert params3 != params1

    def test_get_boss_kill_count(self):
        manager = DifficultyManager('medium')
        assert manager.get_boss_kill_count() == 0

        manager.on_boss_killed()
        assert manager.get_boss_kill_count() == 1

    def test_set_boss_kill_count(self):
        manager = DifficultyManager('medium')
        manager.set_boss_kill_count(5)
        assert manager.get_boss_kill_count() == 5

    def test_set_boss_kill_count_caps_at_max(self):
        manager = DifficultyManager('medium')
        manager.set_boss_kill_count(100)
        assert manager.get_boss_kill_count() == manager.MAX_BOSS_COUNT


class TestDifficultyGrowth:
    @pytest.mark.parametrize('difficulty,expected_multipliers', [
        ('easy', [1.3, 2.3, 3.0]),
        ('medium', [2.0, 4.0, 5.0]),
        ('hard', [2.7, 5.7, 8.0]),
    ])
    def test_growth_curve(self, difficulty, expected_multipliers):
        manager = DifficultyManager(difficulty)

        for expected in expected_multipliers[:3]:
            manager.on_boss_killed()
            assert abs(manager.get_current_multiplier() - expected) < 0.1

    def test_boss_count_sync(self):
        manager = DifficultyManager('medium')

        manager.set_boss_kill_count(5)
        assert manager.get_boss_kill_count() == 5
        assert manager.get_current_multiplier() == 5.0


class TestDifficultyListener:
    def test_listener_notified_on_boss_killed(self):
        class TestListener(DifficultyListener):
            def __init__(self):
                self.last_params = None

            def on_difficulty_changed(self, params):
                self.last_params = params

        manager = DifficultyManager('medium')
        listener = TestListener()
        manager.add_listener(listener)

        manager.on_boss_killed()
        assert listener.last_params is not None
        assert listener.last_params['boss_kills'] == 1

    def test_listener_removed(self):
        class TestListener(DifficultyListener):
            def __init__(self):
                self.call_count = 0

            def on_difficulty_changed(self, params):
                self.call_count += 1

        manager = DifficultyManager('medium')
        listener = TestListener()
        manager.add_listener(listener)
        manager.remove_listener(listener)

        manager.on_boss_killed()
        assert listener.call_count == 0


class TestMovementPatternGenerator:
    def test_get_pattern_returns_valid_pattern(self):
        pattern = MovementPatternGenerator.get_pattern(3)
        assert pattern in ['straight', 'sine', 'zigzag']

    def test_get_pattern_respects_complexity(self):
        pattern1 = MovementPatternGenerator.get_pattern(1)
        assert pattern1 == 'straight'

    def test_get_pattern_complexity_bounded(self):
        pattern_low = MovementPatternGenerator.get_pattern(0)
        assert pattern_low == 'straight'

        pattern_high = MovementPatternGenerator.get_pattern(100)
        assert pattern_high in ['straight', 'sine', 'zigzag', 'hover', 'dive', 'spiral']

    def test_enhance_pattern_returns_dict(self):
        result = MovementPatternGenerator.enhance_pattern('straight', 2.0)
        assert isinstance(result, dict)
        assert 'speed_multiplier' in result

    def test_enhance_pattern_unknown_pattern(self):
        result = MovementPatternGenerator.enhance_pattern('unknown', 2.0)
        assert 'speed_multiplier' in result

    def test_enhance_pattern_straight(self):
        result = MovementPatternGenerator.enhance_pattern('straight', 2.0)
        assert 'speed_multiplier' in result
        assert result['speed_multiplier'] == 1.3

    def test_enhance_pattern_sine(self):
        result = MovementPatternGenerator.enhance_pattern('sine', 2.0)
        assert 'amplitude_multiplier' in result
        assert 'frequency_multiplier' in result

    def test_enhance_pattern_spiral(self):
        result = MovementPatternGenerator.enhance_pattern('spiral', 3.0)
        assert 'spiral_speed_multiplier' in result
        assert 'spiral_tightness' in result

    def test_enhance_pattern_difficulty_1_returns_no_bonus(self):
        result = MovementPatternGenerator.enhance_pattern('straight', 1.0)
        assert result['speed_multiplier'] == 1.0

    @pytest.mark.parametrize('pattern', ['straight', 'sine', 'zigzag', 'hover', 'dive', 'spiral'])
    def test_enhance_pattern_all_patterns(self, pattern):
        result = MovementPatternGenerator.enhance_pattern(pattern, 2.0)
        assert isinstance(result, dict)
        assert len(result) > 0


class TestDifficultyParams:
    def test_current_params_contains_required_keys(self):
        manager = DifficultyManager('medium')
        params = manager.get_current_params()

        required_keys = ['speed', 'fire_rate', 'aggression', 'spawn_rate', 'multiplier', 'boss_kills', 'complexity']
        for key in required_keys:
            assert key in params

    def test_speed_multiplier_increases_with_boss_kills(self):
        manager = DifficultyManager('medium')
        initial_speed = manager.get_speed_multiplier()

        manager.on_boss_killed()
        manager.on_boss_killed()

        new_speed = manager.get_speed_multiplier()
        assert new_speed > initial_speed

    def test_fire_rate_multiplier_increases_with_boss_kills(self):
        manager = DifficultyManager('medium')
        initial_fire = manager.get_fire_rate_multiplier()

        manager.on_boss_killed()
        manager.on_boss_killed()

        new_fire = manager.get_fire_rate_multiplier()
        assert new_fire > initial_fire

    def test_movement_complexity_increases(self):
        manager = DifficultyManager('medium')
        initial_complexity = manager.get_movement_complexity()

        for _ in range(4):
            manager.on_boss_killed()

        new_complexity = manager.get_movement_complexity()
        assert new_complexity >= initial_complexity


class TestDifficultyIndicator:
    def test_get_difficulty_color_low(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        assert indicator._get_difficulty_color(1.5) == (100, 255, 100)
        assert indicator._get_difficulty_color(1.9) == (100, 255, 100)

    def test_get_difficulty_color_medium(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        assert indicator._get_difficulty_color(2.0) == (255, 255, 100)
        assert indicator._get_difficulty_color(3.9) == (255, 255, 100)

    def test_get_difficulty_color_high(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        assert indicator._get_difficulty_color(4.0) == (255, 150, 50)
        assert indicator._get_difficulty_color(5.9) == (255, 150, 50)

    def test_get_difficulty_color_extreme(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        assert indicator._get_difficulty_color(6.0) == (255, 50, 50)
        assert indicator._get_difficulty_color(10.0) == (255, 50, 50)

    def test_toggle_details(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        assert indicator.is_showing_details() is False

        indicator.toggle_details()
        assert indicator.is_showing_details() is True

        indicator.toggle_details()
        assert indicator.is_showing_details() is False

    def test_set_show_details(self):
        mock_manager = Mock(spec=DifficultyManager)
        indicator = DifficultyIndicator(mock_manager)

        indicator.set_show_details(True)
        assert indicator.is_showing_details() is True

        indicator.set_show_details(False)
        assert indicator.is_showing_details() is False

    def test_render_does_not_raise(self):
        pygame.init()
        mock_manager = Mock(spec=DifficultyManager)
        mock_manager.get_current_params.return_value = {
            'multiplier': 2.5,
            'boss_kills': 3,
            'speed': 4.0,
            'fire_rate': 60,
            'aggression': 0.8,
            'spawn_rate': 30,
            'complexity': 2,
        }
        mock_manager.MAX_MULTIPLIER_GLOBAL = 8.0

        indicator = DifficultyIndicator(mock_manager)

        surface = pygame.Surface((800, 600))
        indicator.render(surface)
        pygame.quit()
