"""Scene base classes and scene management framework."""

from abc import ABC, abstractmethod
from enum import Enum

import pygame


class PauseAction(Enum):
    """Actions available from the pause menu.

    Attributes:
        RESUME: Resume the current game.
        MAIN_MENU: Return to main menu.
        SAVE_AND_QUIT: Save progress and quit.
        QUIT_WITHOUT_SAVING: Quit without saving.
        QUIT: 保存并退出（映射到 save_and_quit）。
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


class SceneError(Exception):
    """Base class for SceneManager transition errors.

    Mirrors the HSM discipline (IllegalPlayerTransition, IllegalBossTransition):
    a single root type lets callers `except SceneError` to catch all
    scene-level illegal transitions, while subclasses carry the specific
    failure mode.
    """


class SceneAlreadyActiveError(SceneError):
    """Raised when ``SceneManager.switch()`` is called with the scene that
    is already the active scene.

    Mirrors ``IllegalPlayerTransition`` and ``IllegalBossTransition``:
    makes silent no-op transitions loud, so callers can detect
    double-switch bugs (e.g. a button-click path that re-fires the same
    switch after the previous frame's switch already landed).
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"Scene '{name}' is already active")
        self.scene_name = name


class SceneNotRegisteredError(SceneError, KeyError):
    """Raised when ``SceneManager.switch()`` is called with a name that
    was never registered.

    Subclasses ``KeyError`` so legacy callers that catch ``KeyError`` on
    the old ``self._scenes[name]`` lookup keep working, while new code
    can opt into the explicit type.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"Scene '{name}' is not registered")
        self.scene_name = name


class SceneUnknownError(SceneError):
    """Raised when ``SceneManager.update()`` / ``render()`` /
    ``handle_events()`` is called while no scene is active.

    Catch-all for the "scene director forgot to switch to a scene"
    bug class. Previously the manager silently no-op'd when
    ``_current_scene`` was ``None`` -- hiding framework mis-wiring
    until a downstream consumer hit a ``None`` reference. Now the
    call surfaces a ``SceneUnknownError`` so the bug is loud at the
    source, mirroring ``IllegalPlayerTransition`` /
    ``IllegalBossTransition`` discipline.
    """

    def __init__(self, operation: str) -> None:
        super().__init__(f"SceneManager.{operation}() called with no active scene")
        self.operation = operation


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

    def is_running(self) -> bool:
        """Check if the scene is still active.

        Returns:
            True if the scene should continue running. Override in subclasses
            to implement custom exit conditions.
        """
        return True

    def is_ready(self) -> bool:
        """Return whether the scene has produced a result to advance.

        Subclasses such as ``WelcomeScene`` override this to signal that the
        player has finished interacting with the scene.
        """
        return False

    def get_username(self) -> str:
        """Return the username produced by this scene, if any.

        Override in subclasses that collect player identity.
        """
        return ""

    def get_difficulty(self) -> str:
        """Return the difficulty selected in this scene, if any.

        Override in subclasses that offer difficulty selection.
        """
        return "medium"

    def get_result(self) -> object | None:
        """Return the scene-specific result object, if any.

        Override in subclasses that produce a result payload.
        """
        return None


class SceneManager:
    """Manages scene registration and switching.

    Handles the lifecycle of scenes including registration, switching
    between scenes with proper enter/exit lifecycle calls.

    Attributes:
        _scenes: Dictionary of registered scenes by name.
        _current_scene: Currently active scene.
        _current_scene_name: Name of the current scene.
    """

    def __init__(self):
        self._scenes: dict[str, Scene] = {}
        self._current_scene: Scene | None = None
        self._current_scene_name: str = ""

    def register(self, name: str, scene: Scene, *, overwrite: bool = True) -> None:
        """Register a scene under a name.

        Args:
            name: Name used to later switch to the scene.
            scene: A concrete ``Scene`` instance.
            overwrite: If False, raise when ``name`` is already registered.

        Raises:
            TypeError: If ``scene`` is not a ``Scene`` instance.
            ValueError: If ``overwrite`` is False and ``name`` already exists.
        """
        if not isinstance(scene, Scene):
            raise TypeError(f"Expected Scene instance, got {type(scene).__name__}")
        if not overwrite and name in self._scenes:
            raise ValueError(f"Scene '{name}' is already registered")
        self._scenes[name] = scene

    def switch(self, name: str, **kwargs) -> None:
        """Switch to a named scene.

        Calls exit() on the current scene (if any), then enter() on the
        new scene with the provided keyword arguments.

        Args:
            name: Name of the scene to switch to.
            **kwargs: Data to pass to the new scene's enter() method.

        Raises:
            SceneAlreadyActiveError: If the target scene is already the
                current active scene.
            SceneNotRegisteredError: If the named scene was never
                ``register()``-ed.
            RuntimeError: If entering the new scene fails and the previous
                scene cannot be restored.
        """
        if name == self._current_scene_name and self._current_scene is not None:
            raise SceneAlreadyActiveError(name)
        if name not in self._scenes:
            raise SceneNotRegisteredError(name)

        old_scene = self._current_scene
        old_name = self._current_scene_name
        new_scene = self._scenes[name]

        if old_scene:
            old_scene.exit()

        self._current_scene = new_scene
        self._current_scene_name = name
        try:
            new_scene.enter(**kwargs)
        except Exception:
            self._current_scene = old_scene
            self._current_scene_name = old_name
            if old_scene is not None:
                try:
                    old_scene.enter()
                except Exception:
                    # If re-entering the old scene also fails, the framework
                    # is in an undefined state; surface it loudly.
                    raise RuntimeError(
                        f"Failed to enter scene '{name}' and could not restore scene '{old_name}'"
                    ) from None
            raise

    def get_current_scene(self) -> Scene | None:
        """Get the currently active scene instance.

        Returns:
            Scene instance or None if no scene is active.
        """
        return self._current_scene

    def get_current_scene_name(self) -> str:
        return self._current_scene_name

    def update(self, *args, **kwargs) -> None:
        """Update the currently active scene.

        Raises:
            SceneUnknownError: If no scene is currently active (caller
                forgot to ``switch()`` first).
        """
        if self._current_scene is None:
            raise SceneUnknownError("update")
        self._current_scene.update(*args, **kwargs)

    def render(self, surface: pygame.Surface) -> None:
        """Render the currently active scene.

        Args:
            surface: Pygame surface to render onto.

        Raises:
            SceneUnknownError: If no scene is currently active (caller
                forgot to ``switch()`` first).
        """
        if self._current_scene is None:
            raise SceneUnknownError("render")
        self._current_scene.render(surface)

    def handle_events(self, event: pygame.event.Event) -> None:
        """Dispatch a pygame event to the currently active scene.

        Args:
            event: Pygame event to dispatch.

        Raises:
            SceneUnknownError: If no scene is currently active (caller
                forgot to ``switch()`` first).
        """
        if self._current_scene is None:
            raise SceneUnknownError("handle_events")
        self._current_scene.handle_events(event)

    def get_scene(self, name: str) -> Scene | None:
        """Get a registered scene by name.

        Args:
            name: Name of the scene.

        Returns:
            The registered Scene instance, or None if not found.
        """
        return self._scenes.get(name)
