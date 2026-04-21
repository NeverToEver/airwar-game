"""
Tutorial Navigator Component

This module implements the TutorialNavigator class, which manages
step navigation state and button interactions for the tutorial system.
Following the Single Responsibility Principle - it only handles navigation logic.
"""

from typing import Dict, List, Optional, Tuple
import pygame
from airwar.configs.tutorial import TUTORIAL_STEPS


class TutorialNavigator:
    """
    Tutorial navigator component responsible for step navigation.
    
    This class follows the Single Responsibility Principle by only handling
    navigation state and transitions. It does not handle rendering.
    """

    def __init__(self):
        self._current_index = 0
        self._total_steps = len(TUTORIAL_STEPS)
        self._buttons = {
            'prev': None,
            'next': None,
            'exit': None,
        }
        self._hovered_button = None
        self._animation_time = 0

    def reset(self) -> None:
        """
        Reset navigation state to initial values.
        """
        self._current_index = 0
        self._hovered_button = None

    def next_step(self) -> bool:
        """
        Navigate to the next step.
        
        Returns:
            True if navigation was successful, False if already at last step
        """
        if self._current_index < self._total_steps - 1:
            self._current_index += 1
            return True
        return False

    def previous_step(self) -> bool:
        """
        Navigate to the previous step.
        
        Returns:
            True if navigation was successful, False if already at first step
        """
        if self._current_index > 0:
            self._current_index -= 1
            return True
        return False

    def get_current_step(self) -> Dict:
        """
        Get the current step content.
        
        Returns:
            Dictionary containing step data (id, title, icon, content, etc.)
        """
        return TUTORIAL_STEPS[self._current_index]

    def get_progress(self) -> List[bool]:
        """
        Get the progress state for all steps.
        
        Returns:
            List of booleans indicating which steps are active/completed
        """
        return [i <= self._current_index for i in range(self._total_steps)]

    def get_current_index(self) -> int:
        """
        Get the current step index.
        
        Returns:
            Current step index (0-based)
        """
        return self._current_index

    def get_total_steps(self) -> int:
        """
        Get the total number of steps.
        
        Returns:
            Total number of steps
        """
        return self._total_steps

    def is_first_step(self) -> bool:
        """
        Check if currently at the first step.
        
        Returns:
            True if at first step, False otherwise
        """
        return self._current_index == 0

    def is_last_step(self) -> bool:
        """
        Check if currently at the last step.
        
        Returns:
            True if at last step, False otherwise
        """
        return self._current_index == self._total_steps - 1

    def is_complete_step(self) -> bool:
        """
        Check if current step is the completion step.
        
        Returns:
            True if at completion step, False otherwise
        """
        current_step = self.get_current_step()
        return current_step.get('is_complete', False)

    def update(self) -> None:
        """
        Update navigation state (called each frame).
        """
        self._animation_time += 1
        try:
            mouse_pos = pygame.mouse.get_pos()
            self._update_button_hover(mouse_pos)
        except pygame.error:
            pass

    def _update_button_hover(self, mouse_pos: Tuple[int, int]) -> None:
        """
        Update which button is currently being hovered.
        
        Args:
            mouse_pos: Current mouse position (x, y)
        """
        self._hovered_button = None
        
        for button_name, button_rect in self._buttons.items():
            if button_rect and button_rect.collidepoint(mouse_pos):
                self._hovered_button = button_name
                break

    def set_button_rect(self, button_name: str, rect: pygame.Rect) -> None:
        """
        Set the rectangle for a navigation button.
        
        Args:
            button_name: Name of the button ('prev', 'next', 'exit')
            rect: pygame.Rect defining button bounds
        """
        if button_name in self._buttons:
            self._buttons[button_name] = rect

    def get_button_rect(self, button_name: str) -> Optional[pygame.Rect]:
        """
        Get the rectangle for a navigation button.
        
        Args:
            button_name: Name of the button ('prev', 'next', 'exit')
            
        Returns:
            pygame.Rect or None if not set
        """
        return self._buttons.get(button_name)

    def is_button_hovered(self, button_name: str) -> bool:
        """
        Check if a button is currently being hovered.
        
        Args:
            button_name: Name of the button ('prev', 'next', 'exit')
            
        Returns:
            True if button is hovered, False otherwise
        """
        return self._hovered_button == button_name

    def is_button_clicked(self, mouse_pos: Tuple[int, int], button_name: str) -> bool:
        """
        Check if a button was clicked at the given position.
        
        Args:
            mouse_pos: Mouse position at time of click (x, y)
            button_name: Name of the button ('prev', 'next', 'exit')
            
        Returns:
            True if button was clicked, False otherwise
        """
        button_rect = self._buttons.get(button_name)
        if button_rect:
            return button_rect.collidepoint(mouse_pos)
        return False

    def get_animation_time(self) -> int:
        """
        Get the current animation time.
        
        Returns:
            Animation time counter
        """
        return self._animation_time

    def can_go_previous(self) -> bool:
        """
        Check if navigation to previous step is possible.
        
        Returns:
            True if can go to previous step, False if at first step
        """
        return not self.is_first_step()

    def can_go_next(self) -> bool:
        """
        Check if navigation to next step is possible.
        
        Returns:
            True if can go to next step, False if at last step
        """
        return not self.is_last_step()
