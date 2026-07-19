"""Window — resizable display window with event handling."""

from __future__ import annotations

import logging
import os

import pygame

from airwar.config import set_display_size

logger = logging.getLogger(__name__)

# Prefer GPU-accelerated SDL2 render backend on Linux.
# On Windows this is handled by the direct3d default.
if not os.environ.get("SDL_RENDER_DRIVER"):
    os.environ["SDL_RENDER_DRIVER"] = "opengl"

# P2: selectable window tiers, all locked to 16:9. Only the OS window
# size changes between tiers; the logical render surface stays at the
# display mode size and SDL2 SCALED handles the GPU-side stretching.
RESOLUTION_TIERS: dict[str, tuple[int, int]] = {
    "S": (1280, 720),
    "M": (1920, 1080),
    "L": (2560, 1440),
}
DEFAULT_RESOLUTION_TIER = "M"


class Window:
    """Resizable pygame window with event handling and mode management."""

    def __init__(self, width: int = 1920, height: int = 1080, title: str = "Air War", resizable: bool = True):
        self._running = False
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._default_width = width
        self._default_height = height
        self._width = width
        self._height = height
        self._title = title
        self._resizable = resizable
        self._min_size = (1280, 720)
        self._max_size = (2560, 1440)
        self._is_fullscreen = False
        self._windowed_size = (width, height)

    def init(self, width: int | None = None, height: int | None = None) -> None:
        pygame.init()

        flags = pygame.DOUBLEBUF | pygame.SCALED
        if self._resizable:
            flags |= pygame.RESIZABLE
        # The display surface is always the fixed logical resolution
        # (default 1920x1080). SDL2 SCALED stretches it to whatever the
        # OS window size is, so game coordinates never change.
        self._screen = pygame.display.set_mode((self._default_width, self._default_height), flags)
        pygame.display.set_caption(self._title)
        self._clock = pygame.time.Clock()
        self._running = True
        set_display_size(self._default_width, self._default_height)

        if width is not None and height is not None:
            win_w, win_h = width, height
        else:
            win_w, win_h = self._get_adaptive_size()
        self._width = win_w
        self._height = win_h
        self._windowed_size = (win_w, win_h)
        self._set_os_window_size(win_w, win_h)

    def _set_os_window_size(self, width: int, height: int) -> None:
        """Resize the OS window without touching the logical display surface."""
        if self._screen is None or pygame.display.get_surface() is None:
            return
        if (width, height) == (self._default_width, self._default_height):
            # The window is already created at the logical size.
            return
        try:
            from pygame._sdl2 import video as sdl2_video

            sdl2_video.Window.from_display_module().size = (width, height)
        except Exception:
            # Fallback for environments without the SDL2 window handle:
            # recreate the mode at the requested size. This changes the
            # display surface size, so the viewport letterbox path takes
            # over for presentation.
            logger.warning("SDL2 window handle unavailable; recreating display mode at %sx%s", width, height)
            flags = pygame.DOUBLEBUF | pygame.SCALED
            if self._resizable:
                flags |= pygame.RESIZABLE
            self._screen = pygame.display.set_mode((width, height), flags)

    def _get_adaptive_size(self) -> tuple[int, int]:
        """Largest 16:9 window size that fits the desktop.

        Only the OS window is sized; the logical render surface stays at
        the default resolution either way.
        """
        try:
            info = pygame.display.Info()
            max_width = info.current_w - 40
            max_height = info.current_h - 80
            width = min(self._default_width, max_width, max_height * 16 // 9)
            if width <= 0:
                return (self._default_width, self._default_height)
            return (width, width * 9 // 16)
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

    def get_size(self) -> tuple[int, int]:
        # get_window_size() returns the actual pixel dimensions of the OS window.
        # With SCALED, the display surface is always at the logical resolution
        # (e.g. 1920x1080), but the window itself may be larger or smaller.
        # Mouse events use OS window coordinates, so that's what callers need.
        try:
            return pygame.display.get_window_size()
        except (pygame.error, AttributeError):
            pass
        if self._screen:
            return self._screen.get_size()
        return (self._width, self._height)

    def get_width(self) -> int:
        return self.get_size()[0]

    def get_height(self) -> int:
        return self.get_size()[1]

    def get_surface(self) -> pygame.Surface:
        assert self._screen is not None
        return self._screen

    def get_clock(self) -> pygame.time.Clock:
        assert self._clock is not None
        return self._clock

    def set_title(self, title: str) -> None:
        self._title = title
        pygame.display.set_caption(title)

    def resize(self, width: int, height: int) -> None:
        """Resize the OS window, clamped to the tier range and locked to 16:9.

        The display surface stays at the fixed logical resolution; SDL2
        SCALED handles the visual scaling, so game coordinates and the
        mouse transform are unaffected by the aspect lock.
        """
        if self._is_fullscreen:
            return

        width = max(self._min_size[0], min(width, self._max_size[0]))
        height = width * 9 // 16  # aspect-locked: 16:9
        self._width = width
        self._height = height
        self._windowed_size = (width, height)
        self._set_os_window_size(width, height)

    def set_resolution_tier(self, tier: str) -> bool:
        """Apply a P2 resolution tier ("S" / "M" / "L"). Returns True if applied."""
        size = RESOLUTION_TIERS.get(tier)
        if size is None:
            return False
        self.resize(*size)
        return True

    def flip(self) -> None:
        if self._screen:
            pygame.display.flip()

    def update(self) -> None:
        if self._screen:
            pygame.display.update()

    def tick(self, fps: int = 60) -> float:
        """Wait for the frame cap and return elapsed wall time in seconds."""
        if self._clock:
            return self._clock.tick_busy_loop(fps) / 1000.0
        return 0.0

    def reset_timing(self) -> None:
        """Discard elapsed time accumulated while a scene was loading."""
        if self._clock:
            self._clock.tick(0)

    def get_events(self) -> list[pygame.event.Event]:
        return pygame.event.get()

    def process_events(self) -> tuple[bool, pygame.event.Event | None, tuple[int, int] | None]:
        quit_event = None
        resize_event = None
        keydown_event = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_event = event
            elif event.type == pygame.VIDEORESIZE:
                # With SCALED, SDL2 handles scaling — track the window size
                # for the mouse transform; the surface stays at logical size.
                self._width = event.w
                self._height = event.h
                resize_event = (event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                keydown_event = event

        return quit_event is not None, keydown_event, resize_event

    def clear(self, color: tuple[int, int, int] = (0, 0, 0)) -> None:
        if self._screen:
            self._screen.fill(color)

    def blit(self, surface: pygame.Surface, pos: tuple[int, int]) -> None:
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
            # Back to windowed: the display surface returns to the fixed
            # logical resolution with SCALED; the OS window is restored
            # to its previous size separately.
            flags = pygame.DOUBLEBUF | pygame.SCALED
            if self._resizable:
                flags |= pygame.RESIZABLE
            try:
                self._screen = pygame.display.set_mode((self._default_width, self._default_height), flags)
            except pygame.error:
                self._screen = pygame.display.set_mode((self._default_width, self._default_height), pygame.SHOWN)
            self._is_fullscreen = False
            self._set_os_window_size(*self._windowed_size)
            self._width, self._height = self._windowed_size
        else:
            info = pygame.display.Info()
            self._windowed_size = (self._width, self._height)
            self._width = info.current_w
            self._height = info.current_h
            # FULLSCREEN without SCALED — SCALED causes cropped/zoomed viewport
            # on pygame 2.6+ with certain SDL backends (X11/Wayland). The
            # ScaledViewport letterboxes the logical surface instead.
            try:
                self._screen = pygame.display.set_mode((self._width, self._height), pygame.FULLSCREEN)
            except pygame.error:
                # Fallback: borderless maximized window
                try:
                    self._screen = pygame.display.set_mode((self._width, self._height), pygame.NOFRAME)
                except pygame.error:
                    # Last resort: revert to windowed at the logical size
                    self._width, self._height = self._windowed_size
                    self._screen = pygame.display.set_mode(
                        (self._default_width, self._default_height),
                        pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE,
                    )
                    self._is_fullscreen = False
                    self._set_os_window_size(*self._windowed_size)
                    return
            self._is_fullscreen = True

    def is_fullscreen(self) -> bool:
        return self._is_fullscreen


_window_instance: Window | None = None


def get_window() -> Window:
    global _window_instance
    if _window_instance is None:
        _window_instance = Window()
    return _window_instance


def create_window(width: int = 1400, height: int = 800, title: str = "Air War", resizable: bool = True) -> Window:
    global _window_instance
    _window_instance = Window(width, height, title, resizable)
    _window_instance.init()
    return _window_instance
