from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
import pygame


class PauseAction(Enum):
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    SAVE_AND_QUIT = "save_and_quit"
    QUIT_WITHOUT_SAVING = "quit_without_saving"
    QUIT = "quit"


class ExitConfirmAction(Enum):
    RETURN_TO_MENU = "return_to_menu"
    START_NEW_GAME = "start_new_game"
    QUIT_GAME = "quit_game"


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
        self._scene_states: Dict[str, Dict[str, Any]] = {}

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

    def save_scene_state(self, scene_name: str, state: Dict[str, Any]) -> None:
        """
        Save the state of a scene before switching away.
        
        Args:
            scene_name: Name of the scene
            state: Dictionary containing scene state data
        """
        self._scene_states[scene_name] = state.copy()

    def get_scene_state(self, scene_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve saved state for a scene.
        
        Args:
            scene_name: Name of the scene
            
        Returns:
            Saved state dictionary or None if not found
        """
        return self._scene_states.get(scene_name)

    def clear_scene_state(self, scene_name: str) -> None:
        """
        Clear saved state for a scene.
        
        Args:
            scene_name: Name of the scene
        """
        if scene_name in self._scene_states:
            del self._scene_states[scene_name]
