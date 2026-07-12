"""Tests for the scene lifecycle framework."""

from typing import Any

import pygame
import pytest

from airwar.scenes.scene import (
    Scene,
    SceneAlreadyActiveError,
    SceneManager,
    SceneNotRegisteredError,
    SceneUnknownError,
)


class FakeScene(Scene):
    """Minimal scene implementation for framework tests."""

    def __init__(self, name: str):
        self.name = name
        self.enter_calls: list[Any] = []
        self.exit_calls = 0
        self.events: list[Any] = []
        self.updated = False
        self.rendered = False
        self._running = True

    def enter(self, **kwargs):
        self.enter_calls.append(kwargs)

    def exit(self):
        self.exit_calls += 1

    def handle_events(self, event: pygame.event.Event):
        self.events.append(event)

    def update(self, *args, **kwargs):
        self.updated = True

    def render(self, surface: pygame.Surface):
        self.rendered = True


@pytest.fixture
def manager():
    return SceneManager()


@pytest.fixture
def scene_a():
    return FakeScene("a")


@pytest.fixture
def scene_b():
    return FakeScene("b")


class TestSceneManagerRegistration:
    def test_register_and_get_scene(self, manager, scene_a):
        manager.register("a", scene_a)
        assert manager.get_scene("a") is scene_a

    def test_register_rejects_non_scene(self, manager):
        with pytest.raises(TypeError):
            manager.register("bad", object())

    def test_register_no_overwrite(self, manager, scene_a, scene_b):
        manager.register("a", scene_a)
        with pytest.raises(ValueError):
            manager.register("a", scene_b, overwrite=False)
        assert manager.get_scene("a") is scene_a

    def test_get_current_scene_before_switch_is_none(self, manager):
        assert manager.get_current_scene() is None
        assert manager.get_current_scene_name() == ""


class TestSceneManagerSwitching:
    def test_switch_calls_exit_and_enter(self, manager, scene_a, scene_b):
        manager.register("a", scene_a)
        manager.register("b", scene_b)
        manager.switch("a", difficulty="easy")
        manager.switch("b")

        assert scene_a.exit_calls == 1
        assert scene_b.enter_calls == [{}]
        assert manager.get_current_scene() is scene_b
        assert manager.get_current_scene_name() == "b"

    def test_switch_passes_kwargs_to_enter(self, manager, scene_a):
        manager.register("a", scene_a)
        manager.switch("a", difficulty="hard", username="guest")
        assert scene_a.enter_calls == [{"difficulty": "hard", "username": "guest"}]

    def test_switch_to_same_scene_raises(self, manager, scene_a):
        manager.register("a", scene_a)
        manager.switch("a")
        with pytest.raises(SceneAlreadyActiveError):
            manager.switch("a")

    def test_switch_to_unregistered_scene_raises(self, manager):
        with pytest.raises(SceneNotRegisteredError):
            manager.switch("missing")

    def test_switch_enter_exception_restores_previous_scene(self, manager, scene_a):
        class BrokenEnterScene(FakeScene):
            def enter(self, **kwargs):
                raise RuntimeError("enter failed")

        broken = BrokenEnterScene("broken")
        manager.register("a", scene_a)
        manager.register("broken", broken)
        manager.switch("a")
        assert manager.get_current_scene() is scene_a

        with pytest.raises(RuntimeError):
            manager.switch("broken")

        assert manager.get_current_scene() is scene_a
        assert manager.get_current_scene_name() == "a"
        # Old scene should have been exited once by the failed switch and
        # re-entered during rollback.
        assert scene_a.exit_calls == 1
        assert scene_a.enter_calls == [{}, {}]


class TestSceneManagerDispatch:
    def test_update_routes_to_current_scene(self, manager, scene_a):
        manager.register("a", scene_a)
        manager.switch("a")
        manager.update(frame="ctx")
        assert scene_a.updated is True

    def test_render_routes_to_current_scene(self, manager, scene_a):
        manager.register("a", scene_a)
        manager.switch("a")
        surface = pygame.Surface((10, 10))
        manager.render(surface)
        assert scene_a.rendered is True

    def test_handle_events_routes_to_current_scene(self, manager, scene_a):
        manager.register("a", scene_a)
        manager.switch("a")
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        manager.handle_events(event)
        assert scene_a.events == [event]

    def test_update_without_active_scene_raises(self, manager):
        with pytest.raises(SceneUnknownError):
            manager.update()

    def test_render_without_active_scene_raises(self, manager):
        with pytest.raises(SceneUnknownError):
            manager.render(pygame.Surface((10, 10)))

    def test_handle_events_without_active_scene_raises(self, manager):
        with pytest.raises(SceneUnknownError):
            manager.handle_events(pygame.event.Event(pygame.KEYDOWN))
