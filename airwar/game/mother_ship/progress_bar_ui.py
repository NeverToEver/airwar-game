"""Progress bar UI — visual docking progress indicator."""
import pygame
from airwar.utils.fonts import get_cjk_font
from .interfaces import IMotherShipUI


class ProgressBarUI(IMotherShipUI):
    """Progress bar UI — visual docking progress indicator."""
    BAR_TYPE_HOLD = "hold"
    BAR_TYPE_COOLDOWN = "cooldown"
    BAR_TYPE_STAY = "stay"

    def __init__(self, screen_width: int, screen_height: int):
        self._visible = False
        self._progress = 0.0
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._bar_type = self.BAR_TYPE_HOLD

        self._bar_width = 200
        self._bar_height = 10
        self._corner_radius = 5
        self._border_width = 1

        self._bg_color = (20, 20, 40, 180)
        self._progress_color_inactive = (60, 60, 100)
        self._progress_color_active = (60, 160, 220)
        self._progress_color_complete = (80, 220, 120)
        self._progress_color_cooldown = (160, 120, 50)
        self._progress_color_stay = (80, 180, 110)
        self._border_color = (100, 100, 140)

        self._completion_animation_progress = 0.0
        self._is_playing_complete_animation = False
        self._max_value = 3.0
        self._current_value = 0.0

        pygame.font.init()
        self._font = get_cjk_font(18)

    def show(self, bar_type: str = BAR_TYPE_HOLD, max_value: float = 3.0) -> None:
        self._visible = True
        self._progress = 0.0
        self._is_playing_complete_animation = False
        self._bar_type = bar_type
        self._max_value = max_value
        self._current_value = 0.0

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0
        self._is_playing_complete_animation = False

    def update_progress(self, progress: float, current_value: float = 0.0) -> None:
        if self._visible:
            self._progress = progress
            self._current_value = current_value

    def play_complete_animation(self) -> None:
        self._is_playing_complete_animation = True
        self._completion_animation_progress = 0.0

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        center_x = self._screen_width // 2
        center_y = 40

        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2

        if self._is_playing_complete_animation:
            self._render_complete_animation(surface, center_x, center_y, bar_x, bar_y)
        else:
            self._render_progress_bar(surface, bar_x, bar_y)
            self._render_progress_text(surface, center_x, center_y + 5)

    def _render_progress_bar(self, surface: pygame.Surface, bar_x: int, bar_y: int) -> None:
        bg_rect = pygame.Rect(bar_x, bar_y, self._bar_width, self._bar_height)

        bg_surface = pygame.Surface((self._bar_width, self._bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            bg_surface, self._bg_color,
            (0, 0, self._bar_width, self._bar_height),
            border_radius=self._corner_radius
        )
        surface.blit(bg_surface, (bar_x, bar_y))

        pygame.draw.rect(
            surface, self._border_color,
            (bar_x, bar_y, self._bar_width, self._bar_height),
            self._border_width,
            border_radius=self._corner_radius
        )

        progress_width = int(self._bar_width * self._progress)
        if progress_width > 0:
            progress_color = self._get_progress_color()
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, self._bar_height)
            progress_surface = pygame.Surface((progress_width, self._bar_height), pygame.SRCALPHA)
            pygame.draw.rect(
                progress_surface, (*progress_color, 200),
                (0, 0, progress_width, self._bar_height),
                border_radius=self._corner_radius
            )
            surface.blit(progress_surface, (bar_x, bar_y))

            if progress_width > 2:
                hw = max(1, progress_width - 2)
                highlight_surface = pygame.Surface((hw, 2), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surface, (*progress_color, 120), (0, 0, hw, 2))
                surface.blit(highlight_surface, (bar_x + 1, bar_y + 2))

    def _render_progress_text(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        if self._bar_type == self.BAR_TYPE_HOLD:
            seconds = int(self._progress * 3)
            text = self._font.render(f"按住 {seconds}/3", True, (180, 200, 220))
        elif self._bar_type == self.BAR_TYPE_COOLDOWN:
            remaining = int((1.0 - self._progress) * self._max_value)
            text = self._font.render(f"冷却 {remaining}秒", True, (180, 160, 120))
        elif self._bar_type == self.BAR_TYPE_STAY:
            remaining = int((1.0 - self._progress) * self._max_value)
            text = self._font.render(f"停靠 {remaining}秒", True, (120, 180, 140))
        else:
            text = self._font.render(f"{self._progress:.1%}", True, (180, 200, 220))

        text_rect = text.get_rect(center=(center_x, center_y + 16))
        surface.blit(text, text_rect)

    def _render_mothership_icon(self, surface: pygame.Surface, center_x: int, center_y: int) -> None:
        points = [
            (center_x, center_y - 20),
            (center_x + 25, center_y + 15),
            (center_x + 15, center_y + 10),
            (center_x + 15, center_y + 20),
            (center_x - 15, center_y + 20),
            (center_x - 15, center_y + 10),
            (center_x - 25, center_y + 15),
        ]

        mothership_surface = pygame.Surface((60, 50), pygame.SRCALPHA)
        pygame.draw.polygon(mothership_surface, (180, 180, 220, 200), [
            (p[0] - center_x + 30, p[1] - center_y + 25) for p in points
        ])
        pygame.draw.polygon(mothership_surface, (100, 100, 140, 255), [
            (p[0] - center_x + 30, p[1] - center_y + 25) for p in points
        ], 2)
        surface.blit(mothership_surface, (center_x - 30, center_y - 25))

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

        progress_surface = pygame.Surface((scaled_bar_width, scaled_bar_height), pygame.SRCALPHA)
        pygame.draw.rect(
            progress_surface, (*self._progress_color_complete, alpha),
            (0, 0, scaled_bar_width, scaled_bar_height),
            border_radius=self._corner_radius
        )
        surface.blit(progress_surface, (scaled_x, scaled_y))

    def _get_progress_color(self) -> tuple:
        if self._bar_type == self.BAR_TYPE_COOLDOWN:
            if self._progress >= 1.0:
                return self._progress_color_complete
            return self._progress_color_cooldown
        elif self._bar_type == self.BAR_TYPE_STAY:
            if self._progress >= 0.8:
                t = (self._progress - 0.8) / 0.2
                return self._lerp_color(self._progress_color_stay, self._progress_color_complete, t)
            return self._progress_color_stay
        else:
            if self._progress >= 1.0:
                return self._progress_color_complete
            elif self._progress >= 0.8:
                t = (self._progress - 0.8) / 0.2
                return self._lerp_color(self._progress_color_active, self._progress_color_complete, t)
            return self._progress_color_active

    def _lerp_color(self, color1: tuple, color2: tuple, t: float) -> tuple:
        return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))
