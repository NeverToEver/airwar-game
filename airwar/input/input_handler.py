"""Input handler — pygame input processing with mock support for testing."""
from abc import ABC, abstractmethod
from typing import Dict, Optional
import pygame
from airwar.entities.base import Vector2


class InputHandler(ABC):
    """Abstract input handler — interface for player input providers."""
    DEFAULT_BINDINGS: Dict[str, int] = {
        'left': pygame.K_LEFT,
        'left_alt': pygame.K_a,
        'right': pygame.K_RIGHT,
        'right_alt': pygame.K_d,
        'up': pygame.K_UP,
        'up_alt': pygame.K_w,
        'down': pygame.K_DOWN,
        'down_alt': pygame.K_s,
        'pause': pygame.K_ESCAPE,
        'boost': pygame.K_LSHIFT,
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


class PygameInputHandler(InputHandler):
    """Pygame input handler — reads keyboard input from pygame events.
    
        Provides movement direction, fire state, and action button state
        based on current pygame key presses.
        """
    def __init__(self, key_bindings: Optional[Dict[str, int]] = None):
        self._bindings = key_bindings or self.DEFAULT_BINDINGS

    def get_movement_direction(self) -> Vector2:
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        if keys[self._bindings['left']] or keys[self._bindings['left_alt']]:
            dx = -1
        if keys[self._bindings['right']] or keys[self._bindings['right_alt']]:
            dx = 1
        if keys[self._bindings['up']] or keys[self._bindings['up_alt']]:
            dy = -1
        if keys[self._bindings['down']] or keys[self._bindings['down_alt']]:
            dy = 1

        return Vector2(dx, dy)

    def is_pause_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings['pause']]

    def is_boost_pressed(self) -> bool:
        keys = pygame.key.get_pressed()
        return keys[self._bindings['boost']]


class MockInputHandler(InputHandler):
    """Mock input handler — programmable input for testing.
    
        Accepts preset movement directions and button states, allowing
        tests to simulate player input without pygame events.
        """
    def __init__(self):
        self._direction = Vector2(0, 0)
        self._pause_pressed = False
        self._boost_pressed = False

    def set_direction(self, dx: float, dy: float) -> None:
        self._direction = Vector2(dx, dy)

    def set_pause_pressed(self, pressed: bool) -> None:
        self._pause_pressed = pressed

    def set_boost_pressed(self, pressed: bool) -> None:
        self._boost_pressed = pressed

    def get_movement_direction(self) -> Vector2:
        return self._direction

    def is_pause_pressed(self) -> bool:
        return self._pause_pressed

    def is_boost_pressed(self) -> bool:
        return self._boost_pressed
