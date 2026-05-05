from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.scene_director import SceneDirector
from airwar.game.mother_ship.mother_ship_state import GameSaveData
from airwar.game.mother_ship.persistence_manager import PersistenceManager
from airwar.scenes.scene import ExitConfirmAction, PauseAction
from airwar.utils.database import DatabaseError


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


def test_update_user_stats_handles_database_error_without_crashing():
    user_db = MagicMock()
    user_db.get_user_data.side_effect = DatabaseError("corrupt db")
    director = SceneDirector(SimpleNamespace(), MagicMock(), user_db)
    director._current_user = "pilot"

    assert director._update_user_stats(1200, 5) is None


def test_saved_game_lookup_falls_back_to_legacy_global_save(tmp_path):
    director = _director()
    director._save_dir = str(tmp_path)
    legacy = PersistenceManager(save_dir=str(tmp_path))
    legacy.save_game(GameSaveData(username="pilot", score=3200))

    save_data = director._check_and_get_saved_game("pilot")

    assert save_data is not None
    assert save_data.score == 3200


def test_clear_saved_game_deletes_matching_legacy_global_save(tmp_path):
    director = _director()
    director._current_user = "pilot"
    director._save_dir = str(tmp_path)
    legacy = PersistenceManager(save_dir=str(tmp_path))
    legacy.save_game(GameSaveData(username="pilot", score=3200))

    director._clear_saved_game()

    assert legacy.load_game() is None


class FakeExitConfirmScene:
    def __init__(self, result):
        self.result = result
        self.enter = MagicMock()
        self.exit = MagicMock()

    def is_running(self):
        return False

    def get_result(self):
        return self.result


def test_exit_confirm_return_to_menu_keeps_successful_save():
    scene_manager = MagicMock()
    exit_scene = FakeExitConfirmScene(ExitConfirmAction.RETURN_TO_MENU)
    scene_manager.get_scene.return_value = exit_scene
    director = SceneDirector(SimpleNamespace(), scene_manager)
    director._clear_saved_game = MagicMock()

    result = director._show_exit_confirm(saved=True)

    assert result == "main_menu"
    director._clear_saved_game.assert_not_called()


def test_exit_confirm_return_to_menu_clears_unsaved_exit():
    scene_manager = MagicMock()
    exit_scene = FakeExitConfirmScene(ExitConfirmAction.RETURN_TO_MENU)
    scene_manager.get_scene.return_value = exit_scene
    director = SceneDirector(SimpleNamespace(), scene_manager)
    director._clear_saved_game = MagicMock()

    result = director._show_exit_confirm(saved=False)

    assert result == "main_menu"
    director._clear_saved_game.assert_called_once()
