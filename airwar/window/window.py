"""Window — resizable display window with event handling."""
import pygame
from typing import Optional, Tuple, List
from airwar.config import set_screen_size


class Window:
    """Resizable pygame window with event handling and mode management."""
    def __init__(self, width: int = 1400, height: int = 800, title: str = 'Air War', resizable: bool = True):
        self._running = False
        self._screen: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._default_width = width
        self._default_height = height
        self._width = width
        self._height = height
        self._title = title
        self._resizable = resizable
        self._min_size = (800, 600)
        self._max_size = (1920, 1080)
        self._is_fullscreen = False
        self._windowed_size = (width, height)

    def init(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        pygame.init()
        
        if width is not None and height is not None:
            self._width = width
            self._height = height
        else:
            self._width, self._height = self._get_adaptive_size()

        flags = pygame.RESIZABLE | pygame.SCALED if self._resizable else pygame.SCALED
        self._screen = pygame.display.set_mode((self._width, self._height), flags)
        pygame.display.set_caption(self._title)
        self._clock = pygame.time.Clock()
        self._running = True
        set_screen_size(self._width, self._height)

    def _get_adaptive_size(self) -> Tuple[int, int]:
        try:
            info = pygame.display.Info()
            max_width = info.current_w - 40
            max_height = info.current_h - 80

            target_width = self._default_width
            target_height = self._default_height

            if target_width > max_width:
                scale = max_width / target_width
                target_width = max_width
                target_height = int(target_height * scale)

            if target_height > max_height:
                scale = max_height / target_height
                target_height = max_height
                target_width = int(target_width * scale)

            return (target_width, target_height)
        except pygame.error:
            return (self._default_width, self._default_height)

    def close(self) -> None:
        self._running = False
        if self._screen:
            pygame.display.quit()
        pygame.quit()

    def is_running(self) -> bool:
        return self._running

    def set_running(self, running: bool) -> None:
        self._running = running

    def get_size(self) -> Tuple[int, int]:
        if self._screen:
            return self._screen.get_size()
        return (self._width, self._height)

    def get_width(self) -> int:
        return self.get_size()[0]

    def get_height(self) -> int:
        return self.get_size()[1]

    def get_surface(self) -> pygame.Surface:
        return self._screen

    def get_clock(self) -> pygame.time.Clock:
        return self._clock

    def set_title(self, title: str) -> None:
        self._title = title
        pygame.display.set_caption(title)

    def resize(self, width: int, height: int) -> None:
        if self._is_fullscreen:
            return

        width = max(self._min_size[0], min(width, self._max_size[0]))
        height = max(self._min_size[1], min(height, self._max_size[1]))
        self._width = width
        self._height = height
        if self._screen:
            self._screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.SCALED)
        set_screen_size(width, height)

    def flip(self) -> None:
        if self._screen:
            pygame.display.flip()

    def update(self) -> None:
        if self._screen:
            pygame.display.update()

    def tick(self, fps: int = 60) -> None:
        if self._clock:
            self._clock.tick(fps)

    def get_events(self) -> List[pygame.event.Event]:
        return pygame.event.get()

    def process_events(self) -> Tuple[bool, Optional[pygame.event.Event], Optional[Tuple[int, int]]]:
        quit_event = None
        resize_event = None
        keydown_event = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_event = event
            elif event.type == pygame.VIDEORESIZE:
                self.resize(event.w, event.h)
                resize_event = (event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                keydown_event = event

        return quit_event is not None, keydown_event, resize_event

    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        if self._screen:
            self._screen.fill(color)

    def blit(self, surface: pygame.Surface, pos: Tuple[int, int]) -> None:
        if self._screen:
            self._screen.blit(surface, pos)

    def get_fps(self) -> float:
        if self._clock:
            return self._clock.get_fps()
        return 0.0

    def toggle_fullscreen(self) -> None:
        if self._screen is None:
            return

        if self._is_fullscreen:
            self._width, self._height = self._windowed_size
            flags = (pygame.RESIZABLE | pygame.SCALED) if self._resizable else pygame.SCALED
            try:
                self._screen = pygame.display.set_mode((self._width, self._height), flags)
            except pygame.error:
                self._screen = pygame.display.set_mode((self._width, self._height), pygame.SHOWN)
            self._is_fullscreen = False
        else:
            info = pygame.display.Info()
            self._windowed_size = (self._width, self._height)
            self._width = info.current_w
            self._height = info.current_h
            flags = pygame.FULLSCREEN | pygame.SCALED
            if self._resizable:
                flags |= pygame.RESIZABLE
            try:
                self._screen = pygame.display.set_mode((self._width, self._height), flags)
            except pygame.error:
                # Fallback: try without FULLSCREEN (borderless maximized)
                try:
                    self._screen = pygame.display.set_mode(
                        (self._width, self._height),
                        pygame.NOFRAME | pygame.SCALED)
                except pygame.error:
                    # Last resort: revert to original windowed size
                    self._width, self._height = self._windowed_size
                    self._screen = pygame.display.set_mode(
                        (self._width, self._height),
                        pygame.RESIZABLE | pygame.SCALED)
                    self._is_fullscreen = False
                    return
            self._is_fullscreen = True
        self._width, self._height = self._screen.get_size()
        set_screen_size(self._width, self._height)

    def is_fullscreen(self) -> bool:
        return self._is_fullscreen


_window_instance: Optional[Window] = None


def get_window() -> Window:
    global _window_instance
    if _window_instance is None:
        _window_instance = Window()
    return _window_instance


def create_window(width: int = 1400, height: int = 800, title: str = 'Air War', resizable: bool = True) -> Window:
    global _window_instance
    _window_instance = Window(width, height, title, resizable)
    _window_instance.init()
    return _window_instance
