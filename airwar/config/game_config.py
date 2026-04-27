"""Game config — singleton configuration with adaptive screen sizing."""
from typing import Tuple
import pygame


class GameConfig:
    """Game config singleton — manages screen dimensions and scaling.
    
        Provides adaptive screen sizing functions and caches computed
        dimension values for the current display.
        """
    _instance = None

    def __init__(self):
        if GameConfig._instance is not None:
            raise RuntimeError("Use get_instance() to get GameConfig")
        self._screen_width = 1920
        self._screen_height = 1080
        self._fps = 60

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def screen_width(self) -> int:
        return self._screen_width

    @property
    def screen_height(self) -> int:
        return self._screen_height

    @property
    def screen_size(self) -> Tuple[int, int]:
        return (self._screen_width, self._screen_height)

    @property
    def fps(self) -> int:
        return self._fps

    def set_screen_size(self, width: int, height: int) -> None:
        self._screen_width = width
        self._screen_height = height

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

def set_screen_size(width: int, height: int) -> None:
    GameConfig.get_instance().set_screen_size(width, height)
