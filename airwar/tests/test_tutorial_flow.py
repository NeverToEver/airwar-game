"""
Test module for Tutorial System Integration.

This module contains integration tests for the complete tutorial system flow.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene
from airwar.components.tutorial import TutorialPanel, TutorialNavigator, TutorialRenderer
from airwar.config.tutorial import TUTORIAL_STEPS
from airwar.config.design_tokens import get_design_tokens


class TestTutorialIntegration:
    def test_complete_tutorial_flow(self):
        scene = TutorialScene()
        scene.enter()
        
        assert scene.get_current_step_index() == 0
        assert scene.get_current_step()['id'] == 'welcome'
        
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
        assert len(TUTORIAL_STEPS) == 5
        
        step_ids = [step['id'] for step in TUTORIAL_STEPS]
        assert 'welcome' in step_ids
        assert 'movement' in step_ids
        assert 'buff' in step_ids
        assert 'mechanics' in step_ids
        assert 'ready' in step_ids

    def test_refactor_unchanged_behavior(self):
        assert len(TUTORIAL_STEPS) == 5
        assert TUTORIAL_STEPS[0]['id'] == 'welcome'
        assert TUTORIAL_STEPS[0]['type'] == 'welcome'
        assert TUTORIAL_STEPS[-1]['is_complete'] == True
        assert TUTORIAL_STEPS[1]['id'] == 'movement'
        assert TUTORIAL_STEPS[2]['id'] == 'buff'
        assert TUTORIAL_STEPS[3]['id'] == 'mechanics'

    def test_color_scheme_defined(self):
        tokens = get_design_tokens()
        colors = tokens.colors
        assert hasattr(colors, 'BACKGROUND_PRIMARY')
        assert hasattr(colors, 'HUD_AMBER')
        assert hasattr(colors, 'TEXT_PRIMARY')
        assert hasattr(colors, 'BUTTON_SELECTED_BG')
        assert hasattr(colors, 'BUTTON_UNSELECTED_BG')

    def test_tutorial_scene_with_pygame_surface(self):
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
        scene = TutorialScene()
        scene.enter()
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        assert scene.get_current_step_index() == 2
        
        scene.enter()
        assert scene.get_current_step_index() == 0

    def test_all_step_content(self):
        for step in TUTORIAL_STEPS:
            assert 'id' in step
            assert 'title' in step
            assert 'content' in step
            
            if not step.get('is_complete'):
                content = step['content']
                if step.get('type') == 'welcome':
                    for item in content:
                        assert 'text' in item
                else:
                    assert len(content) > 0
                    for item in content:
                        assert 'key' in item
                        assert 'description' in item

    def test_scene_runs_without_crashing(self):
        scene = TutorialScene()
        scene.enter()
        
        for _ in range(100):
            scene.update()
            
            if not scene.is_running():
                break
        
        assert scene.get_current_step_index() >= 0

    def test_mixed_input_events(self):
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
            current_index = navigator.get_current_index()
            selected_index = navigator.get_selected_index()
            renderer.render(
                surface, panel, step, progress, current_index, selected_index,
                scene.colors, scene._tokens, scene._background_renderer,
                scene._particle_system, scene._animation_time
            )

        pygame.quit()

    def test_welcome_step_type(self):
        welcome_step = TUTORIAL_STEPS[0]
        assert welcome_step['id'] == 'welcome'
        assert welcome_step['type'] == 'welcome'
        assert welcome_step['title'] == 'Welcome Commander'

    def test_mechanics_step_has_l_key(self):
        mechanics_step = TUTORIAL_STEPS[3]
        assert mechanics_step['id'] == 'mechanics'
        
        l_key_item = next((item for item in mechanics_step['content'] if item['key'] == 'L'), None)
        assert l_key_item is not None
        assert l_key_item['description'] == 'Toggle HUD panel'

    def test_keyboard_navigation_up_down(self):
        scene = TutorialScene()
        scene.enter()
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT}))
        assert scene.get_current_step_index() == 2
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP}))

    def test_progress_indicator_with_selection(self):
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        
        scene = TutorialScene()
        scene.enter()
        
        for i in range(5):
            scene.update()
            scene.render(surface)
            
        pygame.quit()
