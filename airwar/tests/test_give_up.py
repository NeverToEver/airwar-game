import pytest
from unittest.mock import patch, MagicMock
import pygame


class TestGiveUpDetector:
    def test_give_up_detector_creation(self):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        assert detector is not None
        assert detector.get_progress() == 0.0
        assert detector.is_active() is False

    def test_give_up_detector_initial_state(self):
        from airwar.game.give_up import GiveUpDetector
        detector = GiveUpDetector(MagicMock())
        assert detector._progress == 0.0
        assert detector._is_complete is False
        assert detector._k_was_pressed is False

    def test_give_up_detector_reset(self):
        from airwar.game.give_up import GiveUpDetector
        detector = GiveUpDetector(MagicMock())
        detector._progress = 0.5
        detector._is_complete = True
        detector._k_was_pressed = True
        detector.reset()
        assert detector._progress == 0.0
        assert detector._is_complete is False
        assert detector._k_was_pressed is False

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_k_pressed(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        mock_get_pressed.return_value = {pygame.K_k: True}
        detector._k_was_pressed = False
        detector.update(1/60)
        assert detector._progress == 0.0
        assert detector._k_was_pressed is True

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_k_released_resets_progress(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        detector._progress = 0.5
        detector._k_was_pressed = True
        mock_get_pressed.return_value = {pygame.K_k: False}
        detector.update(1/60)
        assert detector._progress == 0.0
        assert detector._k_was_pressed is False

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_progress_increases(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        mock_get_pressed.return_value = {pygame.K_k: True}
        detector._k_was_pressed = True
        detector._progress = 0.1
        detector.update(1/60)
        assert detector._progress > 0.1

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_complete_triggers_callback(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        mock_get_pressed.return_value = {pygame.K_k: True}
        detector._k_was_pressed = True
        detector._progress = 0.99
        detector.update(3.0)
        assert callback.called

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_is_active_when_pressing(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        detector = GiveUpDetector(MagicMock())
        mock_get_pressed.return_value = {pygame.K_k: True}
        detector._k_was_pressed = True
        detector._progress = 0.1
        detector.update(1/60)
        assert detector.is_active() is True

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_is_not_active_when_not_pressing(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        detector = GiveUpDetector(MagicMock())
        mock_get_pressed.return_value = {pygame.K_k: False}
        detector._k_was_pressed = False
        detector._progress = 0.0
        assert detector.is_active() is False

    @patch('pygame.key.get_pressed')
    def test_give_up_detector_hold_duration(self, mock_get_pressed):
        from airwar.game.give_up import GiveUpDetector
        callback = MagicMock()
        detector = GiveUpDetector(callback)
        assert detector.HOLD_DURATION == 3.0


class TestGiveUpUI:
    def test_give_up_ui_creation(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        assert ui is not None
        assert ui._visible is False
        assert ui._progress == 0.0

    def test_give_up_ui_show(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        ui.show()
        assert ui._visible is True
        assert ui._progress == 0.0
        assert ui._animation_time == 0

    def test_give_up_ui_hide(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        ui._visible = True
        ui._progress = 0.5
        ui.hide()
        assert ui._visible is False
        assert ui._progress == 0.0

    def test_give_up_ui_update_progress(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        ui.show()
        ui.update_progress(0.5)
        assert ui._progress == 0.5

    def test_give_up_ui_update_animation_time(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        ui._animation_time = 10
        ui.update_progress(0.1)
        assert ui._animation_time == 11

    def test_give_up_ui_render_invisible(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        surface = MagicMock()
        ui._visible = False
        ui._progress = 0.5
        ui.render(surface)
        surface.blit.assert_not_called()

    def test_give_up_ui_render_zero_progress(self):
        from airwar.ui.give_up_ui import GiveUpUI
        ui = GiveUpUI(1400, 800)
        surface = MagicMock()
        ui._visible = True
        ui._progress = 0.0
        ui.render(surface)
        surface.blit.assert_not_called()

    def test_give_up_ui_render_visible(self):
        from airwar.ui.give_up_ui import GiveUpUI
        pygame.init()
        ui = GiveUpUI(1400, 800)
        surface = pygame.display.set_mode((1400, 800))
        ui._visible = True
        ui._progress = 0.5
        ui._animation_time = 10
        ui.render(surface)


class TestGiveUpIntegration:
    def test_give_up_system_integrated_in_game_scene(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        assert hasattr(scene, '_give_up_detector')
        assert hasattr(scene, '_give_up_ui')
        assert scene._give_up_detector is not None
        assert scene._give_up_ui is not None

    def test_can_use_give_up_playing_state(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.state.gameplay_state = GameplayState.PLAYING
        scene.game_controller.state.paused = False
        scene.reward_selector.visible = False
        assert scene._can_use_give_up() is True

    def test_cannot_use_give_up_paused_state(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.state.gameplay_state = GameplayState.PLAYING
        scene.game_controller.state.paused = True
        scene.reward_selector.visible = False
        assert scene._can_use_give_up() is False

    def test_cannot_use_give_up_game_over_state(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.state.gameplay_state = GameplayState.GAME_OVER
        scene.game_controller.state.paused = False
        scene.reward_selector.visible = False
        assert scene._can_use_give_up() is False

    def test_cannot_use_give_up_reward_selector_visible(self):
        from airwar.scenes.game_scene import GameScene
        from airwar.game.managers.game_controller import GameplayState
        scene = GameScene()
        scene.enter(difficulty='medium')
        scene.game_controller.state.gameplay_state = GameplayState.PLAYING
        scene.game_controller.state.paused = False
        scene.reward_selector.visible = True
        assert scene._can_use_give_up() is False

    def test_on_give_up_complete_triggers_death(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        initial_health = scene.player.health
        scene._on_give_up_complete()
        assert scene.player.health <= 0
