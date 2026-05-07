"""Game config — singleton configuration with fixed logical sizing."""
from typing import Tuple
import pygame


class GameConfig:
    """Game config singleton — manages logical and display dimensions.
    
        Game logic always uses the fixed logical size. The physical display
        size is tracked separately for the window and scaled rendering.
        """
    _instance = None
    LOGICAL_WIDTH = 1920
    LOGICAL_HEIGHT = 1080

    def __init__(self):
        if GameConfig._instance is not None:
            raise RuntimeError("Use get_instance() to get GameConfig")
        self._screen_width = self.LOGICAL_WIDTH
        self._screen_height = self.LOGICAL_HEIGHT
        self._display_width = self.LOGICAL_WIDTH
        self._display_height = self.LOGICAL_HEIGHT
        self._fps = 60

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def screen_width(self) -> int:
        return self.get_screen_width()

    @property
    def screen_height(self) -> int:
        return self.get_screen_height()

    @property
    def screen_size(self) -> Tuple[int, int]:
        return (self._screen_width, self._screen_height)

    @property
    def display_width(self) -> int:
        return self.get_display_width()

    @property
    def display_height(self) -> int:
        return self.get_display_height()

    @property
    def display_size(self) -> Tuple[int, int]:
        return (self._display_width, self._display_height)

    @property
    def fps(self) -> int:
        return self._fps

    def get_screen_width(self) -> int:
        return self._screen_width

    def get_screen_height(self) -> int:
        return self._screen_height

    def get_display_width(self) -> int:
        return self._display_width

    def get_display_height(self) -> int:
        return self._display_height

    def set_display_size(self, width: int, height: int) -> None:
        self._display_width = width
        self._display_height = height

    def get_adaptive_screen_size(self) -> Tuple[int, int]:
        info = pygame.display.Info()
        max_width = info.current_w - 40
        max_height = info.current_h - 80

        target_width = self._screen_width
        target_height = self._screen_height

        if target_width > max_width:
            scale = max_width / target_width
            target_width = max_width
            target_height = int(target_height * scale)

        if target_height > max_height:
            scale = max_height / target_height
            target_height = max_height
            target_width = int(target_width * scale)

        return (target_width, target_height)


def get_screen_width() -> int:
    return GameConfig.get_instance().screen_width

def get_screen_height() -> int:
    return GameConfig.get_instance().screen_height

def get_display_width() -> int:
    return GameConfig.get_instance().display_width

def get_display_height() -> int:
    return GameConfig.get_instance().display_height

def set_display_size(width: int, height: int) -> None:
    GameConfig.get_instance().set_display_size(width, height)
