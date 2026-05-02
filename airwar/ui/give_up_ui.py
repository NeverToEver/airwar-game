"""Give-up UI — surrender progress indicator overlay."""
import pygame
from airwar.utils.fonts import get_cjk_font
import math
from airwar.config.design_tokens import get_design_tokens, SceneColors, SystemColors, SystemUI
from airwar.ui.chamfered_panel import draw_chamfered_panel


class GiveUpUI:
    """Give-up UI — surrender progress indicator overlay.
    
        Shows a progress bar that fills as the player holds the surrender key.
        """
    def __init__(self, screen_width: int, screen_height: int):
        self._visible = False
        self._progress = 0.0
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._animation_time = 0
        self._use_themed_style = True

        self._tokens = get_design_tokens()
        colors = self._tokens.colors

        self._bar_width = 250
        self._bar_height = 16
        self._corner_radius = 8
        self._border_width = 2

        self._bg_color = SystemColors.GIVE_UP_BG
        self._progress_color = colors.HEALTH_DANGER
        self._border_color = colors.WARNING
        self._text_color = colors.HEALTH_DANGER

        pygame.font.init()
        self._font = get_cjk_font(self._tokens.typography.BODY_SIZE)

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

        if self._use_themed_style:
            self._render_glow_text(surface, center_x, center_y - 30, alpha)
            self._render_themed_progress_bar(surface, center_x, center_y, alpha)
        else:
            self._render_text(surface, center_x, center_y - 30, alpha)
            self._render_progress_bar(surface, center_x, center_y, alpha)

    def _render_glow_text(self, surface: pygame.Surface, center_x: int, y: int, alpha: int) -> None:
        """Render text in military style."""
        text = self._font.render("投降", True, SceneColors.DANGER_RED)
        text.set_alpha(alpha)
        text_rect = text.get_rect(center=(center_x, y))
        surface.blit(text, text_rect)

    def _render_themed_progress_bar(self, surface: pygame.Surface, center_x: int, center_y: int, alpha: int) -> None:
        """Render progress bar in military style with chamfered corners."""
        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2

        # Draw chamfered background
        draw_chamfered_panel(
            surface,
            bar_x, bar_y,
            self._bar_width, self._bar_height,
            SceneColors.BG_PANEL_LIGHT,
            SceneColors.DANGER_RED,
            None,
            4
        )

        progress_width = int(self._bar_width * self._progress)
        if progress_width > 4:
            # Draw chamfered progress fill
            draw_chamfered_panel(
                surface,
                bar_x + 2, bar_y + 2,
                progress_width - 4, self._bar_height - 4,
                SceneColors.DANGER_RED,
                SceneColors.DANGER_RED,
                None,
                4
            )

    def _render_text(self, surface: pygame.Surface, center_x: int, y: int, alpha: int) -> None:
        text = self._font.render("投降", True, self._text_color)
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
