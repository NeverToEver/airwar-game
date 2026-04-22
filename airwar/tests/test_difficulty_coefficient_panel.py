import pytest
import pygame
from unittest.mock import Mock, MagicMock
from airwar.game.systems.difficulty_manager import DifficultyManager
from airwar.ui.difficulty_coefficient_panel import DifficultyCoefficientPanel


class TestDifficultyCoefficientPanel:
    def setup_method(self):
        pygame.init()

    def teardown_method(self):
        pygame.quit()

    def test_panel_initialization(self):
        mock_manager = MagicMock()
        panel = DifficultyCoefficientPanel(mock_manager)
        assert panel is not None

    def test_panel_stores_initial_multiplier(self):
        mock_manager = MagicMock()
        mock_manager.initial_multiplier = 1.0
        mock_manager.get_current_multiplier.return_value = 1.0
        panel = DifficultyCoefficientPanel(mock_manager)
        assert panel._initial_multiplier == 1.0

    def test_render_does_not_raise(self):
        mock_manager = MagicMock()
        mock_manager.get_current_multiplier.return_value = 2.5
        mock_manager.initial_multiplier = 1.0
        mock_manager.MAX_MULTIPLIER_GLOBAL = 5.0

        panel = DifficultyCoefficientPanel(mock_manager)

        surface = pygame.Surface((800, 600))
        panel.render(surface)

    def test_get_color_for_difficulty_low(self):
        mock_manager = MagicMock()
        panel = DifficultyCoefficientPanel(mock_manager)

        assert panel._get_color_for_multiplier(1.5) == (100, 255, 100)
        assert panel._get_color_for_multiplier(1.9) == (100, 255, 100)

    def test_get_color_for_difficulty_medium(self):
        mock_manager = MagicMock()
        panel = DifficultyCoefficientPanel(mock_manager)

        assert panel._get_color_for_multiplier(2.0) == (255, 255, 100)
        assert panel._get_color_for_multiplier(3.9) == (255, 255, 100)

    def test_get_color_for_difficulty_high(self):
        mock_manager = MagicMock()
        panel = DifficultyCoefficientPanel(mock_manager)

        assert panel._get_color_for_multiplier(4.0) == (255, 150, 50)
        assert panel._get_color_for_multiplier(5.9) == (255, 150, 50)

    def test_get_color_for_difficulty_extreme(self):
        mock_manager = MagicMock()
        panel = DifficultyCoefficientPanel(mock_manager)

        assert panel._get_color_for_multiplier(6.0) == (255, 50, 50)
        assert panel._get_color_for_multiplier(10.0) == (255, 50, 50)

    def test_render_shows_current_and_initial(self):
        mock_manager = MagicMock()
        mock_manager.get_current_multiplier.return_value = 4.5
        mock_manager.initial_multiplier = 1.0
        mock_manager.MAX_MULTIPLIER_GLOBAL = 5.0

        panel = DifficultyCoefficientPanel(mock_manager)

        surface = pygame.Surface((800, 600))
        panel.render(surface)

    def test_render_at_left_center_position(self):
        mock_manager = MagicMock()
        mock_manager.get_current_multiplier.return_value = 3.0
        mock_manager.initial_multiplier = 1.0
        mock_manager.MAX_MULTIPLIER_GLOBAL = 5.0

        panel = DifficultyCoefficientPanel(mock_manager)

        surface = pygame.Surface((800, 600))
        panel.render(surface)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
