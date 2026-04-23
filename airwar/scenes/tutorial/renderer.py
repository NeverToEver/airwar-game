"""
Tutorial Renderer Component

This module implements the TutorialRenderer class, which handles all
rendering logic for the tutorial system in a single-page layout.
Following the Single Responsibility Principle - it only handles rendering.
Visual style follows DesignTokens for consistency with other scenes.
"""

import pygame
import math
from typing import Dict, List, Optional, Any
from airwar.config.tutorial import TUTORIAL_CONTENT
from airwar.utils.responsive import ResponsiveHelper


class TutorialRenderer:
    """
    Tutorial renderer component responsible for all rendering operations.

    This class follows the Single Responsibility Principle by focusing
    exclusively on rendering logic. It uses DesignTokens for visual
    consistency with menu_scene and pause_scene.
    """

    def __init__(self):
        self._animation_time = 0
        self._tokens = None
        self._colors = None
        self._background_renderer = None
        self._particle_system = None

        self._base_panel_width = 850
        self._base_panel_height = 750
        self._base_section_gap = 25
        self._base_item_height = 40
        self._base_item_gap = 6
        self._base_button_width = 220
        self._base_button_height = 55

    def render(
        self,
        surface: pygame.Surface,
        panel,
        step: Dict,
        progress: List[bool],
        current_index: int = 0,
        selected_index: int = 0,
        colors: Dict = None,
        tokens: Any = None,
        background_renderer=None,
        particle_system=None,
        animation_time: int = 0
    ) -> None:
        """
        Main render method - renders all tutorial UI elements in single-page layout.

        Args:
            surface: pygame.Surface to render on
            panel: TutorialPanel instance (unused in single-page mode)
            step: Current step data (unused in single-page mode)
            progress: Progress list (unused in single-page mode)
            current_index: Current section index
            selected_index: Currently selected item index
            colors: Color dictionary from TutorialScene
            tokens: DesignTokens instance
            background_renderer: MenuBackground instance
            particle_system: ParticleSystem instance
            animation_time: Current animation time
        """
        self._tokens = tokens
        self._colors = colors
        self._background_renderer = background_renderer
        self._particle_system = particle_system
        self._animation_time = animation_time

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        self._render_background(surface)
        self._render_particles(surface)
        self._render_panel(surface, scale)
        self._render_title(surface, scale)
        self._render_sections(surface, scale, selected_index)
        self._render_button(surface, scale)
        self._render_bottom_hint(surface, scale)

    def _render_background(self, surface: pygame.Surface) -> None:
        """Render background using MenuBackground."""
        if self._background_renderer:
            self._background_renderer.render(surface, self._colors)

    def _render_particles(self, surface: pygame.Surface) -> None:
        """Render floating particles."""
        if self._particle_system:
            self._particle_system.render(surface, self._colors['particle'])

    def _render_panel(self, surface: pygame.Surface, scale: float) -> None:
        """Render the main panel container."""
        width, height = surface.get_size()

        panel_width = ResponsiveHelper.scale(self._base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2

        glow_color = self._colors['title_glow']
        for i in range(4, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface(
                (panel_width + expand * 2, panel_height + expand * 2),
                pygame.SRCALPHA
            )
            alpha = max(5, 25 // i)
            pygame.draw.rect(
                glow_surf,
                (*glow_color, alpha),
                glow_surf.get_rect(),
                border_radius=18
            )
            surface.blit(glow_surf, (panel_x - expand, panel_y - expand))

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(surface, self._colors['panel'], panel_rect, border_radius=15)

        border_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf,
            (*self._colors['panel_border'], 140),
            border_surf.get_rect(),
            width=2,
            border_radius=15
        )
        surface.blit(border_surf, panel_rect.topleft)

        self._panel_rect = (panel_x, panel_y, panel_width, panel_height)

    def _render_title(self, surface: pygame.Surface, scale: float) -> None:
        """Render the main title."""
        width, height = surface.get_size()
        panel_x, panel_y, panel_width, panel_height = self._panel_rect

        glow_speed = self._tokens.animation.GLOW_SPEED if self._tokens else 0.05
        glow_offset = math.sin(self._animation_time * glow_speed) * 8

        title_font_size = ResponsiveHelper.font_size(56, scale)
        title_font = pygame.font.Font(None, title_font_size)

        title_y = panel_y + ResponsiveHelper.scale(50, scale) + glow_offset * 0.3
        self._draw_glow_text(
            surface,
            TUTORIAL_CONTENT['title'],
            title_font,
            (width // 2, title_y),
            self._colors['title'],
            self._colors['title_glow'],
            5
        )

        subtitle_font_size = ResponsiveHelper.font_size(24, scale)
        subtitle_font = pygame.font.Font(None, subtitle_font_size)
        subtitle_y = title_y + ResponsiveHelper.scale(35, scale)
        subtitle_surface = subtitle_font.render(
            TUTORIAL_CONTENT['subtitle'],
            True,
            self._colors['hint']
        )
        surface.blit(subtitle_surface, subtitle_surface.get_rect(center=(width // 2, subtitle_y)))

    def _draw_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = 4
    ) -> None:
        """Draw text with glow effect."""
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _render_sections(self, surface: pygame.Surface, scale: float, selected_index: int) -> None:
        """Render all tutorial sections in a grid layout."""
        width, height = surface.get_size()
        panel_x, panel_y, panel_width, panel_height = self._panel_rect

        sections = TUTORIAL_CONTENT['sections']
        num_sections = len(sections)

        section_gap = ResponsiveHelper.scale(self._base_section_gap, scale)
        item_height = ResponsiveHelper.scale(self._base_item_height, scale)
        item_gap = ResponsiveHelper.scale(self._base_item_gap, scale)

        title_area_end = panel_y + ResponsiveHelper.scale(120, scale)
        button_area_start = panel_y + panel_height - ResponsiveHelper.scale(100, scale)
        available_height = button_area_start - title_area_end - section_gap * (num_sections - 1)

        cols = 2
        rows = (num_sections + cols - 1) // cols
        section_height = available_height // rows

        section_width = (panel_width - section_gap * 3) // cols

        for idx, section in enumerate(sections):
            col = idx % cols
            row = idx // cols

            section_x = panel_x + section_gap + col * (section_width + section_gap)
            section_y = title_area_end + row * (section_height + section_gap)

            self._render_section(
                surface, section, section_x, section_y,
                section_width, section_height, item_height, item_gap, scale
            )

    def _render_section(
        self,
        surface: pygame.Surface,
        section: Dict,
        x: int,
        y: int,
        width: int,
        height: int,
        item_height: int,
        item_gap: int,
        scale: float
    ) -> None:
        """Render a single tutorial section."""
        section_rect = pygame.Rect(x, y, width, height)

        pygame.draw.rect(
            surface,
            self._colors['option_unselected_bg'],
            section_rect,
            border_radius=10
        )
        border_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf,
            (*self._colors['panel_border'], 80),
            border_surf.get_rect(),
            width=1,
            border_radius=10
        )
        surface.blit(border_surf, section_rect.topleft)

        title_font_size = ResponsiveHelper.font_size(28, scale)
        title_font = pygame.font.Font(None, title_font_size)
        title_surface = title_font.render(section['title'], True, self._colors['title'])
        title_rect = title_surface.get_rect(
            midtop=(x + width // 2, y + ResponsiveHelper.scale(12, scale))
        )
        surface.blit(title_surface, title_rect)

        items = section['items']
        num_items = len(items)
        content_start_y = y + ResponsiveHelper.scale(45, scale)
        available_item_height = height - ResponsiveHelper.scale(50, scale)
        total_items_height = num_items * item_height + (num_items - 1) * item_gap
        start_y = content_start_y + (available_item_height - total_items_height) // 2

        key_font_size = ResponsiveHelper.font_size(22, scale)
        desc_font_size = ResponsiveHelper.font_size(20, scale)
        key_font = pygame.font.Font(None, key_font_size)
        desc_font = pygame.font.Font(None, desc_font_size)

        for i, item in enumerate(items):
            item_y = start_y + i * (item_height + item_gap)

            key_surface = key_font.render(item['key'], True, self._colors['selected'])
            key_rect = key_surface.get_rect(midleft=(x + ResponsiveHelper.scale(15, scale), item_y + item_height // 2))
            surface.blit(key_surface, key_rect)

            desc_surface = desc_font.render(item['desc'], True, self._colors['unselected'])
            desc_rect = desc_surface.get_rect(midright=(x + width - ResponsiveHelper.scale(15, scale), item_y + item_height // 2))
            surface.blit(desc_surface, desc_rect)

    def _render_button(self, surface: pygame.Surface, scale: float) -> None:
        """Render the start button."""
        width, height = surface.get_size()
        panel_x, panel_y, panel_width, panel_height = self._panel_rect

        button_width = ResponsiveHelper.scale(self._base_button_width, scale)
        button_height = ResponsiveHelper.scale(self._base_button_height, scale)
        button_x = width // 2 - button_width // 2
        button_y = panel_y + panel_height - ResponsiveHelper.scale(80, scale)

        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)

        bg_color = self._colors['option_selected_bg'] if is_hover else self._colors['option_unselected_bg']
        border_color = self._colors['selected'] if is_hover else self._colors['panel_border']

        if is_hover:
            glow_color = self._colors['selected_glow']
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = button_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 40 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, bg_color, button_rect, border_radius=10)
        pygame.draw.rect(surface, border_color, button_rect, 2, border_radius=10)

        button_font_size = ResponsiveHelper.font_size(32, scale)
        button_font = pygame.font.Font(None, button_font_size)
        button_text = button_font.render("START GAME", True, self._colors['title'])
        text_rect = button_text.get_rect(center=button_rect.center)
        surface.blit(button_text, text_rect)

        self._start_button_rect = button_rect

    def _render_bottom_hint(self, surface: pygame.Surface, scale: float) -> None:
        """Render bottom hint text."""
        width, height = surface.get_size()
        panel_x, panel_y, panel_width, panel_height = self._panel_rect

        hint_font_size = ResponsiveHelper.font_size(18, scale)
        hint_font = pygame.font.Font(None, hint_font_size)

        blink_interval = self._tokens.animation.BLINK_INTERVAL if self._tokens else 25
        alpha = 150 if (self._animation_time // blink_interval) % 2 == 0 else 100
        hint_color = (*self._colors['hint'][:3], alpha) if len(self._colors['hint']) > 3 else self._colors['hint']

        hint_text = "Press ESC or click button to return to menu"
        hint_surface = hint_font.render(hint_text, True, hint_color)
        hint_rect = hint_surface.get_rect(
            center=(width // 2, panel_y + panel_height - ResponsiveHelper.scale(20, scale))
        )
        surface.blit(hint_surface, hint_rect)

    def get_start_button_rect(self) -> Optional[pygame.Rect]:
        """Get the start button rect for click detection."""
        return getattr(self, '_start_button_rect', None)

    def reset(self) -> None:
        """Reset renderer state."""
        self._animation_time = 0
        self._panel_rect = None
        self._start_button_rect = None
