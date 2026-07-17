"""Tests for scene switcher frame-level exception isolation."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pygame
import pytest

from airwar.game.scaled_viewport import ScaledViewport
from airwar.game.scene_director_components.scene_switcher import SceneSwitcher
from airwar.scenes import GameScene
from airwar.scenes.scene import Scene, SceneManager


class FakeWindow:
    """Minimal window stand-in for SceneSwitcher tests."""

    def __init__(self):
        self.tick_calls: list[int] = []
        self.flip_calls = 0
        self.surface = pygame.Surface((100, 100))

    def tick(self, fps: int) -> float:
        self.tick_calls.append(fps)
        return 1.0 / fps

    def flip(self) -> None:
        self.flip_calls += 1

    def get_surface(self) -> pygame.Surface:
        return self.surface

    def get_size(self) -> tuple[int, int]:
        return self.surface.get_size()


class FakeDirector:
    """Minimal director stand-in for SceneSwitcher tests."""

    def __init__(self):
        self._running = True
        self._window = FakeWindow()
        self._user_db = None
        self._current_user = "guest"
        self._settings_ref = {}
        self._selected_difficulty = "medium"
        self._pending_save_data = None
        self._persistence = SimpleNamespace(save_service=None)

    def __class_getitem__(cls, item):
        return cls

    def _handle_pause_toggle(self, events, game_scene) -> str:
        return "none"

    def _dispatch_pause_result(self, result, current_scene):
        return None


class FakeScene(Scene):
    """Scene whose frame methods can be configured to raise exceptions."""

    def __init__(self, name: str = "fake"):
        self.name = name
        self.enter_calls: list[dict[str, Any]] = []
        self.exit_calls = 0
        self.update_calls = 0
        self.render_calls = 0
        self.event_calls: list[pygame.event.Event] = []
        self.frame_errors: list[str] = []
        self.error_after_updates: int | None = None
        self.error_operation: str | None = "update"
        self._running = True
        self.uses_fixed_simulation = False

    def enter(self, **kwargs):
        self.enter_calls.append(kwargs)

    def exit(self):
        self.exit_calls += 1

    def handle_events(self, event: pygame.event.Event):
        self.event_calls.append(event)
        if self.error_operation == "handle_events":
            raise RuntimeError("handle_events error")

    def update(self, *args, **kwargs):
        self.update_calls += 1
        if self.error_operation == "update":
            if self.error_after_updates is None or self.update_calls >= self.error_after_updates:
                raise RuntimeError("update error")

    def render(self, surface: pygame.Surface):
        self.render_calls += 1
        if self.error_operation == "render":
            raise RuntimeError("render error")

    def is_running(self) -> bool:
        return self._running

    def on_frame_error(self, operation: str) -> None:
        self.frame_errors.append(operation)


@pytest.fixture
def switcher():
    director = FakeDirector()
    scene_manager = SceneManager()
    viewport = ScaledViewport(100, 100)
    return SceneSwitcher(director, scene_manager, viewport)


class TestSceneSwitcherFrameErrors:
    def test_single_update_error_is_skipped(self, switcher, caplog):
        scene = FakeScene("error_once")
        scene.error_after_updates = 1

        # Let one bad frame happen, then stop the scene.
        def stop_after_one_error(operation: str) -> None:
            scene.frame_errors.append(operation)
            scene._running = False

        scene.on_frame_error = stop_after_one_error

        with caplog.at_level(logging.ERROR):
            result = switcher._run_scene_loop(scene)

        assert result == "ended"
        assert scene.update_calls == 1
        assert scene.frame_errors == ["update"]
        assert "Frame error in FakeScene.update" in caplog.text

    def test_consecutive_errors_abort_loop(self, switcher, caplog):
        scene = FakeScene("broken")
        scene.error_operation = "update"

        with caplog.at_level(logging.ERROR):
            result = switcher._run_scene_loop(scene)

        assert result == "quit"
        assert scene.update_calls == SceneSwitcher._MAX_CONSECUTIVE_FRAME_ERRORS
        assert "Too many consecutive frame errors" in caplog.text

    def test_successful_frame_resets_error_counter(self, switcher, caplog):
        scene = FakeScene("recovering")
        scene.error_operation = "update"
        scene.error_after_updates = 3

        def stop_after_recovery(*args, **kwargs):
            # Called on each frame error; after the third error the scene
            # recovers, so we stop on the next successful frame.
            if scene.update_calls >= 4:
                scene._running = False

        scene.on_frame_error = stop_after_recovery

        with caplog.at_level(logging.ERROR):
            result = switcher._run_scene_loop(scene)

        assert result == "ended"
        assert scene.update_calls >= 4
        # The scene recovered before hitting the max threshold.
        assert "Too many consecutive frame errors" not in caplog.text

    def test_render_error_is_skipped(self, switcher, caplog):
        scene = FakeScene("bad_render")
        scene.error_operation = "render"
        scene.render_calls = 0

        def render(surface: pygame.Surface) -> None:
            scene.render_calls += 1
            if scene.render_calls > 1:
                raise RuntimeError("render error")

        scene.render = render
        scene.on_frame_error = lambda op: (scene.frame_errors.append(op), setattr(scene, "_running", False))

        with caplog.at_level(logging.ERROR):
            result = switcher._run_scene_loop(scene)

        assert result == "ended"
        assert scene.render_calls == 2
        assert scene.frame_errors == ["render"]

    def test_flip_error_is_skipped(self, switcher, caplog):
        scene = FakeScene("bad_flip")
        scene.error_operation = "flip"

        def bad_flip() -> None:
            raise RuntimeError("flip failed")

        switcher._director._window.flip = bad_flip
        scene.on_frame_error = lambda op: (scene.frame_errors.append(op), setattr(scene, "_running", False))

        with caplog.at_level(logging.ERROR):
            result = switcher._run_scene_loop(scene)

        assert result == "ended"
        assert scene.frame_errors == ["flip"]


class TestSceneSwitcherSubsceneLifecycle:
    def test_settings_subscene_exit_called_on_update_error(self, switcher):
        scene = FakeScene("settings")
        scene.error_operation = "update"
        switcher._scene_manager.register("settings", scene)

        switcher._show_settings_menu()

        # The loop aborts after max consecutive errors, but exit() must still run.
        assert scene.exit_calls == 1


class FakeGameScene(GameScene):
    """GameScene stand-in that passes run_game_flow's isinstance checks.

    Skips ``GameScene.__init__`` (which builds the full gameplay world) and
    implements only the surface ``run_game_flow`` touches.
    """

    def __init__(self) -> None:
        self.update_calls = 0
        self.frame_errors: list[str] = []

    def enter(self, **kwargs) -> None:
        pass

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        pass

    def update(self, *args, **kwargs) -> None:
        self.update_calls += 1
        raise RuntimeError("update error")

    def render(self, surface: pygame.Surface) -> None:
        pass

    def is_homecoming_locked(self) -> bool:
        return False

    def consume_pause_request(self) -> bool:
        return False

    def is_game_over(self) -> bool:
        return False

    def on_frame_error(self, operation: str) -> None:
        self.frame_errors.append(operation)


class TestGameFlowFrameErrors:
    """run_game_flow must isolate bad frames like the other scene loops."""

    def test_consecutive_update_errors_abort_to_main_menu(self, switcher, caplog):
        scene = FakeGameScene()
        switcher._scene_manager.register("game", scene)

        with caplog.at_level(logging.ERROR):
            result = switcher.run_game_flow()

        assert result == "main_menu"
        assert scene.update_calls == SceneSwitcher._MAX_CONSECUTIVE_FRAME_ERRORS
        assert scene.frame_errors == ["update"] * SceneSwitcher._MAX_CONSECUTIVE_FRAME_ERRORS
        assert "Too many consecutive frame errors" in caplog.text
        # The next flow starts with a clean error budget.
        assert switcher._consecutive_frame_errors == 0

    def test_game_flow_recovers_after_single_update_error(self, switcher, caplog):
        scene = FakeGameScene()
        switcher._scene_manager.register("game", scene)

        def update(*args, **kwargs) -> None:
            scene.update_calls += 1
            if scene.update_calls == 1:
                raise RuntimeError("first frame only")
            if scene.update_calls >= 4:
                switcher._director._running = False

        scene.update = update

        with caplog.at_level(logging.ERROR):
            result = switcher.run_game_flow()

        assert result == "quit"  # director stopped -> normal loop exit
        assert scene.update_calls == 4
        assert scene.frame_errors == ["update"]
        assert "Too many consecutive frame errors" not in caplog.text
        assert switcher._frames_advanced >= 4
