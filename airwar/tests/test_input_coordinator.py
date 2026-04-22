import pytest
from unittest.mock import MagicMock, Mock
from airwar.game.managers.input_coordinator import InputCoordinator


class TestInputCoordinator:
    def test_creation(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        assert coordinator._player == player
        assert coordinator._game_controller == game_controller

    def test_handle_events_delegates_to_reward_selector_for_any_event(self):
        import pygame
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        event = MagicMock()
        event.type = pygame.KEYDOWN
        event.key = pygame.K_SPACE

        coordinator.handle_events(event)

        reward_selector.handle_input.assert_called_once_with(event)

    def test_handle_events_delegates_when_paused(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        event = MagicMock()
        event.type = 2
        event.key = 32

        coordinator.handle_events(event)

        reward_selector.handle_input.assert_called_once_with(event)

    def test_handle_events_delegates_when_reward_visible(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        reward_selector = MagicMock()
        reward_selector.visible = True
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        event = MagicMock()
        event.type = 2
        event.key = 32

        coordinator.handle_events(event)

        reward_selector.handle_input.assert_called_once_with(event)

    def test_handle_events_delegates_to_reward_selector(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        event = MagicMock()
        event.type = 2
        event.key = 99

        coordinator.handle_events(event)

        reward_selector.handle_input.assert_called_once_with(event)

    def test_update_give_up_when_active(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_detector.is_active.return_value = True
        give_up_detector.get_progress.return_value = 0.5
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        coordinator.update_give_up()

        give_up_detector.update.assert_called_once()
        give_up_ui.show.assert_called_once()
        give_up_ui.update_progress.assert_called_once_with(0.5)

    def test_update_give_up_when_inactive(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_detector.is_active.return_value = False
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        coordinator.update_give_up()

        give_up_detector.update.assert_called_once()
        give_up_ui.hide.assert_called_once()

    def test_update_give_up_when_not_playing(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = False
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_ui = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        coordinator.update_give_up()

        give_up_detector.update.assert_not_called()
        give_up_ui.hide.assert_called_once()

    def test_render_give_up_when_active(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_detector.is_active.return_value = True
        give_up_ui = MagicMock()
        surface = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        coordinator.render_give_up(surface)

        give_up_ui.render.assert_called_once_with(surface)

    def test_render_give_up_when_inactive(self):
        player = MagicMock()
        game_controller = MagicMock()
        game_controller.state.paused = False
        game_controller.is_playing.return_value = True
        reward_selector = MagicMock()
        reward_selector.visible = False
        give_up_detector = MagicMock()
        give_up_detector.is_active.return_value = False
        give_up_ui = MagicMock()
        surface = MagicMock()

        coordinator = InputCoordinator(
            player, game_controller, reward_selector, give_up_detector, give_up_ui
        )

        coordinator.render_give_up(surface)

        give_up_ui.render.assert_not_called()
