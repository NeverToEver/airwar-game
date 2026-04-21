"""
Test module for TutorialScene.

This module contains unit tests for the TutorialScene class.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene


class TestTutorialScene:
    """Test suite for TutorialScene class."""

    def test_initialization(self):
        """Test that scene initializes correctly."""
        scene = TutorialScene()
        assert scene is not None
        assert not scene.is_running()
        assert not scene.should_quit()

    def test_enter_starts_scene(self):
        """Test that enter() starts the scene."""
        scene = TutorialScene()
        scene.enter()
        assert scene.is_running()
        assert not scene.should_quit()

    def test_enter_resets_state(self):
        """Test that enter() resets all state."""
        scene = TutorialScene()
        scene.enter()
        assert scene.get_current_step_index() == 0
        assert scene.get_total_steps() == 4
        assert not scene.is_complete()

    def test_exit_does_not_crash(self):
        """Test that exit() can be called safely."""
        scene = TutorialScene()
        scene.exit()

    def test_escape_key_quits_scene(self):
        """Test that ESC key requests quit."""
        scene = TutorialScene()
        scene.enter()
        
        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        
        assert not scene.is_running()
        assert scene.should_quit()

    def test_return_key_at_last_step_quits(self):
        """Test that RETURN key quits at last step."""
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(3):
            right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
            scene.handle_events(right_event)
            scene.update()
        
        return_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        scene.handle_events(return_event)
        
        assert not scene.is_running()
        assert scene.should_quit()

    def test_space_key_at_last_step_quits(self):
        """Test that SPACE key quits at last step."""
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(3):
            right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
            scene.handle_events(right_event)
            scene.update()
        
        space_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE})
        scene.handle_events(space_event)
        
        assert not scene.is_running()
        assert scene.should_quit()

    def test_left_key_navigates_previous(self):
        """Test that LEFT key navigates to previous step."""
        scene = TutorialScene()
        scene.enter()
        
        left_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT})
        scene.handle_events(left_event)
        
        assert scene.get_current_step_index() == 0

    def test_right_key_navigates_next(self):
        """Test that RIGHT key navigates to next step."""
        scene = TutorialScene()
        scene.enter()
        
        right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
        scene.handle_events(right_event)
        
        assert scene.get_current_step_index() == 1

    def test_update_increments_animation(self):
        """Test that update() can be called without errors."""
        scene = TutorialScene()
        scene.enter()
        scene.update()

    def test_render_does_not_crash(self):
        """Test that render() can be called without errors."""
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        scene = TutorialScene()
        scene.enter()
        scene.render(surface)
        pygame.quit()

    def test_scene_lifecycle(self):
        """Test complete scene lifecycle."""
        scene = TutorialScene()
        
        assert not scene.is_running()
        scene.enter()
        assert scene.is_running()
        
        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        
        assert not scene.is_running()
        assert scene.should_quit()

    def test_multiple_navigation_events(self):
        """Test handling multiple navigation events."""
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(2):
            right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
            scene.handle_events(right_event)
            scene.update()
        
        assert scene.get_current_step_index() == 2

    def test_mouse_event_does_not_crash(self):
        """Test that mouse events are handled without errors."""
        scene = TutorialScene()
        scene.enter()
        
        mouse_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (640, 360)})
        scene.handle_events(mouse_event)

    def test_get_current_step_index(self):
        """Test step index getter."""
        scene = TutorialScene()
        scene.enter()
        assert scene.get_current_step_index() == 0

    def test_get_total_steps(self):
        """Test total steps getter."""
        scene = TutorialScene()
        scene.enter()
        assert scene.get_total_steps() > 0

    def test_is_complete_at_start(self):
        """Test that is_complete is False at start."""
        scene = TutorialScene()
        scene.enter()
        assert not scene.is_complete()

    def test_is_complete_at_end(self):
        """Test that is_complete is True at last step."""
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(3):
            right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
            scene.handle_events(right_event)
            scene.update()
        
        assert scene.is_complete()
