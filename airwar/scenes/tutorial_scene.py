"""
Tutorial Scene Module

This module implements the TutorialScene class, which is the main scene
for the tutorial system. It coordinates the panel, navigator, and renderer
components to display an interactive tutorial interface.
Following the Facade Pattern - it provides a simple interface to complex subsystem.
"""

import pygame
from typing import Optional, Dict
from .scene import Scene
from airwar.components.tutorial import TutorialPanel, TutorialNavigator, TutorialRenderer


class TutorialScene(Scene):
    """
    Tutorial scene class - coordinates all tutorial components.
    
    This class follows the Facade Pattern by providing a simple interface
    to the underlying components (Panel, Navigator, Renderer). It manages
    the scene lifecycle and coordinates event handling between components.
    """

    def __init__(self):
        self._is_running = False
        self._exit_requested = False
        self._panel = TutorialPanel()
        self._navigator = TutorialNavigator()
        self._renderer = TutorialRenderer()
        self._animation_time = 0
        self._stars = []
        self._particles = []
        self._hovered_button = None

    def enter(self, **kwargs) -> None:
        """
        Initialize the tutorial scene.
        
        Args:
            **kwargs: Optional parameters (not used currently)
        """
        self._is_running = True
        self._exit_requested = False
        self._panel.reset()
        self._navigator.reset()
        self._renderer.reset()
        self._animation_time = 0
        self._hovered_button = None

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
        self._is_running = True
        self._exit_requested = False
        self._panel.reset()
        self._navigator.reset()
        self._renderer.reset()
        self._animation_time = 0
        self._hovered_button = None

    def handle_events(self, event: pygame.event.Event) -> None:
        """
        Handle input events for the tutorial.
        
        Args:
            event: pygame event to handle
        """
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse(event)

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
        elif event.key == pygame.K_LEFT:
            self._navigator.previous_step()
        elif event.key == pygame.K_RIGHT:
            self._navigator.next_step()

    def _handle_mouse(self, event: pygame.event.Event) -> None:
        """
        Handle mouse input.
        
        Args:
            event: pygame MOUSEBUTTONDOWN event
        """
        mouse_pos = event.pos
        
        if self._navigator.is_last_step():
            if self._is_exit_button_clicked(mouse_pos):
                self._request_exit()
        else:
            if self._is_next_button_clicked(mouse_pos):
                self._navigator.next_step()
        
        if not self._navigator.is_first_step():
            if self._is_prev_button_clicked(mouse_pos):
                self._navigator.previous_step()

    def _is_prev_button_clicked(self, mouse_pos: tuple) -> bool:
        """
        Check if the previous button was clicked.
        
        Args:
            mouse_pos: Mouse position (x, y)
            
        Returns:
            True if previous button was clicked
        """
        return self._navigator.is_button_clicked(mouse_pos, 'prev')

    def _is_next_button_clicked(self, mouse_pos: tuple) -> bool:
        """
        Check if the next button was clicked.
        
        Args:
            mouse_pos: Mouse position (x, y)
            
        Returns:
            True if next button was clicked
        """
        return self._navigator.is_button_clicked(mouse_pos, 'next')

    def _is_exit_button_clicked(self, mouse_pos: tuple) -> bool:
        """
        Check if the exit button was clicked.
        
        Args:
            mouse_pos: Mouse position (x, y)
            
        Returns:
            True if exit button was clicked
        """
        return self._navigator.is_button_clicked(mouse_pos, 'exit')

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

    def render(self, surface: pygame.Surface) -> None:
        """
        Render the tutorial scene.
        
        Args:
            surface: pygame.Surface to render on
        """
        current_step = self._navigator.get_current_step()
        progress = self._navigator.get_progress()
        
        self._renderer.render(
            surface,
            self._panel,
            current_step,
            progress
        )

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
