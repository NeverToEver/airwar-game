import pytest
from unittest.mock import MagicMock


class TestMilestoneManager:
    """MilestoneManager 单元测试"""

    def test_milestone_manager_creation(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        assert manager is not None
        assert manager._game_controller is game_controller
        assert manager._reward_system is reward_system

    def test_set_reward_selector(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        reward_selector = MagicMock()
        manager.set_reward_selector(reward_selector)
        assert manager._reward_selector is reward_selector

    def test_check_and_trigger_returns_false_when_below_threshold(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        game_controller.get_next_threshold.return_value = 1000
        game_controller.state.score = 500
        reward_system = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        player = MagicMock()
        result = manager.check_and_trigger(player)
        assert result is False

    def test_check_and_trigger_returns_true_and_shows_reward_when_at_threshold(self):
        from airwar.game.managers import MilestoneManager
        from airwar.game.controllers.game_controller import GameplayState
        game_controller = MagicMock()
        game_controller.get_next_threshold.return_value = 1000
        game_controller.state.score = 1000
        game_controller.state.gameplay_state = GameplayState.PLAYING
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        result = manager.check_and_trigger(player)
        assert result is True
        reward_selector.visible = True

    def test_check_and_trigger_returns_true_and_shows_reward_when_above_threshold(self):
        from airwar.game.managers import MilestoneManager
        from airwar.game.controllers.game_controller import GameplayState
        game_controller = MagicMock()
        game_controller.get_next_threshold.return_value = 1000
        game_controller.state.score = 1500
        game_controller.state.gameplay_state = GameplayState.PLAYING
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        result = manager.check_and_trigger(player)
        assert result is True
        reward_selector.visible = True

    def test_check_and_trigger_returns_false_when_dying(self):
        from airwar.game.managers import MilestoneManager
        from airwar.game.controllers.game_controller import GameplayState
        game_controller = MagicMock()
        game_controller.get_next_threshold.return_value = 1000
        game_controller.state.score = 1500
        game_controller.state.gameplay_state = GameplayState.DYING
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        result = manager.check_and_trigger(player)
        assert result is False
        reward_selector.show.assert_not_called()

    def test_check_and_trigger_returns_false_when_game_over(self):
        from airwar.game.managers import MilestoneManager
        from airwar.game.controllers.game_controller import GameplayState
        game_controller = MagicMock()
        game_controller.get_next_threshold.return_value = 1000
        game_controller.state.score = 1500
        game_controller.state.gameplay_state = GameplayState.GAME_OVER
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        result = manager.check_and_trigger(player)
        assert result is False
        reward_selector.show.assert_not_called()

    def test_trigger_reward_selection_pauses_game(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        manager._trigger_reward_selection(player)
        assert game_controller.state.paused is True

    def test_trigger_reward_selection_generates_options(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        manager._trigger_reward_selection(player)
        reward_system.generate_options.assert_called_once()

    def test_show_reward_selection_sets_reward_selector_properties(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        options = [{'name': 'Option1'}, {'name': 'Option2'}]
        manager._show_reward_selection(options, player)
        assert reward_selector.visible is True
        assert reward_selector.options == options
        assert reward_selector.selected_index == 0
        assert reward_selector.on_select is not None

    def test_on_reward_selected_calls_game_controller(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        player = MagicMock()
        reward = {'name': 'TestReward'}
        manager._on_reward_selected(reward, player)
        game_controller.on_reward_selected.assert_called_once_with(reward, player)
        assert reward_selector.visible is False

    def test_on_reward_selected_calls_callback(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        callback = MagicMock()
        manager.set_on_reward_selected_callback(callback)
        player = MagicMock()
        reward = {'name': 'TestReward'}
        manager._on_reward_selected(reward, player)
        callback.assert_called_once_with(reward)

    def test_on_reward_selected_does_not_fail_without_reward_selector(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        player = MagicMock()
        reward = {'name': 'TestReward'}
        manager._on_reward_selected(reward, player)
        game_controller.on_reward_selected.assert_called_once_with(reward, player)

    def test_is_reward_visible_returns_true_when_visible(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        reward_selector.visible = True
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        assert manager.is_reward_visible is True

    def test_is_reward_visible_returns_false_when_not_visible(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        reward_selector = MagicMock()
        reward_selector.visible = False
        manager = MilestoneManager(game_controller, reward_system)
        manager.set_reward_selector(reward_selector)
        assert manager.is_reward_visible is False

    def test_is_reward_visible_returns_false_without_reward_selector(self):
        from airwar.game.managers import MilestoneManager
        game_controller = MagicMock()
        reward_system = MagicMock()
        manager = MilestoneManager(game_controller, reward_system)
        assert manager.is_reward_visible is False
