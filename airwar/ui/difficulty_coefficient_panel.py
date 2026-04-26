"""Difficulty coefficient panel — visual indicator of current difficulty."""
import pygame
from typing import TYPE_CHECKING, Tuple, List

from airwar.config.design_tokens import SystemColors

if TYPE_CHECKING:
    from airwar.game.systems.difficulty_manager import DifficultyManager


class DifficultyCoefficientPanel:
    """Difficulty coefficient panel — visual indicator of current difficulty multiplier.
    
        Shows a stacked bar chart comparing initial vs current difficulty
        across speed, fire rate, and aggression dimensions.
        """
    PANEL_WIDTH = 120
    PANEL_HEIGHT = 140
    MARGIN_LEFT = 15

    _COLOR_THRESHOLDS: List[Tuple[float, Tuple[int, int, int], Tuple[int, int, int]]] = [
        (2.0, (100, 255, 100), (0, 255, 255)),
        (4.0, (255, 255, 100), (0, 200, 255)),
        (6.0, (255, 150, 50), (255, 150, 50)),
        (float('inf'), (255, 50, 50), (255, 50, 50)),
    ]

    _bg_surface_cache = None
    _glow_surface_cache = {}

    def __init__(self, difficulty_manager: 'DifficultyManager'):
        self._manager = difficulty_manager
        self._initial_multiplier = difficulty_manager.initial_multiplier
        self._last_multiplier = difficulty_manager.get_current_multiplier()
        self._pulse_timer = 0
        self._glow_intensity = 0.0
        self._last_cached_height = 0

    def update(self) -> None:
        current = self._manager.get_current_multiplier()
        if current > self._last_multiplier:
            self._pulse_timer = 30
            self._glow_intensity = 1.0
        self._last_multiplier = current
        if self._pulse_timer > 0:
            self._pulse_timer -= 1
        if self._glow_intensity > 0:
            self._glow_intensity = max(0, self._glow_intensity - 0.05)

    def render(self, surface: pygame.Surface) -> None:
        current = self._manager.get_current_multiplier()
        max_mult = self._manager.MAX_MULTIPLIER_GLOBAL

        screen_height = surface.get_height()
        panel_x = self.MARGIN_LEFT
        panel_y = (screen_height - self.PANEL_HEIGHT) // 2

        self._render_glow(surface, panel_x, panel_y, current)

        # Use cached background surface
        if DifficultyCoefficientPanel._bg_surface_cache is None:
            bg_color = (10, 10, 30, 220)
            bg_surface = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT), pygame.SRCALPHA)
            bg_surface.fill(bg_color)
            DifficultyCoefficientPanel._bg_surface_cache = bg_surface
        surface.blit(DifficultyCoefficientPanel._bg_surface_cache, (panel_x, panel_y))

        pygame.draw.rect(surface, SystemColors.COEFFICIENT_BAR_BG, (panel_x + 2, panel_y + 2, self.PANEL_WIDTH - 4, self.PANEL_HEIGHT - 4), 1)

        bar_width = self.PANEL_WIDTH - 24
        bar_height = 10
        bar_x = panel_x + 12
        bar_y = panel_y + self.PANEL_HEIGHT - 28

        pygame.draw.rect(surface, SystemColors.COEFFICIENT_BAR_FILL, (bar_x, bar_y, bar_width, bar_height), border_radius=3)
        fill_width = int(bar_width * min(current / max_mult, 1.0))
        color = self._get_color_for_multiplier(current)
        if fill_width > 0:
            pygame.draw.rect(surface, color, (bar_x, bar_y, fill_width, bar_height), border_radius=3)

        font_label = pygame.font.Font(None, 16)
        font_value = pygame.font.Font(None, 22)

        glow_color = self._get_glow_color(current)
        label_text = font_label.render("COEFF", True, glow_color)
        label_rect = label_text.get_rect(center=(panel_x + self.PANEL_WIDTH // 2, panel_y + 18))
        surface.blit(label_text, label_rect)

        value_text = font_value.render(f"{current:.1f} -> {self._initial_multiplier:.1f}", True, color)
        value_rect = value_text.get_rect(center=(panel_x + self.PANEL_WIDTH // 2, panel_y + 45))
        surface.blit(value_text, value_rect)

        delta = current - self._initial_multiplier
        if delta > 0:
            delta_text = font_label.render(f"+{delta:.1f}", True, (100, 255, 100))
            delta_rect = delta_text.get_rect(center=(panel_x + self.PANEL_WIDTH // 2, panel_y + 68))
            surface.blit(delta_text, delta_rect)

        if self._pulse_timer > 0 or self._glow_intensity > 0:
            pulse_alpha = int(150 * (self._pulse_timer / 30 + self._glow_intensity) / 2)
            pulse_color = (*glow_color[:3], min(255, pulse_alpha))
            pulse_surface = pygame.Surface((self.PANEL_WIDTH + 8, self.PANEL_HEIGHT + 8), pygame.SRCALPHA)
            pulse_surface.fill(pulse_color)
            surface.blit(pulse_surface, (panel_x - 4, panel_y - 4))

    def _render_glow(self, surface: pygame.Surface, x: int, y: int, current: float) -> None:
        glow_color = self._get_glow_color(current)
        glow_radius = 4 + int(self._glow_intensity * 3)

        for i in range(glow_radius, 0, -1):
            alpha = int(30 * (1 - i / glow_radius))
            cache_key = (i, glow_color[:3])
            if cache_key not in DifficultyCoefficientPanel._glow_surface_cache:
                glow_surface = pygame.Surface((self.PANEL_WIDTH + i * 2, self.PANEL_HEIGHT + i * 2), pygame.SRCALPHA)
                glow_surface.fill((*glow_color[:3], alpha))
                DifficultyCoefficientPanel._glow_surface_cache[cache_key] = glow_surface
            surface.blit(DifficultyCoefficientPanel._glow_surface_cache[cache_key], (x - i, y - i), special_flags=pygame.BLEND_RGBA_ADD)

    def _get_color_for_multiplier(self, multiplier: float) -> Tuple[int, int, int]:
        return self._get_color_by_index(multiplier, 1)

    def _get_glow_color(self, multiplier: float) -> Tuple[int, int, int]:
        return self._get_color_by_index(multiplier, 2)

    def _get_color_by_index(self, multiplier: float, color_index: int) -> Tuple[int, int, int]:
        for threshold, normal_color, glow_color in self._COLOR_THRESHOLDS:
            if multiplier < threshold:
                return glow_color if color_index == 2 else normal_color
        return self._COLOR_THRESHOLDS[-1][color_index]
