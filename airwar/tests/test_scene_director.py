import pytest
from unittest.mock import Mock, MagicMock, patch
import pygame


class TestPauseAction:
    """Tests for PauseAction enum"""

    def test_pause_action_enum_exists(self):
        from airwar.scenes.scene import PauseAction
        assert PauseAction.RESUME is not None
        assert PauseAction.MAIN_MENU is not None
        assert PauseAction.SAVE_AND_QUIT is not None
        assert PauseAction.QUIT_WITHOUT_SAVING is not None
        assert PauseAction.QUIT is not None

    def test_pause_action_values(self):
        from airwar.scenes.scene import PauseAction
        assert PauseAction.RESUME.value == "resume"
        assert PauseAction.MAIN_MENU.value == "main_menu"
        assert PauseAction.SAVE_AND_QUIT.value == "save_and_quit"
        assert PauseAction.QUIT_WITHOUT_SAVING.value == "quit_without_saving"
        assert PauseAction.QUIT.value == "quit"


class TestPauseSceneResult:
    """Tests for PauseScene result handling"""

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

    def test_pause_scene_returns_save_and_quit(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 2
        scene._select_option()

        assert scene.result == PauseAction.SAVE_AND_QUIT

    def test_pause_scene_returns_quit_without_saving(self):
        from airwar.scenes.pause_scene import PauseScene
        from airwar.scenes.scene import PauseAction

        scene = PauseScene()
        scene.enter()
        scene.selected_index = 3
        scene._select_option()

        assert scene.result == PauseAction.QUIT_WITHOUT_SAVING

    def test_pause_scene_has_four_options(self):
        from airwar.scenes.pause_scene import PauseScene

        scene = PauseScene()
        scene.enter()

        assert len(scene.options) == 4
        assert scene.options == ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']

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
