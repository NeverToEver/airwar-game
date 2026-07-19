"""Scaled logical viewport for fixed-resolution game rendering."""

from __future__ import annotations

import pygame


class ScaledViewport:
    """Render a fixed logical surface into an arbitrary display surface.

    With the pygame SCALED flag, SDL2's GPU-accelerated renderer handles
    window-level scaling, so this viewport only needs a 1:1 blit.
    """

    def __init__(self, logical_w: int = 1920, logical_h: int = 1080):
        if logical_w <= 0 or logical_h <= 0:
            raise ValueError(f"logical size must be positive, got ({logical_w}, {logical_h})")
        self._logical_size = (logical_w, logical_h)
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._logical_surface = pygame.Surface((logical_w, logical_h), pygame.SRCALPHA)
        # Cached window size behind the mouse transform; the transform
        # is only recomputed when the OS window size actually changes.
        self._window_size: tuple[int, int] | None = None
        # Single-entry cache for the fullscreen letterbox path:
        # (display_size, scaled_size, letterbox_offset, scratch_surface).
        self._present_cache: tuple[tuple[int, int], tuple[int, int], tuple[int, int], pygame.Surface] | None = None

    @property
    def logical_size(self) -> tuple[int, int]:
        """Logical design-time resolution (width, height).

        This value is read-only from the outside. To resize the viewport,
        construct a new instance or call ``update(display_w, display_h)``
        to adjust the display-to-logical transform.
        """
        return self._logical_size

    @logical_size.setter
    def logical_size(self, value: tuple[int, int]) -> None:
        w, h = value
        if w <= 0 or h <= 0:
            raise ValueError(f"logical size must be positive, got ({w}, {h})")
        self._logical_size = (w, h)
        self._logical_surface = pygame.Surface((w, h), pygame.SRCALPHA)

    def update(self, display_w: int, display_h: int) -> None:
        """Compute the transform that maps display-space mouse coords
        into logical-space coords (the design-time 1920x1080 surface).

        Aspect-preserving fit: the entire logical surface fits inside
        the display with a black letterbox on the shorter axis. This
        is the case when the user resizes a window larger than the
        design resolution.

        Note: callers that pass the actual window size AS the
        ``logical_w``/``logical_h`` at construction time (e.g. ``Game``
        using ``_get_adaptive_size``) will see a no-op transform
        because ``display_w == logical_w`` and ``display_h ==
        logical_h``. That's the intended path for adaptive windows.
        """
        if display_w <= 0 or display_h <= 0:
            self._scale = 0.0
            self._offset = (0.0, 0.0)
            return
        self._scale = min(
            display_w / self.logical_size[0],
            display_h / self.logical_size[1],
        )
        self._offset = (
            (display_w - self.logical_size[0] * self._scale) / 2,
            (display_h - self.logical_size[1] * self._scale) / 2,
        )

    def screen_to_logical(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        self._sync_window_transform()
        if self._scale <= 0:
            return (0.0, 0.0)
        x = (screen_x - self._offset[0]) / self._scale
        y = (screen_y - self._offset[1]) / self._scale
        return (
            max(0.0, min(x, float(self.logical_size[0]))),
            max(0.0, min(y, float(self.logical_size[1]))),
        )

    def _sync_window_transform(self) -> None:
        """Refresh the mouse transform from the live OS window size.

        Self-synchronizing: callers never need to push resize events
        here. The transform is cached and only recomputed when the
        window size actually changes, so per-frame mouse mapping stays
        O(1). Headless environments (no display surface) keep whatever
        transform was last set via ``update``.
        """
        if not pygame.display.get_init() or pygame.display.get_surface() is None:
            return
        try:
            size = pygame.display.get_window_size()
        except pygame.error:
            return
        if size != self._window_size:
            self._window_size = size
            self.update(*size)

    def present(self, display_surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        display_size = display_surface.get_size()
        if display_size == self._logical_size:
            # Windowed SCALED path: the display surface is at the logical
            # resolution and SDL2's GPU renderer scales it to the window,
            # so a 1:1 blit is all that's needed. ``offset`` shifts the
            # logical surface for screen-shake effects (JuiceController).
            if offset == (0, 0):
                display_surface.blit(self._logical_surface, (0, 0))
            else:
                display_surface.blit(self._logical_surface, offset)
            return
        # Fullscreen / non-SCALED path: the display surface is larger
        # than (or differs from) the logical surface — letterbox with
        # black bars so the picture never distorts. The transform and
        # scratch surface are cached per display size (space-for-time:
        # one scale + one blit per frame, no per-frame allocation).
        cache = self._present_cache
        if cache is None or cache[0] != display_size:
            lw, lh = self._logical_size
            scale = min(display_size[0] / lw, display_size[1] / lh)
            scaled_size = (max(1, int(lw * scale)), max(1, int(lh * scale)))
            letterbox = (
                (display_size[0] - scaled_size[0]) // 2,
                (display_size[1] - scaled_size[1]) // 2,
            )
            cache = (display_size, scaled_size, letterbox, pygame.Surface(scaled_size))
            self._present_cache = cache
        _, scaled_size, letterbox, scratch = cache
        pygame.transform.scale(self._logical_surface, scaled_size, scratch)
        display_surface.fill((0, 0, 0))
        display_surface.blit(scratch, (letterbox[0] + offset[0], letterbox[1] + offset[1]))

    @property
    def logical_surface(self) -> pygame.Surface:
        return self._logical_surface
