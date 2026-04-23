"""
Tutorial Scene Module

This module implements the TutorialScene class, which is the main scene
for the tutorial system. It coordinates the panel, navigator, and renderer
components to display an interactive tutorial interface.
Following the Facade Pattern - provides simple interface to complex subsystem.
Visual style follows DesignTokens for consistency with other scenes.
"""

import pygame
import math
from typing import Optional, Dict
from .scene import Scene
from airwar.components.tutorial import TutorialPanel, TutorialNavigator, TutorialRenderer
from airwar.config.design_tokens import get_design_tokens
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.utils.responsive import ResponsiveHelper
from airwar.utils.mouse_interaction import MouseInteractiveMixin


class TutorialScene(Scene, MouseInteractiveMixin):
    """
    Tutorial scene class - coordinates all tutorial components.

    This class follows the Facade Pattern by providing a simple interface
    to the underlying components (Panel, Navigator, Renderer). It manages
    the scene lifecycle and coordinates event handling between components.
    Uses DesignTokens for visual consistency with other scenes.
    """

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._is_running = False
        self._exit_requested = False
        self._panel = TutorialPanel()
        self._navigator = TutorialNavigator()
        self._renderer = TutorialRenderer()
        self._animation_time = 0
        self._stars = []
        self._particles = []

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
        """
        Initialize the tutorial scene.

        Args:
            **kwargs: Optional parameters (not used currently)
        """
        self.clear_hover()
        self.clear_buttons()
        self._is_running = True
        self._exit_requested = False
        self._panel.reset()
        self._navigator.reset()
        self._renderer.reset()
        self._animation_time = 0
        self._particle_system.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

    def exit(self) -> None:
        """
        Clean up when exiting the tutorial scene.
        Performs necessary cleanup operations.
        """
        self._is_running = False
        self._exit_requested = False
        self._panel.reset()
        self._navigator.reset()
        self._renderer.reset()

    def reset(self) -> None:
        """
        Reset the tutorial scene to initial state.
        Called when returning to tutorial from another scene.
        """
        self.clear_hover()
        self.clear_buttons()
        self._is_running = True
        self._exit_requested = False
        self._panel.reset()
        self._navigator.reset()
        self._renderer.reset()
        self._animation_time = 0
        self._background_renderer = MenuBackground()
        self._particle_system.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

    def handle_events(self, event: pygame.event.Event) -> None:
        """
        Handle input events for the tutorial.

        Args:
            event: pygame event to handle
        """
        self._ensure_buttons_registered()
        
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._handle_button_click(self.get_hovered_button())

    def _ensure_buttons_registered(self) -> None:
        display_surface = pygame.display.get_surface()
        if display_surface is None:
            return
        screen_width = display_surface.get_width()
        screen_height = display_surface.get_height()
        self._register_buttons(screen_width, screen_height)

    def _handle_button_click(self, button_name: str) -> None:
        if button_name == 'exit':
            self._request_exit()
        elif button_name == 'next':
            if not self._navigator.is_last_step():
                self._navigator.next_step()
        elif button_name == 'prev':
            if not self._navigator.is_first_step():
                self._navigator.previous_step()

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """
        Handle keyboard input.

        Args:
            event: pygame KEYDOWN event
        """
        if event.key == pygame.K_ESCAPE:
            self._request_exit()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self._navigator.is_last_step():
                self._request_exit()
            else:
                self._navigator.next_step()
                self._navigator.set_selected_index(0)
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._navigator.previous_step()
            self._navigator.set_selected_index(0)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._navigator.next_step()
            self._navigator.set_selected_index(0)
        elif event.key in (pygame.K_UP, pygame.K_w):
            current_step = self._navigator.get_current_step()
            content = current_step.get('content', [])
            max_index = max(0, len(content) - 1)
            self._navigator.move_selection_up(max_index)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            current_step = self._navigator.get_current_step()
            content = current_step.get('content', [])
            max_index = max(0, len(content) - 1)
            self._navigator.move_selection_down(max_index)


    def _request_exit(self) -> None:
        """
        Request exit from the tutorial scene.
        """
        self._exit_requested = True
        self._is_running = False

    def update(self, *args, **kwargs) -> None:
        """
        Update tutorial state (called each frame).

        Args:
            *args: Additional arguments (not used)
            **kwargs: Additional keyword arguments (not used)
        """
        self._navigator.update()
        self._animation_time += 1

        self._background_renderer._animation_time = self._animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self._animation_time
        self._particle_system.update(direction=-1)

    def render(self, surface: pygame.Surface) -> None:
        """
        Render the tutorial scene.

        Args:
            surface: pygame.Surface to render on
        """
        current_step = self._navigator.get_current_step()
        progress = self._navigator.get_progress()
        current_index = self._navigator.get_current_index()
        selected_index = self._navigator.get_selected_index()

        self._renderer.render(
            surface,
            self._panel,
            current_step,
            progress,
            current_index,
            selected_index,
            self.colors,
            self._tokens,
            self._background_renderer,
            self._particle_system,
            self._animation_time
        )

    def _register_buttons(self, screen_width: int, screen_height: int) -> None:
        self.clear_buttons()
        
        if self._navigator.is_last_step():
            exit_rect = self._panel.get_button_rect(screen_width, screen_height, 'exit')
            self.register_button('exit', pygame.Rect(*exit_rect))
        else:
            next_rect = self._panel.get_button_rect(screen_width, screen_height, 'next')
            self.register_button('next', pygame.Rect(*next_rect))

        if not self._navigator.is_first_step():
            prev_rect = self._panel.get_button_rect(screen_width, screen_height, 'prev')
            self.register_button('prev', pygame.Rect(*prev_rect))

    def is_running(self) -> bool:
        """
        Check if the scene is currently running.

        Returns:
            True if scene is running
        """
        return self._is_running

    def is_ready(self) -> bool:
        """
        Check if the scene is ready (finished).
        For tutorial scene, ready means exit was requested.

        Returns:
            True if scene is ready to be switched
        """
        return not self._is_running

    def should_quit(self) -> bool:
        """
        Check if the scene should quit.

        Returns:
            True if quit was requested
        """
        return self._exit_requested

    def get_current_step_index(self) -> int:
        """
        Get the current step index.

        Returns:
            Current step index (0-based)
        """
        return self._navigator.get_current_index()

    def get_current_step(self) -> Dict:
        """
        Get the current step content.

        Returns:
            Dictionary containing step data
        """
        return self._navigator.get_current_step()

    def get_total_steps(self) -> int:
        """
        Get the total number of steps.

        Returns:
            Total number of steps
        """
        return self._navigator.get_total_steps()

    def is_complete(self) -> bool:
        """
        Check if tutorial is complete (at last step).

        Returns:
            True if at the last step
        """
        return self._navigator.is_last_step()
