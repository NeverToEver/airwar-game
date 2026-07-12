"""Tests for GameScene event dispatchers exception isolation."""

from unittest.mock import MagicMock

import pygame

from airwar.scenes.game_scene_event_dispatcher import GameSceneEventDispatcher
from airwar.scenes.scene_homecoming_dispatcher import SceneHomecomingDispatcher


class TestGameSceneEventDispatcherExceptions:
    def _make_scene(self):
        scene = MagicMock()
        scene._input_coordinator = MagicMock()
        scene.game_renderer = MagicMock()
        scene.game_renderer.integrated_hud = MagicMock()
        scene._aim_assist = MagicMock()
        scene._homecoming_base_pending = False
        scene._base_talent_console = MagicMock()
        return scene

    def test_input_coordinator_exception_is_caught_and_logged(self, caplog):
        scene = self._make_scene()
        scene._input_coordinator.handle_events.side_effect = RuntimeError("input boom")
        dispatcher = GameSceneEventDispatcher(scene)

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)
        # Should not raise.
        dispatcher.dispatch(event)

        assert "input boom" in caplog.text
        # HUD toggle should NOT run because input handling failed before branching.
        scene.game_renderer.integrated_hud.toggle.assert_not_called()

    def test_exception_is_isolated_between_events(self, caplog):
        scene = self._make_scene()

        def handle_events(event):
            if event.type == pygame.KEYDOWN:
                raise RuntimeError("key boom")

        scene._input_coordinator.handle_events.side_effect = handle_events
        dispatcher = GameSceneEventDispatcher(scene)

        bad_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)
        good_event = pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 2))

        dispatcher.dispatch(bad_event)
        dispatcher.dispatch(good_event)

        assert "key boom" in caplog.text
        scene._aim_assist.set_raw_aim_position.assert_called_with((1, 2))

    def test_mouse_button_branch_exception_is_caught(self, caplog):
        scene = self._make_scene()
        scene.handle_mouse_click.side_effect = RuntimeError("click boom")
        dispatcher = GameSceneEventDispatcher(scene)

        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 20))
        dispatcher.dispatch(event)

        assert "click boom" in caplog.text
        scene._aim_assist.set_raw_aim_position.assert_called_with((10, 20))


class TestSceneHomecomingDispatcherExceptions:
    def _make_dispatcher(self, coordinator):
        scene = MagicMock()
        return SceneHomecomingDispatcher(coordinator, scene), scene

    def test_on_requested_exception_is_caught_and_logged(self, caplog):
        coordinator = MagicMock()
        coordinator.on_requested.side_effect = RuntimeError("homecoming boom")
        dispatcher, scene = self._make_dispatcher(coordinator)

        dispatcher.on_requested()

        assert "homecoming boom" in caplog.text
        coordinator.on_requested.assert_called_once()

    def test_on_complete_exception_is_caught(self, caplog):
        coordinator = MagicMock()
        coordinator.on_complete.side_effect = RuntimeError("complete boom")
        dispatcher, scene = self._make_dispatcher(coordinator)

        dispatcher.on_complete()

        assert "complete boom" in caplog.text
        coordinator.on_complete.assert_called_once()

    def test_handle_console_click_exception_returns_false(self, caplog):
        coordinator = MagicMock()
        coordinator.handle_console_click.side_effect = RuntimeError("console boom")
        dispatcher, scene = self._make_dispatcher(coordinator)

        result = dispatcher.handle_console_click((0, 0))

        assert result is False
        assert "console boom" in caplog.text
