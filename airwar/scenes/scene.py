"""Scene base classes and scene management framework."""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
import pygame


class PauseAction(Enum):
    """Actions available from the pause menu.

    Attributes:
        RESUME: Resume the current game.
        MAIN_MENU: Return to main menu.
        SAVE_AND_QUIT: Save progress and quit.
        QUIT_WITHOUT_SAVING: Quit without saving.
        QUIT: Quit the application.
    """
    RESUME = "resume"
    MAIN_MENU = "main_menu"
    SAVE_AND_QUIT = "save_and_quit"
    QUIT_WITHOUT_SAVING = "quit_without_saving"
    QUIT = "quit"


class ExitConfirmAction(Enum):
    """Actions available from the exit confirmation dialog.

    Attributes:
        RETURN_TO_MENU: Return to menu without quitting.
        START_NEW_GAME: Start a new game.
        QUIT_GAME: Quit the game entirely.
    """
    RETURN_TO_MENU = "return_to_menu"
    START_NEW_GAME = "start_new_game"
    QUIT_GAME = "quit_game"


class Scene(ABC):
    """Abstract base class for all game scenes.

    Defines the interface that all scenes must implement: enter, exit,
    handle_events, update, and render lifecycle methods.
    """

    @abstractmethod
    def enter(self, **kwargs) -> None:
        """Called when the scene becomes active.

        Args:
            **kwargs: Scene-specific initialization data.
        """
        pass

    @abstractmethod
    def exit(self) -> None:
        """Called when the scene is about to be replaced."""
        pass

    @abstractmethod
    def handle_events(self, event: pygame.event.Event) -> None:
        """Process pygame events for this scene.

        Args:
            event: Pygame event to handle.
        """
        pass

    @abstractmethod
    def update(self, *args, **kwargs) -> None:
        """Update scene state each frame.

        Args:
            *args: Scene-specific update arguments.
        """
        pass

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """Render the scene to the display surface.

        Args:
            surface: Pygame surface to render onto.
        """
        pass


class SceneManager:
    """Manages scene registration, switching, and state persistence.

    Handles the lifecycle of scenes including registration, switching,
    state save/restore for scene state preservation across transitions.

    Attributes:
        _scenes: Dictionary of registered scenes by name.
        _current_scene: Currently active scene.
        _current_scene_name: Name of the current scene.
        _scene_states: Saved states for scenes.
    """

    def __init__(self):
        self._scenes: Dict[str, Scene] = {}
        self._current_scene: Scene = None
        self._current_scene_name: str = ""
        self._scene_states: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene

    def switch(self, name: str, **kwargs) -> None:
        """Switch to a named scene.

        Calls exit() on the current scene (if any), then enter() on the
        new scene with the provided keyword arguments.

        Args:
            name: Name of the scene to switch to.
            **kwargs: Data to pass to the new scene's enter() method.
        """
        if self._current_scene:
            self._current_scene.exit()
        self._current_scene = self._scenes[name]
        self._current_scene_name = name
        self._current_scene.enter(**kwargs)

    def get_current_scene(self) -> Scene:
        """Get the currently active scene instance.

        Returns:
            Scene instance or None if no scene is active.
        """
        return self._current_scene

    def get_current_scene_name(self) -> str:
        return self._current_scene_name

    def update(self, *args, **kwargs) -> None:
        """Update the currently active scene."""
        if self._current_scene:
            self._current_scene.update(*args, **kwargs)

    def render(self, surface: pygame.Surface) -> None:
        """Render the currently active scene.

        Args:
            surface: Pygame surface to render onto.
        """
        if self._current_scene:
            self._current_scene.render(surface)

    def handle_events(self, event: pygame.event.Event) -> None:
        if self._current_scene:
            self._current_scene.handle_events(event)

    def save_scene_state(self, scene_name: str, state: Dict[str, Any]) -> None:
        """Save the state of a scene before switching away.

        Args:
            scene_name: Name of the scene.
            state: Dictionary containing scene state data.
        """
        self._scene_states[scene_name] = state.copy()

    def get_scene_state(self, scene_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve saved state for a scene.

        Args:
            scene_name: Name of the scene.

        Returns:
            Saved state dictionary or None if not found.
        """
        return self._scene_states.get(scene_name)

    def clear_scene_state(self, scene_name: str) -> None:
        """Clear saved state for a scene.

        Args:
            scene_name: Name of the scene.
        """
        if scene_name in self._scene_states:
            del self._scene_states[scene_name]
