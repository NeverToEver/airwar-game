import pytest
from airwar.scenes.death_scene import DeathScene


class TestDeathScene:
    def test_death_scene_can_be_created(self):
        scene = DeathScene()
        assert scene is not None

    def test_death_scene_has_options(self):
        scene = DeathScene()
        scene.enter(score=1000, kills=10, username='TestPlayer')
        assert hasattr(scene, 'options')
        assert len(scene.options) == 2
        assert 'RETURN TO MAIN MENU' in scene.options
        assert 'QUIT GAME' in scene.options

    def test_death_scene_initial_state(self):
        scene = DeathScene()
        scene.enter(score=500, kills=5, username='TestPlayer')
        assert scene.running is True
        assert scene.selected_index == 0
        assert scene.score == 500
        assert scene.kills == 5
        assert scene.username == 'TestPlayer'

    def test_death_scene_navigation_up(self):
        import pygame
        scene = DeathScene()
        scene.enter()
        initial_index = scene.selected_index
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
        scene.handle_events(event)
        assert scene.selected_index == (initial_index - 1) % len(scene.options)

    def test_death_scene_navigation_down(self):
        import pygame
        scene = DeathScene()
        scene.enter()
        initial_index = scene.selected_index
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
        scene.handle_events(event)
        assert scene.selected_index == (initial_index + 1) % len(scene.options)

    def test_death_scene_select_option_returns_to_menu(self):
        import pygame
        scene = DeathScene()
        scene.enter()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        scene.handle_events(event)
        assert scene.running is False
        assert scene.result == 'return_to_menu'

    def test_death_scene_select_quit_option(self):
        import pygame
        scene = DeathScene()
        scene.enter()
        scene.selected_index = 1
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        scene.handle_events(event)
        assert scene.running is False
        assert scene.result == 'quit'

    def test_death_scene_update_changes_animation_time(self):
        scene = DeathScene()
        scene.enter()
        initial_time = scene.animation_time
        scene.update()
        assert scene.animation_time > initial_time

    def test_death_scene_get_result_returns_correct_value(self):
        scene = DeathScene()
        scene.enter()
        scene._select_option = lambda: setattr(scene, 'result', 'return_to_menu')
        scene._select_option()
        assert scene.get_result() == 'return_to_menu'

    def test_death_scene_is_running_returns_true_initially(self):
        scene = DeathScene()
        scene.enter()
        assert scene.is_running() is True

    def test_death_scene_is_running_returns_false_after_selection(self):
        scene = DeathScene()
        scene.enter()
        scene.selected_index = 0
        scene.handle_events(type('Event', (), {'type': 768, 'key': 13})())
        assert scene.is_running() is False
