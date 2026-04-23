import pytest
import pygame
from unittest.mock import MagicMock, patch


class TestGameScenePauseButton:
    """测试 GameScene 暂停按钮的鼠标交互功能"""

    def setup_method(self):
        pygame.init()

    def teardown_method(self):
        pygame.quit()

    def _create_scene(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        return scene

    def test_pause_requested_initially_false(self):
        scene = self._create_scene()
        assert scene._pause_requested is False

    def test_consume_pause_request_returns_false_when_none(self):
        scene = self._create_scene()
        assert scene.consume_pause_request() is False

    def test_consume_pause_request_returns_true_and_resets(self):
        scene = self._create_scene()
        scene._pause_requested = True
        assert scene.consume_pause_request() is True
        assert scene._pause_requested is False
        assert scene.consume_pause_request() is False

    def test_handle_button_click_sets_pause_requested(self):
        scene = self._create_scene()
        scene._handle_button_click("pause")
        assert scene._pause_requested is True

    def test_handle_button_click_ignores_unknown_button(self):
        scene = self._create_scene()
        scene._handle_button_click("unknown")
        assert scene._pause_requested is False

    def test_mouse_click_on_pause_button_triggers_request(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        margin = scene.PAUSE_BUTTON_MARGIN
        size = scene.PAUSE_BUTTON_SIZE
        center_x = margin + size // 2
        center_y = margin + size // 2

        click_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (center_x, center_y)}
        )
        scene.handle_events(click_event)
        assert scene._pause_requested is True

    def test_mouse_click_outside_pause_button_no_request(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        click_event = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {'button': 1, 'pos': (500, 500)}
        )
        scene.handle_events(click_event)
        assert scene._pause_requested is False

    def test_mouse_motion_over_pause_button_updates_hover(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        margin = scene.PAUSE_BUTTON_MARGIN
        size = scene.PAUSE_BUTTON_SIZE
        center_x = margin + size // 2
        center_y = margin + size // 2

        motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (center_x, center_y)}
        )
        scene.handle_events(motion_event)
        assert scene.is_button_hovered("pause") is True

    def test_mouse_motion_away_clears_hover(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        margin = scene.PAUSE_BUTTON_MARGIN
        size = scene.PAUSE_BUTTON_SIZE
        center_x = margin + size // 2
        center_y = margin + size // 2

        motion_on = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (center_x, center_y)}
        )
        scene.handle_events(motion_on)
        assert scene.is_button_hovered("pause") is True

        motion_off = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (500, 500)}
        )
        scene.handle_events(motion_off)
        assert scene.is_button_hovered("pause") is False

    def test_render_pause_button_registers_button_rect(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        rect = scene.get_button_rect("pause")
        assert rect is not None
        assert rect.width == scene.PAUSE_BUTTON_SIZE
        assert rect.height == scene.PAUSE_BUTTON_SIZE

    def test_pause_button_not_rendered_when_paused(self):
        scene = self._create_scene()
        scene.pause()
        # 使用干净 surface 只渲染暂停按钮
        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        scene._render_pause_button(surface)

        # 按钮始终注册，但暂停时不应有渲染输出
        rect = scene.get_button_rect("pause")
        assert rect is not None
        button_area = surface.subsurface(rect)
        has_content = any(button_area.get_at((x, y))[3] > 0
                          for x in range(rect.width)
                          for y in range(rect.height))
        assert not has_content

    def test_pause_button_not_rendered_when_reward_visible(self):
        scene = self._create_scene()
        scene.reward_selector.visible = True
        # 使用干净 surface 只渲染暂停按钮
        surface = pygame.Surface((800, 600), pygame.SRCALPHA)
        scene._render_pause_button(surface)

        # 按钮始终注册，但奖励选择时不应有渲染输出
        rect = scene.get_button_rect("pause")
        assert rect is not None
        button_area = surface.subsurface(rect)
        has_content = any(button_area.get_at((x, y))[3] > 0
                          for x in range(rect.width)
                          for y in range(rect.height))
        assert not has_content

    def test_enter_resets_pause_request(self):
        scene = self._create_scene()
        scene._pause_requested = True
        scene.enter(difficulty='medium')
        assert scene._pause_requested is False

    def test_enter_clears_hover_and_reinitializes_layout(self):
        scene = self._create_scene()
        surface = pygame.Surface((800, 600))
        scene.render(surface)

        assert scene.get_button_rect("pause") is not None

        # 模拟悬停状态
        margin = scene.PAUSE_BUTTON_MARGIN
        size = scene.PAUSE_BUTTON_SIZE
        center_x = margin + size // 2
        center_y = margin + size // 2
        motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (center_x, center_y)}
        )
        scene.handle_events(motion_event)
        assert scene.is_button_hovered("pause") is True

        # enter() 应清除悬停并重新初始化布局
        scene.enter(difficulty='medium')
        assert scene.get_button_rect("pause") is not None  # 布局已重新初始化
        assert scene.get_hovered_button() is None  # 悬停已清除

    def test_pause_button_constants(self):
        from airwar.scenes.game_scene import GameScene
        assert GameScene.PAUSE_BUTTON_SIZE == 30
        assert GameScene.PAUSE_BUTTON_MARGIN == 10
        assert GameScene.PAUSE_BAR_WIDTH == 4
        assert GameScene.PAUSE_BAR_HEIGHT == 14
        assert GameScene.PAUSE_BAR_GAP == 4


class TestGameScenePauseButtonRendering:
    """测试暂停按钮的渲染输出"""

    def setup_method(self):
        pygame.init()

    def teardown_method(self):
        pygame.quit()

    def test_render_pause_button_does_not_crash(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')
        surface = pygame.Surface((800, 600))
        scene.render(surface)

    def test_render_pause_button_with_hover_does_not_crash(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        scene.enter(difficulty='medium')

        margin = scene.PAUSE_BUTTON_MARGIN
        size = scene.PAUSE_BUTTON_SIZE
        center_x = margin + size // 2
        center_y = margin + size // 2

        motion_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {'pos': (center_x, center_y)}
        )
        scene.handle_events(motion_event)

        surface = pygame.Surface((800, 600))
        scene.render(surface)

    def test_render_without_game_controller_does_not_crash(self):
        from airwar.scenes.game_scene import GameScene
        scene = GameScene()
        surface = pygame.Surface((800, 600))
        scene._render_pause_button(surface)
