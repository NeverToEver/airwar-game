import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExitConfirmAction:
    def test_exit_confirm_action_enum_exists(self):
        from airwar.scenes.scene import ExitConfirmAction
        assert hasattr(ExitConfirmAction, 'RETURN_TO_MENU')
        assert hasattr(ExitConfirmAction, 'START_NEW_GAME')
        assert hasattr(ExitConfirmAction, 'QUIT_GAME')

    def test_exit_confirm_action_values(self):
        from airwar.scenes.scene import ExitConfirmAction
        assert ExitConfirmAction.RETURN_TO_MENU.value == "return_to_menu"
        assert ExitConfirmAction.START_NEW_GAME.value == "start_new_game"
        assert ExitConfirmAction.QUIT_GAME.value == "quit_game"


class TestExitConfirmScene:
    def test_scene_can_be_imported(self):
        from airwar.scenes import ExitConfirmScene
        assert ExitConfirmScene is not None

    def test_scene_enter_initializes(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter()
        assert scene.running is True
        assert scene.result is None
        assert scene.selected_index == 0
        assert scene.saved is False
        assert scene.options == ['RETURN TO MENU', 'START NEW GAME', 'QUIT GAME']

    def test_scene_enter_with_saved_true(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter(saved=True)
        assert scene.saved is True

    def test_scene_enter_with_saved_false(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter(saved=False)
        assert scene.saved is False

    def test_scene_enter_with_difficulty(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter(difficulty='hard')
        assert scene.difficulty == 'hard'

    def test_scene_is_running_initially_true(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter()
        assert scene.is_running() is True

    def test_scene_get_result_initially_none(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter()
        assert scene.get_result() is None


class TestExitConfirmSceneKeyboard:
    def test_up_key_navigates_up(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP}))
        assert scene.selected_index == 2

    def test_w_key_navigates_up(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_w}))
        assert scene.selected_index == 2

    def test_down_key_navigates_down(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        assert scene.selected_index == 1

    def test_s_key_navigates_down(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_s}))
        assert scene.selected_index == 1

    def test_enter_key_selects_first_option(self):
        from airwar.scenes import ExitConfirmScene
        from airwar.scenes.scene import ExitConfirmAction
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
        assert scene.running is False
        assert scene.result == ExitConfirmAction.RETURN_TO_MENU

    def test_space_key_selects_option(self):
        from airwar.scenes import ExitConfirmScene
        from airwar.scenes.scene import ExitConfirmAction
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SPACE}))
        assert scene.running is False
        assert scene.result == ExitConfirmAction.RETURN_TO_MENU

    def test_escape_returns_to_menu(self):
        from airwar.scenes import ExitConfirmScene
        from airwar.scenes.scene import ExitConfirmAction
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_ESCAPE}))
        assert scene.running is False
        assert scene.result == ExitConfirmAction.RETURN_TO_MENU

    def test_navigate_to_second_option(self):
        from airwar.scenes import ExitConfirmScene
        from airwar.scenes.scene import ExitConfirmAction
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
        assert scene.result == ExitConfirmAction.START_NEW_GAME

    def test_navigate_to_third_option(self):
        from airwar.scenes import ExitConfirmScene
        from airwar.scenes.scene import ExitConfirmAction
        import pygame
        pygame.init()
        scene = ExitConfirmScene()
        scene.enter()
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN}))
        scene.handle_events(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_RETURN}))
        assert scene.result == ExitConfirmAction.QUIT_GAME


class TestExitConfirmSceneUpdate:
    def test_update_increments_animation_time(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter()
        initial_time = scene.animation_time
        scene.update()
        assert scene.animation_time > initial_time

    def test_update_changes_glow_offset(self):
        from airwar.scenes import ExitConfirmScene
        scene = ExitConfirmScene()
        scene.enter()
        scene.update()
        assert hasattr(scene, 'glow_offset')


class TestExitConfirmSceneRender:
    def test_render_does_not_raise(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        scene = ExitConfirmScene()
        scene.enter()
        scene.render(screen)
        pygame.display.quit()

    def test_render_with_saved_true(self):
        from airwar.scenes import ExitConfirmScene
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        scene = ExitConfirmScene()
        scene.enter(saved=True)
        scene.render(screen)
        pygame.display.quit()
