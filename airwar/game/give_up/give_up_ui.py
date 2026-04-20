import pygame
import math


class GiveUpUI:
    def __init__(self, screen_width: int, screen_height: int):
        self._visible = False
        self._progress = 0.0
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._animation_time = 0

        self._bar_width = 250
        self._bar_height = 16
        self._corner_radius = 8
        self._border_width = 2

        self._bg_color = (40, 10, 10)
        self._progress_color = (255, 60, 60)
        self._border_color = (200, 80, 80)
        self._text_color = (255, 100, 100)

        pygame.font.init()
        self._font = pygame.font.Font(None, 32)

    def show(self) -> None:
        self._visible = True
        self._progress = 0.0
        self._animation_time = 0

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0

    def update_progress(self, progress: float) -> None:
        if self._visible and progress > 0:
            self._progress = progress
        self._animation_time += 1

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible or self._progress <= 0:
            return

        center_x = self._screen_width // 2
        center_y = 60

        alpha = 180 + int(75 * math.sin(self._animation_time * 0.2))

        self._render_text(surface, center_x, center_y - 30, alpha)
        self._render_progress_bar(surface, center_x, center_y, alpha)

    def _render_text(self, surface: pygame.Surface, center_x: int, y: int, alpha: int) -> None:
        text = self._font.render("GIVE UP", True, self._text_color)
        text.set_alpha(alpha)
        text_rect = text.get_rect(center=(center_x, y))
        surface.blit(text, text_rect)

    def _render_progress_bar(self, surface: pygame.Surface, center_x: int, center_y: int, alpha: int) -> None:
        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2

        bg_surface = pygame.Surface((self._bar_width, self._bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            bg_surface, (*self._bg_color, 200),
            (0, 0, self._bar_width, self._bar_height),
            border_radius=self._corner_radius
        )
        surface.blit(bg_surface, (bar_x, bar_y))

        pygame.draw.rect(
            surface, (*self._border_color, alpha),
            (bar_x, bar_y, self._bar_width, self._bar_height),
            self._border_width,
            border_radius=self._corner_radius
        )

        progress_width = int(self._bar_width * self._progress)
        if progress_width > 0:
            progress_surface = pygame.Surface((progress_width, self._bar_height), pygame.SRCALPHA)
            pygame.draw.rect(
                progress_surface, (*self._progress_color, 220),
                (0, 0, progress_width, self._bar_height),
                border_radius=self._corner_radius
            )
            surface.blit(progress_surface, (bar_x, bar_y))

            if progress_width > 4:
                highlight_surface = pygame.Surface((progress_width - 4, 4), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surface, (255, 150, 150, 100), (0, 0, progress_width - 4, 4))
                surface.blit(highlight_surface, (bar_x + 2, bar_y + 2))
