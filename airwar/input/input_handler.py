"""Input handler — pygame input processing."""

from abc import ABC, abstractmethod

import pygame

from airwar.entities.base import Vector2


class InputHandler(ABC):
    """Abstract input handler — interface for player input providers."""

    DEFAULT_BINDINGS: dict[str, int] = {
        "left": pygame.K_LEFT,
        "left_alt": pygame.K_a,
        "right": pygame.K_RIGHT,
        "right_alt": pygame.K_d,
        "up": pygame.K_UP,
        "up_alt": pygame.K_w,
        "down": pygame.K_DOWN,
        "down_alt": pygame.K_s,
        "pause": pygame.K_ESCAPE,
        "boost": pygame.K_LSHIFT,
        "precision": pygame.K_LCTRL,
    }

    @abstractmethod
    def get_movement_direction(self) -> Vector2:
        pass

    @abstractmethod
    def is_pause_pressed(self) -> bool:
        pass

    @abstractmethod
    def is_boost_pressed(self) -> bool:
        pass

    @abstractmethod
    def is_boost_just_pressed(self) -> bool:
        pass

    @abstractmethod
    def is_precision_pressed(self) -> bool:
        pass

    @abstractmethod
    def is_precision_just_pressed(self) -> bool:
        pass

    @abstractmethod
    def tick(self) -> None:
        """Read current input state and update edge-detection state."""
        pass


class PygameInputHandler(InputHandler):
    """Pygame input handler — reads keyboard input from pygame events.

    Provides movement direction, fire state, and action button state
    based on current pygame key presses.
    """

    _REQUIRED_BINDINGS: set[str] = {
        "left", "left_alt", "right", "right_alt",
        "up", "up_alt", "down", "down_alt",
        "pause", "boost", "precision",
    }

    def __init__(self, key_bindings: dict[str, int] | None = None):
        self._bindings = dict(key_bindings) if key_bindings is not None else dict(self.DEFAULT_BINDINGS)
        missing = self._REQUIRED_BINDINGS - self._bindings.keys()
        if missing:
            raise ValueError(f"Missing key bindings: {sorted(missing)}")
        for action, key in self._bindings.items():
            if not isinstance(key, int) or key < 0 or not pygame.key.name(key):
                raise ValueError(
                    f"Invalid key binding for '{action}': {key!r} (must be a valid pygame key constant)"
                )
        self._prev_boost_pressed = False
        self._boost_just_pressed = False
        self._prev_precision_pressed = False
        self._precision_just_pressed = False

    def get_movement_direction(self) -> Vector2:
        """Return the normalized movement direction from keyboard input.

        Opposite direction keys are resolved by later assignments overriding
        earlier ones: right overrides left, and down overrides up. Callers
        that need neutral-opposite behavior must handle that at a higher
        level.
        """
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        if keys[self._bindings["left"]] or keys[self._bindings["left_alt"]]:
            dx = -1
        if keys[self._bindings["right"]] or keys[self._bindings["right_alt"]]:
            dx = 1
        if keys[self._bindings["up"]] or keys[self._bindings["up_alt"]]:
            dy = -1
        if keys[self._bindings["down"]] or keys[self._bindings["down_alt"]]:
            dy = 1

        vec = Vector2(dx, dy)
        return vec.normalize() if vec.length() > 0 else vec

    def is_pause_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings["pause"]]

    def tick(self) -> None:
        """Read current key states and update edge-detection state."""
        keys = pygame.key.get_pressed()
        boost = keys[self._bindings["boost"]]
        self._boost_just_pressed = boost and not self._prev_boost_pressed
        self._prev_boost_pressed = boost
        precision = keys[self._bindings["precision"]]
        self._precision_just_pressed = precision and not self._prev_precision_pressed
        self._prev_precision_pressed = precision

    def is_boost_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings["boost"]]

    def is_boost_just_pressed(self) -> bool:
        just_pressed = self._boost_just_pressed
        self._boost_just_pressed = False
        return just_pressed

    def is_precision_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings["precision"]]

    def is_precision_just_pressed(self) -> bool:
        just_pressed = self._precision_just_pressed
        self._precision_just_pressed = False
        return just_pressed
