"""Regression coverage for welcome-page child-flow re-entry.

The welcome screen launches tutorial/settings/benchmark as one-shot child
flows. Returning from one of those flows must restore the welcome scene to a
running state and consume the request flag; otherwise the next welcome-loop
iteration immediately reopens the same child flow, or leaves
SceneManager._current_scene pointing at the tutorial while the switcher is
rendering the welcome instance directly.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.scene_director_components.scene_switcher import SceneSwitcher
from airwar.scenes.scene import Scene
from airwar.scenes.scene import SceneManager


class _FlowScene(Scene):
    def __init__(self) -> None:
        self.running = False
        self.enter_calls = 0
        self.exit_calls = 0
        self.received: list[pygame.event.Event] = []

    def enter(self, **kwargs) -> None:
        self.running = True
        self.enter_calls += 1

    def exit(self) -> None:
        self.running = False
        self.exit_calls += 1

    def handle_events(self, event: pygame.event.Event) -> None:
        self.received.append(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False

    def update(self, *args, **kwargs) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        pass

    def is_running(self) -> bool:
        return self.running


class _WelcomeFlowScene(_FlowScene):
    def __init__(self, request: str) -> None:
        super().__init__()
        self.request = request
        self.tutorial_requested = request == "tutorial"
        self.settings_requested = request == "settings"
        self.benchmark_requested = request == "benchmark"
        self.want_to_quit = False
        self.ready = False
        self.username = "pilot"
        self.difficulty = "medium"
        self.clear_hover_calls = 0

    def clear_hover(self) -> None:
        self.clear_hover_calls += 1

    def should_quit(self) -> bool:
        return self.want_to_quit

    def should_open_tutorial(self) -> bool:
        return self.tutorial_requested

    def should_open_settings(self) -> bool:
        return self.settings_requested

    def should_open_benchmark(self) -> bool:
        return self.benchmark_requested

    def is_ready(self) -> bool:
        return self.ready

    def get_username(self) -> str:
        return self.username

    def get_difficulty(self) -> str:
        return self.difficulty


def _make_switcher(sm: SceneManager) -> SceneSwitcher:
    viewport = SimpleNamespace(
        screen_to_logical=lambda x, y: (x, y),
        logical_surface=pygame.Surface((320, 240), pygame.SRCALPHA),
    )
    director = SimpleNamespace(
        _running=True,
        _window=SimpleNamespace(get_surface=lambda: pygame.Surface((320, 240), pygame.SRCALPHA)),
        _user_db=None,
        _current_user=None,
        _selected_difficulty="medium",
        _settings_ref={"ctrl_mode": "hold", "shift_boost_mode": "hold"},
        _mothership_dock_count=0,
        _achievement_registry=None,
        _load_user_settings=MagicMock(),
        _create_achievement_registry=MagicMock(),
        _check_and_get_saved_game=MagicMock(return_value=None),
    )
    switcher = SceneSwitcher(director, sm, viewport)
    switcher._render_scene = MagicMock()
    return switcher


def test_tutorial_return_restores_welcome_scene_and_consumes_request() -> None:
    sm = SceneManager()
    welcome = _WelcomeFlowScene("tutorial")
    tutorial = _FlowScene()
    sm.register("welcome", welcome)
    sm.register("tutorial", tutorial)
    switcher = _make_switcher(sm)

    loop_calls = 0

    def fake_loop(scene, *, escape_handled=False):
        nonlocal loop_calls
        loop_calls += 1
        if scene is welcome and loop_calls == 2:
            assert welcome.running is True
            assert welcome.tutorial_requested is False
            assert sm.get_current_scene_name() == "welcome"
        scene.running = False
        if scene is welcome and loop_calls >= 2:
            welcome.ready = True
        return "ended"

    switcher._run_scene_loop = fake_loop

    ok, save_data = switcher.run_welcome_flow()

    assert ok is True
    assert save_data is None
    assert sm.get_current_scene_name() == "welcome"
    assert welcome.tutorial_requested is False
    assert tutorial.enter_calls == 1
    assert welcome.enter_calls == 2


def test_settings_request_is_one_shot_after_child_flow_returns() -> None:
    sm = SceneManager()
    welcome = _WelcomeFlowScene("settings")
    sm.register("welcome", welcome)
    switcher = _make_switcher(sm)
    switcher._show_settings_menu = MagicMock(return_value=True)

    def fake_loop(scene, *, escape_handled=False):
        if not welcome.settings_requested:
            assert welcome.running is True
            assert sm.get_current_scene_name() == "welcome"
        scene.running = False
        if not welcome.settings_requested:
            welcome.ready = True
        return "ended"

    switcher._run_scene_loop = fake_loop

    ok, _ = switcher.run_welcome_flow()

    assert ok is True
    switcher._show_settings_menu.assert_called_once_with()
    assert sm.get_current_scene_name() == "welcome"
    assert welcome.settings_requested is False
    assert welcome.clear_hover_calls >= 1


def test_benchmark_request_is_one_shot_after_child_flow_returns() -> None:
    sm = SceneManager()
    welcome = _WelcomeFlowScene("benchmark")
    sm.register("welcome", welcome)
    switcher = _make_switcher(sm)
    switcher._show_benchmark_menu = MagicMock(return_value=True)

    def fake_loop(scene, *, escape_handled=False):
        if not welcome.benchmark_requested:
            assert welcome.running is True
            assert sm.get_current_scene_name() == "welcome"
        scene.running = False
        if not welcome.benchmark_requested:
            welcome.ready = True
        return "ended"

    switcher._run_scene_loop = fake_loop

    ok, _ = switcher.run_welcome_flow()

    assert ok is True
    switcher._show_benchmark_menu.assert_called_once_with()
    assert sm.get_current_scene_name() == "welcome"
    assert welcome.benchmark_requested is False
