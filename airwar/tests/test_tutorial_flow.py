"""
Test module for Tutorial System Integration.

This module contains integration tests for the complete tutorial system flow.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene
from airwar.components.tutorial import TutorialPanel, TutorialNavigator, TutorialRenderer
from airwar.configs.tutorial import TUTORIAL_STEPS, TUTORIAL_COLORS


class TestTutorialIntegration:
    """Integration tests for the tutorial system."""

    def test_complete_tutorial_flow(self):
        """Test complete navigation through all tutorial steps."""
        scene = TutorialScene()
        scene.enter()
        
        assert scene.get_current_step_index() == 0
        assert scene.get_current_step()['id'] == 'movement'
        
        for i in range(1, len(TUTORIAL_STEPS)):
            right_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
            scene.handle_events(right_event)
            scene.update()
            assert scene.get_current_step_index() == i
        
        assert scene.is_complete()
        
        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        assert scene.should_quit()

    def test_back_and_forth_navigation(self):
        """Test navigating back and forth between steps."""
        scene = TutorialScene()
        scene.enter()
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        assert scene.get_current_step_index() == 1
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT}))
        assert scene.get_current_step_index() == 0
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        assert scene.get_current_step_index() == 2

    def test_component_integration(self):
        """Test that all components work together."""
        panel = TutorialPanel()
        navigator = TutorialNavigator()
        renderer = TutorialRenderer()
        
        layout = panel.calculate_layout(1280, 720)
        assert layout is not None
        
        step = navigator.get_current_step()
        assert step is not None
        assert 'id' in step
        
        progress = navigator.get_progress()
        assert len(progress) == len(TUTORIAL_STEPS)

    def test_tutorial_config_loaded(self):
        """Test that tutorial configuration is properly loaded."""
        assert len(TUTORIAL_STEPS) == 4
        
        step_ids = [step['id'] for step in TUTORIAL_STEPS]
        assert 'movement' in step_ids
        assert 'mother_ship' in step_ids
        assert 'pause' in step_ids
        assert 'complete' in step_ids

    def test_color_scheme_defined(self):
        """Test that color scheme is properly defined."""
        assert 'background' in TUTORIAL_COLORS
        assert 'panel_background' in TUTORIAL_COLORS
        assert 'title' in TUTORIAL_COLORS
        assert 'key_highlight' in TUTORIAL_COLORS
        assert 'button_normal' in TUTORIAL_COLORS

    def test_tutorial_scene_with_pygame_surface(self):
        """Test rendering tutorial scene to pygame surface."""
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(5):
            scene.update()
            scene.render(surface)
        
        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        
        pygame.quit()

    def test_navigator_resets_scene_state(self):
        """Test that navigator reset works with scene."""
        scene = TutorialScene()
        scene.enter()
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        assert scene.get_current_step_index() == 2
        
        scene.enter()
        assert scene.get_current_step_index() == 0

    def test_all_step_content(self):
        """Test that all tutorial steps have valid content."""
        for step in TUTORIAL_STEPS:
            assert 'id' in step
            assert 'title' in step
            assert 'icon' in step
            assert 'content' in step
            
            if not step.get('is_complete'):
                assert len(step['content']) > 0
                for item in step['content']:
                    assert 'key' in item
                    assert 'description' in item

    def test_scene_runs_without_crashing(self):
        """Test that scene can run through multiple updates without crashing."""
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(100):
            scene.update()
            
            if not scene.is_running():
                break
        
        assert scene.get_current_step_index() >= 0

    def test_mixed_input_events(self):
        """Test handling of mixed keyboard and mouse events."""
        scene = TutorialScene()
        scene.enter()
        
        events = [
            pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (640, 360)}),
            pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT}),
        ]
        
        for event in events:
            scene.handle_events(event)
        
        scene.update()

    def test_render_with_components(self):
        """Test rendering with real components."""
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        
        scene = TutorialScene()
        panel = TutorialPanel()
        navigator = TutorialNavigator()
        renderer = TutorialRenderer()
        
        scene.enter()
        
        for _ in range(3):
            scene.update()
            navigator.update()
            
            step = navigator.get_current_step()
            progress = navigator.get_progress()
            renderer.render(surface, panel, step, progress)
        
        pygame.quit()
