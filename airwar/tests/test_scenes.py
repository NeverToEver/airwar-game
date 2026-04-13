import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSceneManager:
    def test_scene_manager_creation(self):
        from airwar.scenes import SceneManager
        sm = SceneManager()
        assert sm._scenes == {}
        assert sm._current_scene is None

    def test_scene_manager_register(self):
        from airwar.scenes import SceneManager, MenuScene
        sm = SceneManager()
        scene = MenuScene()
        sm.register('menu', scene)
        assert 'menu' in sm._scenes
        assert sm._scenes['menu'] is scene

    def test_scene_manager_switch(self):
        from airwar.scenes import SceneManager, MenuScene
        sm = SceneManager()
        menu = MenuScene()
        sm.register('menu', menu)
        sm.switch('menu')
        assert sm._current_scene is menu
        assert sm._current_scene_name == 'menu'

    def test_scene_manager_get_current_scene(self):
        from airwar.scenes import SceneManager, MenuScene
        sm = SceneManager()
        menu = MenuScene()
        sm.register('menu', menu)
        sm.switch('menu')
        assert sm.get_current_scene() is menu


class TestSceneInterface:
    def test_scene_has_required_methods(self):
        from airwar.scenes import Scene
        required = ['enter', 'exit', 'handle_events', 'update', 'render']
        for method in required:
            assert hasattr(Scene, method)


class TestMenuScene:
    def test_menu_scene_enter_initializes(self):
        from airwar.scenes import MenuScene
        scene = MenuScene()
        scene.enter()
        assert scene.difficulty == 'medium'
        assert scene.selected_index == 1
        assert scene.difficulty_options == ['easy', 'medium', 'hard']

    def test_menu_scene_is_ready_initially_false(self):
        from airwar.scenes import MenuScene
        scene = MenuScene()
        scene.enter()
        assert scene.is_ready() is False

    def test_menu_scene_is_selection_confirmed_initially_false(self):
        from airwar.scenes import MenuScene
        scene = MenuScene()
        scene.enter()
        assert scene.is_selection_confirmed() is False

    def test_menu_scene_confirms_selection(self):
        from airwar.scenes import MenuScene
        import pygame
        pygame.init()
        scene = MenuScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
        assert scene.is_selection_confirmed() is True

    def test_menu_scene_back_on_escape(self):
        from airwar.scenes import MenuScene
        import pygame
        pygame.init()
        scene = MenuScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE}))
        assert scene.should_go_back() is True
        assert scene.running is False


class TestLoginScene:
    def test_login_scene_enter_initializes(self):
        from airwar.scenes import LoginScene
        scene = LoginScene()
        scene.enter()
        assert scene.mode == 'login'
        assert scene.username == ''
        assert scene.password == ''

    def test_login_scene_is_ready_initially_false(self):
        from airwar.scenes import LoginScene
        scene = LoginScene()
        scene.enter()
        assert scene.is_ready() is False

    def test_login_scene_should_quit_initially_false(self):
        from airwar.scenes import LoginScene
        scene = LoginScene()
        scene.enter()
        assert scene.should_quit() is False


class TestPauseScene:
    def test_pause_scene_enter_initializes(self):
        from airwar.scenes import PauseScene
        scene = PauseScene()
        scene.enter()
        assert scene.running is True
        assert scene.options == ['RESUME', 'MAIN MENU']

    def test_pause_scene_is_paused_initially_true(self):
        from airwar.scenes import PauseScene
        scene = PauseScene()
        scene.enter()
        assert scene.is_paused() is True
