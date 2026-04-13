from abc import ABC, abstractmethod
from typing import Dict, Any
import pygame


class Scene(ABC):
    @abstractmethod
    def enter(self, **kwargs) -> None:
        pass

    @abstractmethod
    def exit(self) -> None:
        pass

    @abstractmethod
    def handle_events(self, event: pygame.event.Event) -> None:
        pass

    @abstractmethod
    def update(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        pass


class SceneManager:
    def __init__(self):
        self._scenes: Dict[str, Scene] = {}
        self._current_scene: Scene = None
        self._current_scene_name: str = ""

    def register(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene

    def switch(self, name: str, **kwargs) -> None:
        if self._current_scene:
            self._current_scene.exit()
        self._current_scene = self._scenes[name]
        self._current_scene_name = name
        self._current_scene.enter(**kwargs)

    def get_current_scene(self) -> Scene:
        return self._current_scene

    def get_current_scene_name(self) -> str:
        return self._current_scene_name

    def update(self, *args, **kwargs) -> None:
        if self._current_scene:
            self._current_scene.update(*args, **kwargs)

    def render(self, surface: pygame.Surface) -> None:
        if self._current_scene:
            self._current_scene.render(surface)

    def handle_events(self, event: pygame.event.Event) -> None:
        if self._current_scene:
            self._current_scene.handle_events(event)
