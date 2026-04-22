"""
Tutorial Renderer Component

This module implements the TutorialRenderer class, which handles all
rendering logic for the tutorial system including background, panel,
progress indicators, content, and navigation buttons.
Following the Single Responsibility Principle - it only handles rendering.
"""

import pygame
import math
import random
from typing import Dict, List
from airwar.config.tutorial import (
    TUTORIAL_COLORS,
    TUTORIAL_FONTS,
    TUTORIAL_STEPS,
    PanelConfig,
    ButtonConfig,
    ProgressIndicatorConfig,
    AnimationConfig,
)
from airwar.utils.responsive import ResponsiveHelper


class TutorialRenderer:
    """
    Tutorial renderer component responsible for all rendering operations.
    
    This class follows the Single Responsibility Principle by focusing
    exclusively on rendering logic. It delegates layout calculations
    to TutorialPanel and state management to TutorialNavigator.
    """

    def __init__(self):
        self._colors = TUTORIAL_COLORS
        self._fonts = TUTORIAL_FONTS
        self._panel_config = PanelConfig()
        self._button_config = ButtonConfig()
        self._progress_config = ProgressIndicatorConfig()
        self._animation_config = AnimationConfig()
        
        self._background_cache = None
        self._animation_time = 0
        self._stars = []
        self._particles = []
        self._init_background_elements()

    def _init_background_elements(self) -> None:
        """Initialize star and particle systems for background animation."""
        self._stars = []
        self._particles = []
        
        for _ in range(100):
            self._stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })
        
        for _ in range(40):
            self._particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(0.3, 0.9),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })

    def render(
        self,
        surface: pygame.Surface,
        panel,
        step: Dict,
        progress: List[bool]
    ) -> None:
        """
        Main render method - renders all tutorial UI elements.
        
        Args:
            surface: pygame.Surface to render on
            panel: TutorialPanel instance for layout calculations
            step: Current step data dictionary
            progress: List of booleans indicating progress state
        """
        self._animation_time += 1
        self._update_background_elements()
        
        layout = panel.calculate_layout(*surface.get_size())
        
        self._render_background(surface)
        self._render_stars(surface)
        self._render_particles(surface)
        self._render_panel(surface, layout)
        self._render_progress_indicators(surface, layout, progress)
        self._render_step_content(surface, layout, step)
        self._render_navigation_buttons(surface, layout, step)

    def _update_background_elements(self) -> None:
        """Update background animation state."""
        for star in self._stars:
            star['y'] += 0.008 * (star.get('speed', 1))
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()
        
        for p in self._particles[:]:
            p['y'] -= p['speed'] * 0.003
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)

    def _render_background(self, surface: pygame.Surface) -> None:
        """Render gradient background."""
        width, height = surface.get_size()
        
        for y in range(0, height, 3):
            ratio = y / height
            r = int(self._colors['background'][0] * (1 - ratio) + 
                   self._colors['background_gradient'][0] * ratio)
            g = int(self._colors['background'][1] * (1 - ratio) + 
                   self._colors['background_gradient'][1] * ratio)
            b = int(self._colors['background'][2] * (1 - ratio) + 
                   self._colors['background_gradient'][2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _render_stars(self, surface: pygame.Surface) -> None:
        """Render twinkling star background."""
        width, height = surface.get_size()
        
        for star in self._stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self._animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(
                surface,
                (brightness, brightness, brightness + 30),
                (x, y),
                int(star['size'])
            )

    def _render_particles(self, surface: pygame.Surface) -> None:
        """Render floating particle effect."""
        width, height = surface.get_size()
        
        for p in self._particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self._animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = int(p['size'] * (0.7 + 0.3 * pulse))
            
            particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for i in range(int(size * 2), 0, -2):
                layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                pygame.draw.circle(
                    particle_surf,
                    (*self._colors['particle'], layer_alpha),
                    (int(size * 2), int(size * 2)),
                    i
                )
            surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def _render_panel(self, surface: pygame.Surface, layout: Dict) -> None:
        """Render the main panel container."""
        panel_rect = pygame.Rect(
            layout['x'],
            layout['y'],
            layout['width'],
            layout['height']
        )
        
        glow_color = self._colors['title_glow']
        for i in range(4, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface(
                (layout['width'] + expand * 2, layout['height'] + expand * 2),
                pygame.SRCALPHA
            )
            alpha = max(5, 25 // i)
            pygame.draw.rect(
                glow_surf,
                (*glow_color, alpha),
                glow_surf.get_rect(),
                border_radius=18
            )
            surface.blit(glow_surf, (layout['x'] - expand, layout['y'] - expand))
        
        pygame.draw.rect(surface, self._colors['panel_background'], panel_rect, border_radius=15)
        
        border_surf = pygame.Surface((layout['width'], layout['height']), pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf,
            (*self._colors['panel_border'], 140),
            border_surf.get_rect(),
            width=2,
            border_radius=15
        )
        surface.blit(border_surf, panel_rect.topleft)

    def _render_progress_indicators(self, surface: pygame.Surface, layout: Dict, progress: List[bool]) -> None:
        """Render step progress indicators."""
        width = layout['width']
        x_start = layout['x'] + width // 2 - (self._progress_config.WIDTH + self._progress_config.SPACING) * len(progress) // 2
        y = layout['y'] + 50
        
        for i, is_active in enumerate(progress):
            color = self._colors['progress_active'] if is_active else self._colors['progress_inactive']
            pygame.draw.circle(
                surface,
                color,
                (x_start + i * (self._progress_config.WIDTH + self._progress_config.SPACING) + self._progress_config.WIDTH // 2, y),
                self._progress_config.WIDTH // 2
            )

    def _render_step_content(self, surface: pygame.Surface, layout: Dict, step: Dict) -> None:
        """Render the current step content."""
        scale = ResponsiveHelper.get_scale_factor(layout['width'], layout['height'])
        
        title_y = layout['y'] + 100
        title_font = pygame.font.Font(None, int(self._fonts['title']['size'] * scale))
        
        glow_offset = math.sin(self._animation_time * self._animation_config.GLOW_PULSE_SPEED) * 3
        
        title_surface = title_font.render(step['title'], True, self._colors['title'])
        title_rect = title_surface.get_rect(center=(layout['x'] + layout['width'] // 2, int(title_y + glow_offset)))
        surface.blit(title_surface, title_rect)
        
        if step.get('is_complete'):
            self._render_complete_step(surface, layout, scale)
        else:
            self._render_content_items(surface, layout, step, scale)

    def _render_complete_step(self, surface: pygame.Surface, layout: Dict, scale: float) -> None:
        """Render the completion step special content."""
        complete_y = layout['y'] + layout['height'] // 2
        hint_font = pygame.font.Font(None, int(self._fonts['hint']['size'] * scale))
        
        text = "You have mastered all the basic controls!"
        text_surface = hint_font.render(text, True, self._colors['description'])
        text_rect = text_surface.get_rect(center=(layout['x'] + layout['width'] // 2, complete_y))
        surface.blit(text_surface, text_rect)
        
        sub_text = "Click the button below to start the game or return to menu"
        sub_surface = hint_font.render(sub_text, True, self._colors['hint'])
        sub_rect = sub_surface.get_rect(center=(layout['x'] + layout['width'] // 2, complete_y + 40))
        surface.blit(sub_surface, sub_rect)

    def _render_content_items(self, surface: pygame.Surface, layout: Dict, step: Dict, scale: float) -> None:
        """Render content items for a step."""
        content = step.get('content', [])
        if not content:
            return
        
        section_font = pygame.font.Font(None, int(self._fonts['section']['size'] * scale))
        key_font = pygame.font.Font(None, int(self._fonts['key']['size'] * scale))
        desc_font = pygame.font.Font(None, int(self._fonts['description']['size'] * scale))
        
        start_y = layout['y'] + 180
        item_gap = 50
        
        content_area = pygame.Rect(
            layout['x'] + 30,
            start_y,
            layout['width'] - 60,
            len(content) * item_gap + 20
        )
        pygame.draw.rect(surface, (20, 25, 50), content_area, border_radius=10)
        
        for i, item in enumerate(content):
            item_y = start_y + 15 + i * item_gap
            
            key_surface = key_font.render(item['key'], True, self._colors['key_highlight'])
            key_rect = key_surface.get_rect(left=content_area.x + 20, top=item_y)
            surface.blit(key_surface, key_rect)
            
            desc_surface = desc_font.render(item['description'], True, self._colors['description'])
            desc_rect = desc_surface.get_rect(right=content_area.right - 20, top=item_y)
            surface.blit(desc_surface, desc_rect)
        
        if 'note' in step:
            note_y = start_y + len(content) * item_gap + 35
            note_font = pygame.font.Font(None, int(self._fonts['hint']['size'] * scale))
            note_surface = note_font.render(step['note'], True, self._colors['hint'])
            note_rect = note_surface.get_rect(center=(layout['x'] + layout['width'] // 2, note_y))
            surface.blit(note_surface, note_rect)

    def _render_navigation_buttons(self, surface: pygame.Surface, layout: Dict, step: Dict) -> None:
        """Render navigation buttons."""
        scale = ResponsiveHelper.get_scale_factor(layout['width'], layout['height'])
        button_width = int(self._button_config.WIDTH * scale)
        button_height = int(self._button_config.HEIGHT * scale)
        button_y = layout['y'] + layout['height'] - int(80 * scale)
        
        button_font = pygame.font.Font(None, int(self._fonts['button']['size'] * scale))
        
        is_first = step.get('id') == TUTORIAL_STEPS[0]['id']
        is_last = step.get('is_complete', False)
        
        if not is_first:
            prev_x = layout['x'] + layout['width'] // 2 - button_width - 20
            prev_rect = pygame.Rect(prev_x, button_y, button_width, button_height)
            
            mouse_pos = pygame.mouse.get_pos()
            prev_hover = prev_rect.collidepoint(mouse_pos)
            
            btn_color = self._colors['button_hover'] if prev_hover else self._colors['button_normal']
            pygame.draw.rect(surface, btn_color, prev_rect, border_radius=10)
            
            prev_border = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
            pygame.draw.rect(
                prev_border,
                (*self._colors['panel_border_highlight'], 120 if prev_hover else 100),
                prev_border.get_rect(),
                width=2,
                border_radius=10
            )
            surface.blit(prev_border, prev_rect.topleft)
            
            prev_text = button_font.render("Previous", True, (245, 250, 255))
            prev_text_rect = prev_text.get_rect(center=prev_rect.center)
            surface.blit(prev_text, prev_text_rect)
        
        if is_last:
            exit_x = layout['x'] + layout['width'] // 2 - button_width // 2
            exit_rect = pygame.Rect(exit_x, button_y, button_width, button_height)
            
            mouse_pos = pygame.mouse.get_pos()
            exit_hover = exit_rect.collidepoint(mouse_pos)
            
            btn_color = self._colors['button_hover'] if exit_hover else self._colors['button_normal']
            pygame.draw.rect(surface, btn_color, exit_rect, border_radius=10)
            
            exit_border = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
            pygame.draw.rect(
                exit_border,
                (*self._colors['progress_active'], 150 if exit_hover else 120),
                exit_border.get_rect(),
                width=2,
                border_radius=10
            )
            surface.blit(exit_border, exit_rect.topleft)
            
            exit_text = button_font.render("Return to Menu", True, (245, 250, 255))
            exit_text_rect = exit_text.get_rect(center=exit_rect.center)
            surface.blit(exit_text, exit_text_rect)
        else:
            next_x = layout['x'] + layout['width'] // 2 + 20
            next_rect = pygame.Rect(next_x, button_y, button_width, button_height)
            
            mouse_pos = pygame.mouse.get_pos()
            next_hover = next_rect.collidepoint(mouse_pos)
            
            btn_color = self._colors['button_hover'] if next_hover else self._colors['button_normal']
            pygame.draw.rect(surface, btn_color, next_rect, border_radius=10)
            
            next_border = pygame.Surface((button_width, button_height), pygame.SRCALPHA)
            pygame.draw.rect(
                next_border,
                (*self._colors['progress_active'], 150 if next_hover else 120),
                next_border.get_rect(),
                width=2,
                border_radius=10
            )
            surface.blit(next_border, next_rect.topleft)
            
            next_text = button_font.render("Next", True, (245, 250, 255))
            next_text_rect = next_text.get_rect(center=next_rect.center)
            surface.blit(next_text, next_text_rect)
        
        hint_font = pygame.font.Font(None, int(self._fonts['hint']['size'] * scale))
        hint_y = layout['y'] + layout['height'] - int(25 * scale)
        
        if (self._animation_time // 30) % 2 == 0:
            hint_color = self._colors['hint']
        else:
            hint_color = (100, 100, 140)
        
        hint_text = "ESC Return to Menu  |  L/R Arrow Keys Navigate"
        hint_surface = hint_font.render(hint_text, True, hint_color)
        hint_rect = hint_surface.get_rect(center=(layout['x'] + layout['width'] // 2, hint_y))
        surface.blit(hint_surface, hint_rect)

    def reset(self) -> None:
        """Reset renderer state."""
        self._animation_time = 0
        self._init_background_elements()
