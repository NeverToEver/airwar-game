"""
Test module for Tutorial System Integration.

This module contains integration tests for the single-page tutorial system.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene
from airwar.scenes.tutorial import TutorialRenderer
from airwar.config.tutorial import TUTORIAL_CONTENT
from airwar.config.design_tokens import get_design_tokens


class TestTutorialIntegration:
    def test_tutorial_content_has_required_structure(self):
        """Test that TUTORIAL_CONTENT has the expected structure."""
        assert 'title' in TUTORIAL_CONTENT
        assert 'subtitle' in TUTORIAL_CONTENT
        assert 'sections' in TUTORIAL_CONTENT
        assert len(TUTORIAL_CONTENT['sections']) == 4

    def test_tutorial_sections_have_required_fields(self):
        """Test that all sections have required fields."""
        for section in TUTORIAL_CONTENT['sections']:
            assert 'title' in section
            assert 'icon' in section
            assert 'items' in section
            assert len(section['items']) > 0

    def test_tutorial_items_have_key_and_desc(self):
        """Test that all items have 'key' and 'desc' fields."""
        for section in TUTORIAL_CONTENT['sections']:
            for item in section['items']:
                assert 'key' in item
                assert 'desc' in item

    def test_scene_renders_without_crashing(self):
        """Test that the tutorial scene renders correctly."""
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))

        scene = TutorialScene()
        scene.enter()

        for _ in range(10):
            scene.update()
            scene.render(surface)

        pygame.quit()

    def test_escape_exits_scene(self):
        """Test that ESC key exits the scene."""
        scene = TutorialScene()
        scene.enter()

        assert scene.is_running()
        assert not scene.should_quit()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)

        assert not scene.is_running()
        assert scene.should_quit()

    def test_enter_exits_scene(self):
        """Test that ENTER key exits the scene."""
        scene = TutorialScene()
        scene.enter()

        enter_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        scene.handle_events(enter_event)

        assert not scene.is_running()
        assert scene.should_quit()

    def test_space_exits_scene(self):
        """Test that SPACE key exits the scene."""
        scene = TutorialScene()
        scene.enter()

        space_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE})
        scene.handle_events(space_event)

        assert not scene.is_running()
        assert scene.should_quit()

    def test_scene_reset(self):
        """Test that scene can be reset."""
        scene = TutorialScene()
        scene.enter()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)

        scene.reset()

        assert scene.is_running()
        assert not scene.should_quit()

    def test_renderer_initialization(self):
        """Test that renderer initializes correctly."""
        renderer = TutorialRenderer()
        renderer.reset()
        assert renderer is not None

    def test_color_scheme_defined(self):
        """Test that color scheme is properly defined."""
        tokens = get_design_tokens()
        colors = tokens.colors
        assert hasattr(colors, 'BACKGROUND_PRIMARY')
        assert hasattr(colors, 'HUD_AMBER')
        assert hasattr(colors, 'TEXT_PRIMARY')
        assert hasattr(colors, 'BUTTON_SELECTED_BG')
        assert hasattr(colors, 'BUTTON_UNSELECTED_BG')

    def test_scene_with_pygame_surface(self):
        """Test complete scene lifecycle with pygame surface."""
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))

        scene = TutorialScene()
        scene.enter()

        for _ in range(5):
            scene.update()
            scene.render(surface)

        assert scene.is_running()

        escape_event = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(escape_event)
        assert scene.should_quit()

        pygame.quit()

    def test_all_control_keys_documented(self):
        """Test that all major control keys are documented in tutorial."""
        all_keys = set()
        for section in TUTORIAL_CONTENT['sections']:
            for item in section['items']:
                all_keys.add(item['key'])

        assert 'W / ↑' in all_keys or 'W' in str(all_keys)
        assert 'SPACE' in all_keys
        assert 'ESC' in all_keys
