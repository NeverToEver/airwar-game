import pygame
from typing import Optional
from .interfaces import IMotherShipUI
from airwar.utils.render_cache import SurfaceCache


class ProgressBarUI(IMotherShipUI):
    def __init__(self, screen_width: int, screen_height: int):
        self._visible = False
        self._progress = 0.0
        self._screen_width = screen_width
        self._screen_height = screen_height

        self._bar_width = 300
        self._bar_height = 20
        self._corner_radius = 10
        self._border_width = 2

        self._bg_color = (30, 30, 50, 200)
        self._progress_color_inactive = (80, 80, 120)
        self._progress_color_active = (60, 180, 255)
        self._progress_color_complete = (80, 255, 120)
        self._border_color = (120, 120, 160)

        self._completion_animation_progress = 0.0
        self._is_playing_complete_animation = False

        pygame.font.init()
        self._font = pygame.font.Font(None, 24)
        self._icon_surface = self._build_mothership_icon()

    def show(self) -> None:
        self._visible = True
        self._progress = 0.0
        self._is_playing_complete_animation = False

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0
        self._is_playing_complete_animation = False

    def update_progress(self, progress: float) -> None:
        if self._visible:
            self._progress = progress

    def play_complete_animation(self) -> None:
        self._is_playing_complete_animation = True
        self._completion_animation_progress = 0.0

    def resize(self, screen_width: int, screen_height: int) -> None:
        self._screen_width = screen_width
        self._screen_height = screen_height

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        center_x = self._screen_width // 2
        center_y = self._screen_height - 150

        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2

        self._render_mothership_icon(surface, center_x, center_y - 60)

        if self._is_playing_complete_animation:
            self._render_complete_animation(surface, center_x, center_y, bar_x, bar_y)
        else:
            self._render_progress_bar(surface, bar_x, bar_y)
            self._render_progress_text(surface, center_x, center_y)

    def _render_progress_bar(self, surface: pygame.Surface, bar_x: int, bar_y: int) -> None:
        bg_rect = pygame.Rect(bar_x, bar_y, self._bar_width, self._bar_height)

        bg_surface = SurfaceCache.get_rect_fill(
            self._bar_width,
            self._bar_height,
            self._bg_color,
            border_radius=self._corner_radius,
        )
        surface.blit(bg_surface, (bar_x, bar_y))

        surface.blit(
            SurfaceCache.get_rect_border(
                self._bar_width,
                self._bar_height,
                self._border_color,
                border_width=self._border_width,
                border_radius=self._corner_radius,
            ),
            (bar_x, bar_y),
        )

        progress_width = int(self._bar_width * self._progress)
        if progress_width > 0:
            progress_color = self._get_progress_color()
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, self._bar_height)
            progress_surface = SurfaceCache.get_rect_fill(
                progress_width,
                self._bar_height,
                (*progress_color, 200),
                border_radius=self._corner_radius,
            )
            surface.blit(progress_surface, (bar_x, bar_y))

            if progress_width > 4:
                highlight_rect = pygame.Rect(bar_x + 2, bar_y + 2, progress_width - 4, 4)
                highlight_surface = SurfaceCache.get_rect_fill(
                    progress_width - 4,
                    4,
                    (*progress_color, 100),
                )
                surface.blit(highlight_surface, (bar_x + 2, bar_y + 2))

    def _render_progress_text(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        seconds = int(self._progress * 3)
        text = self._font.render(f"HOLD {seconds}/3", True, (200, 200, 220))
        text_rect = text.get_rect(center=(center_x, center_y + 30))
        surface.blit(text, text_rect)

    def _build_mothership_icon(self) -> pygame.Surface:
        icon_width = 60
        icon_height = 50
        center_x = icon_width // 2
        center_y = icon_height // 2
        points = [
            (center_x, center_y - 20),
            (center_x + 25, center_y + 15),
            (center_x + 15, center_y + 10),
            (center_x + 15, center_y + 20),
            (center_x - 15, center_y + 20),
            (center_x - 15, center_y + 10),
            (center_x - 25, center_y + 15),
        ]

        mothership_surface = pygame.Surface((icon_width, icon_height), pygame.SRCALPHA)
        pygame.draw.polygon(mothership_surface, (180, 180, 220, 200), points)
        pygame.draw.polygon(mothership_surface, (100, 100, 140, 255), points, 2)
        return mothership_surface

    def _render_mothership_icon(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        surface.blit(self._icon_surface, (center_x - self._icon_surface.get_width() // 2, center_y - self._icon_surface.get_height() // 2))

    def _render_complete_animation(self, surface: pygame.Surface, center_x: int, center_y: int,
                                   bar_x: int, bar_y: int) -> None:
        self._completion_animation_progress += 0.05

        if self._completion_animation_progress >= 1.0:
            self._is_playing_complete_animation = False
            return

        scale = 1.0 + 0.1 * (1.0 - self._completion_animation_progress)
        alpha = 255 - int(255 * self._completion_animation_progress)

        original_bar_width = self._bar_width
        original_bar_height = self._bar_height

        scaled_bar_width = int(original_bar_width * scale)
        scaled_bar_height = int(original_bar_height * scale)

        scaled_x = center_x - scaled_bar_width // 2
        scaled_y = center_y - scaled_bar_height // 2

        progress_surface = SurfaceCache.get_rect_fill(
            scaled_bar_width,
            scaled_bar_height,
            (*self._progress_color_complete, alpha),
            border_radius=self._corner_radius,
        )
        surface.blit(progress_surface, (scaled_x, scaled_y))

    def _get_progress_color(self) -> tuple:
        if self._progress >= 1.0:
            return self._progress_color_complete
        elif self._progress >= 0.8:
            t = (self._progress - 0.8) / 0.2
            return self._lerp_color(self._progress_color_active, self._progress_color_complete, t)
        return self._progress_color_active

    def _lerp_color(self, color1: tuple, color2: tuple, t: float) -> tuple:
        return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))
