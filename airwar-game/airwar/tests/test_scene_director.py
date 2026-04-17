import pytest
from unittest.mock import Mock, MagicMock, patch
import pygame


class TestPauseAction:
    def test_pause_action_enum_exists(self):
        from airwar.scenes.scene import PauseAction
        assert PauseAction.RESUME is not None
        assert PauseAction.MAIN_MENU is not None
        assert PauseAction.QUIT is not None

    def test_pause_action_values(self):
        from airwar.scenes.scene import PauseAction
        assert PauseAction.RESUME.value == "resume"
        assert PauseAction.MAIN_MENU.value == "main_menu"
        assert PauseAction.QUIT.value == "quit"


class TestPauseSceneResult:
    def test_pause_scene_returns_resume(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 0
        scene._select_option()

        assert scene.result == PauseAction.RESUME

    def test_pause_scene_returns_main_menu(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 1
        scene._select_option()

        assert scene.result == PauseAction.MAIN_MENU

    def test_pause_scene_returns_quit(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 2
        scene._select_option()

        assert scene.result == PauseAction.QUIT

    def test_pause_scene_escape_returns_resume(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction
        from unittest.mock import Mock

        pygame.init()
        scene = PauseScene()
        scene.enter()

        mock_event = Mock()
        mock_event.type = pygame.KEYDOWN
        mock_event.key = pygame.K_ESCAPE
        scene.handle_events(mock_event)

        assert scene.result == PauseAction.RESUME
        assert scene.running is False

    def test_pause_scene_get_result(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 0
        scene._select_option()

        assert scene.get_result() == PauseAction.RESUME


class TestSceneDirectorFlow:
    def test_scene_director_run_signature(self):
        from airwar.game.scene_director import SceneDirector

        director = SceneDirector.__new__(SceneDirector)
        director._running = False

        assert hasattr(SceneDirector, 'run')
        assert callable(getattr(SceneDirector, 'run'))

    def test_run_game_flow_returns_string(self):
        from airwar.game.scene_director import SceneDirector
        import inspect

        sig = inspect.signature(SceneDirector._run_game_flow)
        return_annotation = sig.return_annotation
        assert return_annotation == str or 'str' in str(return_annotation)