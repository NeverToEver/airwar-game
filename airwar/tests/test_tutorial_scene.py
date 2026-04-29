"""Tests for TutorialScene — multi-page pagination and navigation."""
import pytest
import pygame
from airwar.scenes.tutorial_scene import TutorialScene


class TestTutorialScene:
    """Unit tests for TutorialScene — pagination, keyboard, lifecycle."""

    def test_initialization(self):
        scene = TutorialScene()
        assert scene is not None
        assert not scene.should_quit()
        assert scene._current_page == 0
        assert scene._total_pages == 4

    def test_enter_starts_scene(self):
        scene = TutorialScene()
        scene.enter()
        assert scene.is_running()
        assert not scene.should_quit()
        assert scene._current_page == 0

    def test_exit_does_not_crash(self):
        scene = TutorialScene()
        scene.enter()
        scene.exit()

    def test_escape_key_quits_scene(self):
        scene = TutorialScene()
        scene.enter()
        esc = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(esc)
        assert scene.should_quit()

    def test_right_arrow_advances_page(self):
        scene = TutorialScene()
        scene.enter()
        assert scene._current_page == 0
        right = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
        scene.handle_events(right)
        assert scene._current_page == 1

    def test_left_arrow_goes_back(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 2
        left = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT})
        scene.handle_events(left)
        assert scene._current_page == 1

    def test_right_arrow_at_last_page_does_nothing(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 3  # last page
        right = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RIGHT})
        scene.handle_events(right)
        assert scene._current_page == 3  # unchanged

    def test_left_arrow_at_first_page_does_nothing(self):
        scene = TutorialScene()
        scene.enter()
        left = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_LEFT})
        scene.handle_events(left)
        assert scene._current_page == 0  # unchanged

    def test_down_arrow_advances_page(self):
        scene = TutorialScene()
        scene.enter()
        down = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN})
        scene.handle_events(down)
        assert scene._current_page == 1

    def test_up_arrow_goes_back(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 1
        up = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP})
        scene.handle_events(up)
        assert scene._current_page == 0

    def test_enter_key_on_last_page_quits(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 3  # last page
        ret = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        scene.handle_events(ret)
        assert scene.should_quit()

    def test_enter_key_not_on_last_page_does_not_quit(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 0  # not last page
        ret = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN})
        scene.handle_events(ret)
        assert not scene.should_quit()

    def test_modifier_keys_ignored(self):
        """Non-navigation keys should not change state."""
        scene = TutorialScene()
        scene.enter()
        for key in (pygame.K_a, pygame.K_TAB, pygame.K_F1):
            ev = pygame.event.Event(pygame.KEYDOWN, {'key': key})
            scene.handle_events(ev)
        assert scene._current_page == 0
        assert not scene.should_quit()

    def test_reset_clears_state(self):
        scene = TutorialScene()
        scene.enter()
        scene._current_page = 2
        scene.reset()
        assert scene._current_page == 0
        assert scene.is_running()
        assert not scene.should_quit()

    def test_update_does_not_crash(self):
        scene = TutorialScene()
        scene.enter()
        for _ in range(10):
            scene.update()

    def test_render_does_not_crash(self):
        pygame.init()
        surface = pygame.display.set_mode((1280, 720))
        scene = TutorialScene()
        scene.enter()
        for pg in range(4):
            scene._current_page = pg
            scene.render(surface)
        pygame.quit()

    def test_mouse_events_do_not_crash(self):
        pygame.init()
        pygame.display.set_mode((1280, 720))
        scene = TutorialScene()
        scene.enter()
        scene.render(pygame.display.get_surface())
        mev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (640, 600), 'button': 1})
        scene.handle_events(mev)
        pygame.quit()

    def test_is_ready(self):
        scene = TutorialScene()
        scene.enter()
        assert not scene.is_ready()
        esc = pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE})
        scene.handle_events(esc)
        assert scene.is_ready()
