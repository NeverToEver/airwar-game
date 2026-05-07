"""Scaled logical viewport for fixed-resolution game rendering."""
from __future__ import annotations

from typing import Tuple

import pygame


class ScaledViewport:
    """Render a fixed logical surface into an arbitrary display surface."""

    def __init__(self, logical_w: int = 1920, logical_h: int = 1080):
        self.logical_size = (logical_w, logical_h)
        self._scale = 1.0
        self._offset = (0.0, 0.0)
        self._logical_surface = pygame.Surface((logical_w, logical_h))

    def update(self, display_w: int, display_h: int) -> None:
        scale_x = display_w / self.logical_size[0]
        scale_y = display_h / self.logical_size[1]
        self._scale = min(scale_x, scale_y)
        self._offset = (
            (display_w - self.logical_size[0] * self._scale) / 2,
            (display_h - self.logical_size[1] * self._scale) / 2,
        )

    def screen_to_logical(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        x = (screen_x - self._offset[0]) / self._scale
        y = (screen_y - self._offset[1]) / self._scale
        return (
            max(0.0, min(x, float(self.logical_size[0]))),
            max(0.0, min(y, float(self.logical_size[1]))),
        )

    def present(self, display_surface: pygame.Surface) -> None:
        scaled_size = (
            int(self.logical_size[0] * self._scale),
            int(self.logical_size[1] * self._scale),
        )
        scaled = pygame.transform.scale(self._logical_surface, scaled_size)
        display_surface.fill((0, 0, 0))
        display_surface.blit(scaled, self._offset)

    @property
    def logical_surface(self) -> pygame.Surface:
        return self._logical_surface
