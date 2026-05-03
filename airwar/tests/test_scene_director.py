from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.scene_director import SceneDirector
from airwar.scenes.scene import PauseAction


class FakeGameScene:
    def __init__(self, paused=False):
        self.paused = paused
        self.pause = MagicMock()
        self.resume = MagicMock()


def _director():
    window = SimpleNamespace()
    scene_manager = MagicMock()
    return SceneDirector(window, scene_manager)


def test_handle_pause_toggle_consumes_escape_when_resuming_paused_scene():
    director = _director()
    scene = FakeGameScene(paused=True)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    result = director._handle_pause_toggle([event], scene)

    assert result == "resume"
    scene.resume.assert_called_once()


def test_handle_pause_toggle_maps_main_menu_action():
    director = _director()
    director._show_pause_menu = MagicMock(return_value=PauseAction.MAIN_MENU)
    scene = FakeGameScene(paused=False)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    result = director._handle_pause_toggle([event], scene)

    assert result == "main_menu"
    scene.pause.assert_called_once()


def test_handle_scene_events_skips_consumed_escape_event():
    director = _director()
    escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    other = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)

    director._handle_scene_events([escape, other], skip_escape=True)

    director._scene_manager.handle_events.assert_called_once_with(other)
