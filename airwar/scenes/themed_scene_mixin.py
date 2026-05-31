"""Mixin for scenes with themed military-style rendering."""
import math

import pygame

from airwar.ui.scene_rendering_utils import draw_themed_decorations, draw_themed_option_box, draw_themed_title


class ThemedSceneMixin:
    """Shared themed rendering methods for menu scenes."""

    def _draw_themed_title(self, surface: pygame.Surface, text: str, font: pygame.font.Font, pos: tuple) -> None:
        """Draw title in military style with amber glow."""
        draw_themed_title(surface, text, font, pos)

    def _draw_themed_decorations(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Draw military style decorations."""
        draw_themed_decorations(surface, width, height)

    def _draw_themed_option_box(
        self, surface: pygame.Surface, text: str, y: int,
        is_selected: bool, scale: float = 1.0
    ) -> None:
        """Draw option box in military style with chamfered corners."""
        draw_themed_option_box(
            surface, text, y, is_selected, self.option_font, self._option_rects,
            self.base_box_width, self.base_box_height, scale,
        )

    def update(self, *args, **kwargs) -> None:
        """Update animation state for background and particles."""
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED) * 8
        self._background_renderer.set_animation_time(self.animation_time)
        self._background_renderer.update()
        self._particle_system.set_animation_time(self.animation_time)
        self._particle_system.update(direction=-1)
