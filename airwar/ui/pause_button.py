"""Pause button layout and rendering component."""

import pygame


class PauseButtonComponent:
    PAUSE_BUTTON_SIZE = 44
    PAUSE_BUTTON_MARGIN = 10
    PAUSE_BAR_WIDTH = 5
    PAUSE_BAR_HEIGHT = 18
    PAUSE_BAR_GAP = 5

    def __init__(self) -> None:
        self._pause_btn_layout = None
        self._pause_btn_cache = {}

    def init_layout(self, register_button_callback) -> None:
        size = self.PAUSE_BUTTON_SIZE
        margin = self.PAUSE_BUTTON_MARGIN
        bar_w = self.PAUSE_BAR_WIDTH
        bar_h = self.PAUSE_BAR_HEIGHT
        bar_gap = self.PAUSE_BAR_GAP

        button_x = margin
        button_y = margin
        center_x = button_x + size // 2
        center_y = button_y + size // 2

        self._pause_btn_layout = {
            'rect': pygame.Rect(button_x, button_y, size, size),
            'left_bar': (center_x - bar_gap // 2 - bar_w, center_y - bar_h // 2, bar_w, bar_h),
            'right_bar': (center_x + bar_gap // 2, center_y - bar_h // 2, bar_w, bar_h),
            'pos': (button_x, button_y),
        }
        register_button_callback("pause", self._pause_btn_layout['rect'])
        self._pause_btn_cache.clear()

    def render(self, surface: pygame.Surface, is_hovered: bool, colors, spacing) -> None:
        if not self._pause_btn_layout:
            return

        self._ensure_cache(colors, spacing)
        state_key = "hovered" if is_hovered else "normal"
        bg_surface, border_surface = self._pause_btn_cache[state_key]

        layout = self._pause_btn_layout
        pos = layout['pos']
        surface.blit(bg_surface, pos)
        surface.blit(border_surface, pos)

        bar_color = colors.HUD_AMBER if is_hovered else colors.TEXT_MUTED
        pygame.draw.rect(surface, bar_color, layout['left_bar'], border_radius=1)
        pygame.draw.rect(surface, bar_color, layout['right_bar'], border_radius=1)

    def clear_cache(self) -> None:
        self._pause_btn_cache.clear()

    def _ensure_cache(self, colors, spacing) -> None:
        if self._pause_btn_cache:
            return

        size = self.PAUSE_BUTTON_SIZE
        for state_key, bg_alpha, border_alpha in [
            ("normal", 180, 120),
            ("hovered", 220, 200),
        ]:
            bg_color = (*colors.BACKGROUND_PANEL, bg_alpha)
            bg_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(
                bg_surface, bg_color,
                bg_surface.get_rect(),
                border_radius=spacing.BORDER_RADIUS_SM
            )

            border_color = (*colors.PANEL_BORDER, border_alpha)
            border_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surface, border_color,
                border_surface.get_rect(),
                width=1,
                border_radius=spacing.BORDER_RADIUS_SM
            )

            self._pause_btn_cache[state_key] = (bg_surface, border_surface)
