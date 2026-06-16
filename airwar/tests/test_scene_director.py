from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.achievements import USER_DATA_FIELD, build_default_registry
from airwar.game.mother_ship.mother_ship_state import GameSaveData
from airwar.game.mother_ship.persistence_manager import PersistenceManager
from airwar.game.scene_director import SceneDirector
from airwar.scenes.scene import ExitConfirmAction, PauseAction
from airwar.utils.database import DatabaseError, UserDB


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
        # SceneSwitcher._run_scene_loop now pre-renders once before
        # the first dispatch (so the first click has button rects to
        # land on — see commit f262b33). The fake must accept the
        # render call without raising.
        self.render = MagicMock()

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


# ---------------------------------------------------------------------------
# Achievement integration tests
# ---------------------------------------------------------------------------


def test_create_achievement_registry_is_noop_for_guest(tmp_path):
    director = _director()
    director._user_db = UserDB(str(tmp_path / "users.json"))
    director._current_user = "Guest"

    director._create_achievement_registry()

    assert director._achievement_registry is None


def test_create_achievement_registry_skipped_when_no_user_db():
    director = _director()
    director._user_db = None
    director._current_user = "pilot"

    director._create_achievement_registry()

    assert director._achievement_registry is None


def test_create_achievement_registry_hydrates_prior_unlocks(tmp_path):
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("pilot", "secret")
    db.update_user_data(
        "pilot",
        {USER_DATA_FIELD: {"first_kill": "2025-01-01T00:00:00+00:00"}},
    )

    director = _director()
    director._user_db = db
    director._current_user = "pilot"
    director._acquire_event_bus = lambda: None

    director._create_achievement_registry()

    assert director._achievement_registry is not None
    assert "first_kill" in director._achievement_registry.unlocked_ids()


def test_evaluate_achievements_unlocks_defaults_and_persists(tmp_path):
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("pilot", "secret")

    director = _director()
    director._user_db = db
    director._current_user = "pilot"
    director._acquire_event_bus = lambda: None
    director._create_achievement_registry()

    game_scene = SimpleNamespace(
        score=12_000,
        get_kill_count=lambda: 50,
        get_boss_kill_count=lambda: 1,
    )

    unlocked = director._evaluate_achievements(game_scene)

    assert set(unlocked) == {"first_kill", "score_1k", "score_10k", "boss_kill"}

    saved = db.get_user_data("pilot").get(USER_DATA_FIELD)
    assert saved is not None
    assert {"first_kill", "score_1k", "score_10k", "boss_kill"} <= set(saved.keys())


def test_evaluate_achievements_unlocks_mothership_dock_via_counter():
    director = _director()
    director._user_db = MagicMock()
    director._current_user = "pilot"
    director._achievement_registry = build_default_registry(user_db=director._user_db, user_id="pilot")
    director._mothership_dock_count = 1

    game_scene = SimpleNamespace(
        score=0,
        get_kill_count=lambda: 0,
        get_boss_kill_count=lambda: 0,
    )

    unlocked = director._evaluate_achievements(game_scene)

    assert "mothership_dock" in unlocked
    # Counter must reset so the next run starts at zero.
    assert director._mothership_dock_count == 0


def test_evaluate_achievements_is_noop_without_registry():
    director = _director()

    assert director._evaluate_achievements(SimpleNamespace()) == []


def test_evaluate_achievements_tolerates_database_error():
    director = _director()
    director._current_user = "pilot"
    registry = MagicMock()
    registry.check_all.side_effect = DatabaseError("boom")
    director._achievement_registry = registry

    game_scene = SimpleNamespace(
        score=0,
        get_kill_count=lambda: 0,
        get_boss_kill_count=lambda: 0,
    )
    assert director._evaluate_achievements(game_scene) == []


def test_docking_callback_increments_counter_and_rechecks(tmp_path):
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("pilot", "secret")

    director = _director()
    director._user_db = db
    director._current_user = "pilot"
    director._acquire_event_bus = lambda: None
    director._create_achievement_registry()

    assert director._mothership_dock_count == 0

    director._on_mothership_docking_complete()

    assert director._mothership_dock_count == 1
    assert "mothership_dock" in director._achievement_registry.unlocked_ids()


def test_handle_game_over_invokes_evaluate_achievements():
    director = _director()
    director._evaluate_achievements = MagicMock(return_value=["first_kill"])
    director._update_user_stats = MagicMock()
    director._submit_leaderboard_score = MagicMock()

    game_scene = SimpleNamespace(
        score=200,
        get_kill_count=lambda: 1,
        get_boss_kill_count=lambda: 0,
    )
    director._scene_manager.get_scene.return_value = None

    director._handle_game_over(game_scene)

    director._evaluate_achievements.assert_called_once_with(game_scene)


def test_run_uses_overridable_flow_forwarders():
    """Smoke tests and harnesses patch the director-level flow methods."""
    director = _director()
    director._run_welcome_flow = MagicMock(return_value=(True, None))
    director._run_game_flow = MagicMock(return_value="quit")

    director.run()

    director._run_welcome_flow.assert_called_once_with()
    director._run_game_flow.assert_called_once_with()


def test_welcome_flow_resets_per_run_achievement_state(tmp_path):
    """Each welcome iteration must reset dock count and registry reference.

    A restart-from-menu flow should not carry over the previous run's
    counter or registry; otherwise achievements would either double-fire
    or skip a re-evaluation.
    """
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("pilot", "secret")

    director = _director()
    director._user_db = db
    director._current_user = "pilot"
    director._acquire_event_bus = lambda: None
    director._create_achievement_registry()
    director._mothership_dock_count = 5  # simulate prior run

    # Simulate welcome flow reset
    director._mothership_dock_count = 0
    director._achievement_registry = None
    director._create_achievement_registry()

    assert director._mothership_dock_count == 0
    assert director._achievement_registry is not None
