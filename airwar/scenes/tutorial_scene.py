"""
Tutorial Scene Module

This module implements the TutorialScene class, which displays a single-page
tutorial interface showing all game controls at once.
"""

import pygame
from .scene import Scene
from .tutorial import TutorialRenderer
from airwar.config.design_tokens import get_design_tokens
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.utils.mouse_interaction import MouseInteractiveMixin


class TutorialScene(Scene, MouseInteractiveMixin):
    """
    Tutorial scene class - displays all controls in a single page.

    This class provides a simple, non-navigable tutorial that shows
    all game controls at once. User can click START GAME or press ESC
    to return to menu.
    """

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._is_running = False
        self._exit_requested = False
        self._renderer = TutorialRenderer()
        self._animation_time = 0

        self._tokens = get_design_tokens()
        self._background_renderer = MenuBackground()
        self._particle_system = ParticleSystem()
        self._init_colors()

    def _init_colors(self) -> None:
        colors = self._tokens.colors
        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'title': colors.TEXT_PRIMARY,
            'title_glow': colors.HUD_AMBER_BRIGHT,
            'selected': colors.HUD_AMBER,
            'selected_glow': colors.HUD_AMBER_BRIGHT,
            'unselected': colors.TEXT_MUTED,
            'hint': colors.TEXT_HINT,
            'particle': colors.PARTICLE_PRIMARY,
            'particle_alt': colors.PARTICLE_ALT,
            'panel': colors.BACKGROUND_PANEL,
            'panel_border': colors.PANEL_BORDER,
            'option_selected_bg': colors.BUTTON_SELECTED_BG,
            'option_unselected_bg': colors.BUTTON_UNSELECTED_BG,
        }

    def enter(self, **kwargs) -> None:
        """Initialize the tutorial scene."""
        self.clear_hover()
        self.clear_buttons()
        self._is_running = True
        self._exit_requested = False
        self._renderer.reset()
        self._animation_time = 0
        self._particle_system.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

    def exit(self) -> None:
        """Clean up when exiting the tutorial scene."""
        self._is_running = False
        self._exit_requested = False
        self._renderer.reset()

    def reset(self) -> None:
        """Reset the tutorial scene to initial state."""
        self.enter()

    def handle_events(self, event: pygame.event.Event) -> None:
        """Handle input events for the tutorial."""
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_click(event.pos)

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keyboard input."""
        if event.key == pygame.K_ESCAPE:
            self._request_exit()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._request_exit()

    def _handle_mouse_click(self, pos: tuple) -> None:
        """Handle mouse click."""
        button_rect = self._renderer.get_start_button_rect()
        if button_rect and button_rect.collidepoint(pos):
            self._request_exit()

    def _request_exit(self) -> None:
        """Request exit from the tutorial scene."""
        self._exit_requested = True
        self._is_running = False

    def update(self, *args, **kwargs) -> None:
        """Update tutorial state (called each frame)."""
        self._animation_time += 1

        self._background_renderer._animation_time = self._animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self._animation_time
        self._particle_system.update(direction=-1)

    def render(self, surface: pygame.Surface) -> None:
        """Render the tutorial scene."""
        self._renderer.render(
            surface,
            panel=None,
            step={},
            progress=[],
            current_index=0,
            selected_index=0,
            colors=self.colors,
            tokens=self._tokens,
            background_renderer=self._background_renderer,
            particle_system=self._particle_system,
            animation_time=self._animation_time
        )

    def is_running(self) -> bool:
        """Check if the scene is currently running."""
        return self._is_running

    def is_ready(self) -> bool:
        """Check if the scene is ready (finished)."""
        return not self._is_running

    def should_quit(self) -> bool:
        """Check if the scene should quit."""
        return self._exit_requested
