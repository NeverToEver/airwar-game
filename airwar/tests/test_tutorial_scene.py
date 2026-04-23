"""
Test module for TutorialScene.

This module contains unit tests for the simplified single-page TutorialScene class.
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

    def test_exit_does_not_crash(self):
        """Test that exit() can be called safely."""
        scene = TutorialScene()
        scene.exit()

    def test_reset(self):
        """Test that reset() restarts the scene."""
        scene = TutorialScene()
        scene.enter()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)

        scene.reset()
        assert scene.is_running()
        assert not scene.should_quit()

    def test_escape_key_quits_scene(self):
        """Test that ESC key requests quit."""
        scene = TutorialScene()
        scene.enter()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)

        assert not scene.is_running()
        assert scene.should_quit()

    def test_return_key_quits_scene(self):
        """Test that RETURN key quits the scene."""
        scene = TutorialScene()
        scene.enter()

        return_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        scene.handle_events(return_event)

        assert not scene.is_running()
        assert scene.should_quit()

    def test_space_key_quits_scene(self):
        """Test that SPACE key quits the scene."""
        scene = TutorialScene()
        scene.enter()

        space_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE})
        scene.handle_events(space_event)

        assert not scene.is_running()
        assert scene.should_quit()

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

    def test_mouse_event_does_not_crash(self):
        """Test that mouse events are handled without errors."""
        scene = TutorialScene()
        scene.enter()

        mouse_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (640, 360)})
        scene.handle_events(mouse_event)

    def test_mouse_click_on_start_button_area(self):
        """Test mouse click in the general area of the start button."""
        scene = TutorialScene()
        scene.enter()

        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        scene.render(surface)

        mouse_event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (640, 600)})
        scene.handle_events(mouse_event)

        pygame.quit()

    def test_is_ready(self):
        """Test is_ready() method."""
        scene = TutorialScene()
        assert scene.is_ready()

        scene.enter()
        assert not scene.is_ready()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        assert scene.is_ready()
