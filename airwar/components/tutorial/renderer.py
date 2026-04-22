"""
Tutorial Renderer Component

This module implements the TutorialRenderer class, which handles all
rendering logic for the tutorial system including background, panel,
progress indicators, content, and navigation buttons.
Following the Single Responsibility Principle - it only handles rendering.
Visual style follows DesignTokens for consistency with other scenes.
"""

import pygame
import math
from typing import Dict, List, Optional, Any
from airwar.config.tutorial import TUTORIAL_STEPS, StepType
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

        self._base_panel_width = 600
        self._base_panel_height = 550
        self._base_option_height = 65
        self._base_option_gap = 10
        self._base_title_y = 55
        self._base_button_width = 160
        self._base_button_height = 48

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
        Main render method - renders all tutorial UI elements.

        Args:
            surface: pygame.Surface to render on
            panel: TutorialPanel instance for layout calculations
            step: Current step data dictionary
            progress: List of booleans indicating progress state
            current_index: Current step index
            selected_index: Currently selected content item index
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
        self._render_title_section(surface, step, scale)
        self._render_content_items(surface, step, scale, selected_index)
        self._render_note_and_warning(surface, step, scale)
        self._render_navigation_buttons(surface, step, scale, panel)
        self._render_bottom_hints(surface, scale)

    def _render_background(self, surface: pygame.Surface) -> None:
        """Render background using MenuBackground."""
        if self._background_renderer:
            self._background_renderer.render(surface, self._colors)

    def _render_particles(self, surface: pygame.Surface) -> None:
        """Render floating particles."""
        if self._particle_system:
            self._particle_system.render(surface, self._colors['particle'])

    def _render_panel(self, surface: pygame.Surface, scale: float) -> None:
        """Render the main panel container matching menu_scene.py style."""
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

    def _render_title_section(self, surface: pygame.Surface, step: Dict, scale: float) -> None:
        """Render the step title with glow effect."""
        width, height = surface.get_size()
        panel_width = ResponsiveHelper.scale(self._base_panel_width, scale)
        panel_x = width // 2 - panel_width // 2
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2

        glow_radius = self._tokens.animation.GLOW_RADIUS_TITLE if self._tokens else 6
        glow_speed = self._tokens.animation.GLOW_SPEED if self._tokens else 0.08
        glow_offset = math.sin(self._animation_time * glow_speed) * 12

        title_font_size = ResponsiveHelper.font_size(72, scale)
        title_font = pygame.font.Font(None, title_font_size)

        title_y = panel_y + ResponsiveHelper.scale(self._base_title_y, scale) + glow_offset * 0.5

        self._draw_glow_text(
            surface,
            step['title'],
            title_font,
            (width // 2, title_y),
            self._colors['title'],
            self._colors['title_glow'],
            glow_radius
        )

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
            alpha = int(120 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _render_content_items(
        self,
        surface: pygame.Surface,
        step: Dict,
        scale: float,
        selected_index: int = 0
    ) -> None:
        """Render content items as option boxes matching menu_scene.py style."""
        if step.get('is_complete'):
            self._render_complete_step(surface, scale)
            return

        width, height = surface.get_size()
        panel_width = ResponsiveHelper.scale(self._base_panel_width, scale)
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2

        content = step.get('content', [])
        if not content:
            return

        option_height = ResponsiveHelper.scale(self._base_option_height, scale)
        option_gap = ResponsiveHelper.scale(self._base_option_gap, scale)
        box_width = ResponsiveHelper.scale(540, scale)
        center_x = width // 2

        title_area_end = panel_y + ResponsiveHelper.scale(100, scale)
        note_area_start = panel_y + panel_height - ResponsiveHelper.scale(175, scale)
        available_height = note_area_start - title_area_end - ResponsiveHelper.scale(10, scale)
        max_items = (available_height + option_gap) // (option_height + option_gap)
        visible_items = min(len(content), max_items)

        total_content_height = visible_items * option_height + (visible_items - 1) * option_gap
        start_y = title_area_end + (available_height - total_content_height) // 2

        for i, item in enumerate(content):
            if i >= visible_items:
                break

            y = start_y + i * (option_height + option_gap)
            is_selected = (i == selected_index)

            if 'key' in item:
                self._render_key_option_item(
                    surface, item, center_x, y, box_width, option_height, is_selected, scale
                )
            else:
                self._render_text_option_item(
                    surface, item, center_x, y, box_width, option_height, is_selected, scale
                )

    def _render_key_option_item(
        self,
        surface: pygame.Surface,
        item: Dict,
        center_x: int,
        y: int,
        box_width: int,
        box_height: int,
        is_selected: bool,
        scale: float
    ) -> None:
        """Render a key-description option item."""
        box_rect = pygame.Rect(center_x - box_width // 2, y, box_width, box_height)

        if is_selected:
            glow_color = self._colors['selected_glow']
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = box_rect.inflate(expand * 2, expand * 2)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surf,
                    (*glow_color, 35 // i),
                    glow_surf.get_rect(),
                    border_radius=10
                )
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(
                surface,
                self._colors['option_selected_bg'],
                box_rect,
                border_radius=10
            )
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*self._colors['selected'], 200),
                border_surf.get_rect(),
                width=2,
                border_radius=10
            )
            surface.blit(border_surf, box_rect.topleft)
        else:
            pygame.draw.rect(
                surface,
                self._colors['option_unselected_bg'],
                box_rect,
                border_radius=10
            )
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*self._colors['unselected'], 80),
                border_surf.get_rect(),
                width=1,
                border_radius=10
            )
            surface.blit(border_surf, box_rect.topleft)

        key_font_size = ResponsiveHelper.font_size(32, scale)
        desc_font_size = ResponsiveHelper.font_size(26, scale)
        key_font = pygame.font.Font(None, key_font_size)
        desc_font = pygame.font.Font(None, desc_font_size)

        arrow = ">" if is_selected else " "
        key_text = f"  {arrow}  {item['key']}"
        text_color = self._colors['selected'] if is_selected else self._colors['unselected']
        key_surface = key_font.render(key_text, True, text_color)
        key_rect = key_surface.get_rect(midleft=(box_rect.x + 15, box_rect.centery))
        surface.blit(key_surface, key_rect)

        desc_color = self._colors['title'] if is_selected else self._colors['unselected']
        desc_surface = desc_font.render(f"- {item['description']}", True, desc_color)
        desc_rect = desc_surface.get_rect(midright=(box_rect.right - 15, box_rect.centery))
        surface.blit(desc_surface, desc_rect)

    def _render_text_option_item(
        self,
        surface: pygame.Surface,
        item: Dict,
        center_x: int,
        y: int,
        box_width: int,
        box_height: int,
        is_selected: bool,
        scale: float
    ) -> None:
        """Render a text-only option item (for welcome step)."""
        box_rect = pygame.Rect(center_x - box_width // 2, y, box_width, box_height)

        if is_selected:
            glow_color = self._colors['selected_glow']
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = box_rect.inflate(expand * 2, expand * 2)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surf,
                    (*glow_color, 35 // i),
                    glow_surf.get_rect(),
                    border_radius=10
                )
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(
                surface,
                self._colors['option_selected_bg'],
                box_rect,
                border_radius=10
            )
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*self._colors['selected'], 200),
                border_surf.get_rect(),
                width=2,
                border_radius=10
            )
            surface.blit(border_surf, box_rect.topleft)
        else:
            pygame.draw.rect(
                surface,
                self._colors['option_unselected_bg'],
                box_rect,
                border_radius=10
            )
            border_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*self._colors['unselected'], 80),
                border_surf.get_rect(),
                width=1,
                border_radius=10
            )
            surface.blit(border_surf, box_rect.topleft)

        desc_font_size = ResponsiveHelper.font_size(28, scale)
        desc_font = pygame.font.Font(None, desc_font_size)

        arrow = ">" if is_selected else " "
        text = f"  {arrow}  {item['text']}"
        text_color = self._colors['selected'] if is_selected else self._colors['unselected']
        text_surface = desc_font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(box_rect.centerx, box_rect.centery))
        surface.blit(text_surface, text_rect)

    def _render_complete_step(self, surface: pygame.Surface, scale: float) -> None:
        """Render the completion step special content."""
        width, height = surface.get_size()
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2

        desc_font_size = ResponsiveHelper.font_size(32, scale)
        desc_font = pygame.font.Font(None, desc_font_size)

        center_y = panel_y + panel_height // 2 - ResponsiveHelper.scale(30, scale)

        text = "You have mastered all the basic controls!"
        self._draw_glow_text(
            surface,
            text,
            desc_font,
            (width // 2, center_y),
            self._colors['title'],
            self._colors['title_glow'],
            4
        )

        sub_text_font_size = ResponsiveHelper.font_size(24, scale)
        sub_text_font = pygame.font.Font(None, sub_text_font_size)
        sub_text = "Click the button below to start the game or return to menu"
        sub_surface = sub_text_font.render(sub_text, True, self._colors['hint'])
        sub_rect = sub_surface.get_rect(center=(width // 2, center_y + 50))
        surface.blit(sub_surface, sub_rect)

    def _render_note_and_warning(self, surface: pygame.Surface, step: Dict, scale: float) -> None:
        """Render note and warning text in dedicated area."""
        width, height = surface.get_size()
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2

        note_font_size = ResponsiveHelper.font_size(18, scale)
        note_font = pygame.font.Font(None, note_font_size)

        y_offset = panel_y + panel_height - ResponsiveHelper.scale(175, scale)

        if 'note' in step:
            note_color = self._colors['hint']
            note_surface = note_font.render(f"Note: {step['note']}", True, note_color)
            note_rect = note_surface.get_rect(
                center=(width // 2, y_offset)
            )
            surface.blit(note_surface, note_rect)
            y_offset += ResponsiveHelper.scale(22, scale)

        if 'warning' in step:
            warning_color = self._tokens.colors.WARNING if self._tokens else (255, 100, 80)
            warning_surface = note_font.render(f"Warning: {step['warning']}", True, warning_color)
            warning_rect = warning_surface.get_rect(
                center=(width // 2, y_offset)
            )
            surface.blit(warning_surface, warning_rect)

    def _render_navigation_buttons(
        self,
        surface: pygame.Surface,
        step: Dict,
        scale: float,
        panel
    ) -> None:
        """Render navigation buttons matching pause_scene.py style."""
        width, height = surface.get_size()
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2
        panel_width = ResponsiveHelper.scale(self._base_panel_width, scale)
        panel_x = width // 2 - panel_width // 2

        button_width = ResponsiveHelper.scale(self._base_button_width, scale)
        button_height = ResponsiveHelper.scale(self._base_button_height, scale)
        button_y = panel_y + panel_height - ResponsiveHelper.scale(75, scale)

        button_font_size = ResponsiveHelper.font_size(28, scale)
        button_font = pygame.font.Font(None, button_font_size)

        is_first = step.get('id') == TUTORIAL_STEPS[0]['id']
        is_last = step.get('is_complete', False)

        mouse_pos = pygame.mouse.get_pos()

        if is_last:
            exit_x = width // 2 - button_width // 2
            exit_rect = pygame.Rect(exit_x, button_y, button_width, button_height)
            exit_hover = exit_rect.collidepoint(mouse_pos)

            self._render_button(
                surface, exit_rect, "Return to Menu",
                button_font, exit_hover, is_first, is_last
            )
        elif is_first:
            next_x = width // 2 - button_width // 2
            next_rect = pygame.Rect(next_x, button_y, button_width, button_height)
            next_hover = next_rect.collidepoint(mouse_pos)

            self._render_button(
                surface, next_rect, "Next",
                button_font, next_hover, is_first, is_last
            )
        else:
            prev_x = width // 2 - button_width - ResponsiveHelper.scale(20, scale)
            prev_rect = pygame.Rect(prev_x, button_y, button_width, button_height)
            prev_hover = prev_rect.collidepoint(mouse_pos)

            self._render_button(
                surface, prev_rect, "Previous",
                button_font, prev_hover, is_first, is_last
            )

            next_x = width // 2 + ResponsiveHelper.scale(20, scale)
            next_rect = pygame.Rect(next_x, button_y, button_width, button_height)
            next_hover = next_rect.collidepoint(mouse_pos)

            self._render_button(
                surface, next_rect, "Next",
                button_font, next_hover, is_first, is_last
            )

    def _render_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        is_hover: bool,
        is_prev_disabled: bool,
        is_exit: bool
    ) -> None:
        """Render a single button with hover effect."""
        if is_exit:
            bg_color = self._tokens.colors.DANGER_BUTTON_SELECTED_PRIMARY if is_hover else self._tokens.colors.DANGER_BUTTON_UNSELECTED_PRIMARY
            border_color = self._tokens.colors.DANGER_BUTTON_SELECTED_GLOW if is_hover else self._tokens.colors.DANGER_BUTTON_SELECTED_PRIMARY
            text_color = self._tokens.colors.BUTTON_SELECTED_TEXT
        else:
            bg_color = self._tokens.colors.BUTTON_SELECTED_BG if is_hover else self._tokens.colors.BUTTON_UNSELECTED_BG
            border_color = self._tokens.colors.BUTTON_SELECTED_PRIMARY if is_hover else self._tokens.colors.BUTTON_UNSELECTED_PRIMARY
            text_color = self._tokens.colors.BUTTON_SELECTED_TEXT

        if is_hover:
            glow_color = self._tokens.colors.BUTTON_SELECTED_GLOW if not is_exit else self._tokens.colors.DANGER_BUTTON_SELECTED_GLOW
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, bg_color, rect, border_radius=10)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=10)

        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        surface.blit(text_surface, text_rect)

    def _render_bottom_hints(self, surface: pygame.Surface, scale: float) -> None:
        """Render bottom hints with blinking effect."""
        width, height = surface.get_size()
        panel_height = ResponsiveHelper.scale(self._base_panel_height, scale)
        panel_y = height // 2 - panel_height // 2
        panel_width = ResponsiveHelper.scale(self._base_panel_width, scale)

        blink_interval = self._tokens.animation.BLINK_INTERVAL if self._tokens else 25
        hint_font_size = ResponsiveHelper.font_size(20, scale)
        hint_font = pygame.font.Font(None, hint_font_size)

        if (self._animation_time // blink_interval) % 2 == 0:
            hint_color = (110, 110, 160)
        else:
            hint_color = (140, 140, 180)

        controls_text = "W/S or UP/DOWN to select  |  A/D or LEFT/RIGHT to navigate steps  |  ESC to exit"
        controls_surface = hint_font.render(controls_text, True, hint_color)
        controls_rect = controls_surface.get_rect(
            center=(width // 2, panel_y + panel_height - ResponsiveHelper.scale(20, scale))
        )
        surface.blit(controls_surface, controls_rect)

    def reset(self) -> None:
        """Reset renderer state."""
        self._animation_time = 0
