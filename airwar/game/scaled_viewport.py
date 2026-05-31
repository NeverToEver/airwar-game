"""Scaled logical viewport for fixed-resolution game rendering."""
from __future__ import annotations

import pygame


class ScaledViewport:
    """Render a fixed logical surface into an arbitrary display surface.

    With the pygame SCALED flag, SDL2's GPU-accelerated renderer handles
    window-level scaling, so this viewport only needs a 1:1 blit.
    """

    def __init__(self, logical_w: int = 1920, logical_h: int = 1080):
        self.logical_size = (logical_w, logical_h)
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._logical_surface = pygame.Surface((logical_w, logical_h), pygame.SRCALPHA)

    def update(self, display_w: int, display_h: int) -> None:
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
        if self._scale <= 0:
            return (0.0, 0.0)
        x = (screen_x - self._offset[0]) / self._scale
        y = (screen_y - self._offset[1]) / self._scale
        return (
            max(0.0, min(x, float(self.logical_size[0]))),
            max(0.0, min(y, float(self.logical_size[1]))),
        )

    def present(self, display_surface: pygame.Surface) -> None:
        # The SCALED flag means SDL2's GPU renderer handles scaling.
        # The display surface is always at the logical resolution, so a
        # 1:1 blit is all that's needed; SDL2 scales to the actual window.
        display_surface.blit(self._logical_surface, (0, 0))

    @property
    def logical_surface(self) -> pygame.Surface:
        return self._logical_surface
