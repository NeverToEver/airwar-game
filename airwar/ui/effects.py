"""UI effects — visual feedback effects for the interface."""

import pygame

from airwar.config.design_tokens import SystemColors, SystemUI, get_design_tokens
from airwar.utils.fonts import get_cjk_font
from airwar.utils.responsive import ResponsiveHelper

from .chamfered_panel import draw_chamfered_panel
from .scene_rendering_utils import draw_centered_option_box, get_glow_text_surface


class EffectsRenderer:
    """Effects renderer for glow text and other visual feedback."""

    OPTION_GLOW_LAYERS = 4
    OPTION_GLOW_ALPHA_DIVISOR = 50
    OPTION_BORDER_RADIUS = 12
    TEXT_GLOW_LAYERS = 3
    TEXT_GLOW_ALPHA_DIVISOR = 60

    def __init__(self):
        self._glow_cache = {}
        self._tokens = get_design_tokens()

    def render_option_box(
        self,
        surface: pygame.Surface,
        text: str,
        y: int,
        is_selected: bool,
        colors: dict,
        option_width: int | None = None,
        option_height: int | None = None,
        scale: float = 1.0,
    ):
        """Render an option selection box."""
        if option_width is None:
            option_width = self._tokens.spacing.BOX_WIDTH
        if option_height is None:
            option_height = self._tokens.spacing.BOX_HEIGHT

        option_font = get_cjk_font(self._tokens.typography.OPTION_SIZE)
        box_width = ResponsiveHelper.scale(option_width, scale)
        box_height = ResponsiveHelper.scale(option_height, scale)

        colors_config = self._tokens.colors
        draw_centered_option_box(
            surface,
            text,
            option_font,
            y,
            is_selected,
            box_width,
            box_height,
            colors_config.BUTTON_SELECTED_BG,
            colors.get("selected", colors_config.HUD_AMBER),
            colors_config.BUTTON_UNSELECTED_BG,
            colors.get("unselected", colors_config.TEXT_MUTED),
            colors.get("selected_glow", colors_config.HUD_AMBER_BRIGHT),
            colors.get("selected", colors_config.HUD_AMBER),
            colors.get("unselected", colors_config.TEXT_MUTED),
            glow_layers=self.OPTION_GLOW_LAYERS,
            glow_alpha_divisor=self.OPTION_GLOW_ALPHA_DIVISOR,
            border_radius=self.OPTION_BORDER_RADIUS,
        )

    def render_chamfered_rect(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
        bg_color: tuple | None = None,
        border_color: tuple | None = None,
        glow_color: tuple | None = None,
        glow_intensity: float = 1.0,
    ):
        """Render a chamfered rectangle panel (military style).

        Args:
            surface: Target surface.
            x: Top-left X coordinate.
            y: Top-left Y coordinate.
            width: Panel width.
            height: Panel height.
            bg_color: Background color.
            border_color: Border color.
            glow_color: Glow color.
            glow_intensity: Glow intensity (0.0-1.0).
        """
        if bg_color is None:
            bg_color = SystemColors.BG_PANEL
        if border_color is None:
            border_color = SystemColors.BORDER_GLOW
        if glow_color is None:
            glow_color = SystemColors.AMBER_GLOW

        effective_glow = self._scaled_alpha(glow_color, glow_intensity) if glow_intensity > 0 else None
        draw_chamfered_panel(
            surface,
            x,
            y,
            width,
            height,
            bg_color,
            border_color,
            effective_glow,
            SystemUI.CHAMFER_DEPTH,
        )

    @staticmethod
    def _scaled_alpha(color: tuple, intensity: float) -> tuple:
        if len(color) == 4:
            return (*color[:3], int(color[3] * max(0.0, min(1.0, intensity))))
        return (*color, int(255 * max(0.0, min(1.0, intensity))))

    def render_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        x: int,
        y: int,
        color: tuple | None = None,
        glow: bool = True,
    ):
        """Render military-style text with optional glow.

        Args:
            surface: Target surface.
            text: Text content.
            font: Font to use.
            x: X coordinate.
            y: Y coordinate.
            color: Text color.
            glow: Whether to add glow effect.
        """
        if color is None:
            color = SystemColors.TEXT_PRIMARY

        if glow:
            composed = get_glow_text_surface(
                font,
                text,
                color,
                SystemColors.AMBER_PRIMARY,
                self.TEXT_GLOW_LAYERS,
                0.5,
                self.TEXT_GLOW_ALPHA_DIVISOR,
            )
            surface.blit(composed, composed.get_rect(center=(x, y)))
            return

        main_text = font.render(text, True, color)
        text_rect = main_text.get_rect(center=(x, y))
        surface.blit(main_text, text_rect)

    def render_scanline_overlay(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect | None = None,
        alpha: int | None = None,
    ):
        """Render a scanline overlay effect.

        Args:
            surface: Target surface.
            rect: Coverage area; None covers the entire surface.
            alpha: Scanline opacity.
        """
        if alpha is None:
            alpha = SystemUI.SCANLINE_ALPHA
        if rect is None:
            rect = surface.get_rect()

        # 每隔 SCANLINE_SPACING 像素画一条线
        for ly in range(rect.top, rect.bottom, SystemUI.SCANLINE_SPACING):
            pygame.draw.line(surface, (*SystemColors.AMBER_PRIMARY[:3], alpha), (rect.left, ly), (rect.right, ly))
