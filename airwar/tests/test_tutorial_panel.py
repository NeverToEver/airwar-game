"""
Test module for TutorialPanel component.

This module contains unit tests for the TutorialPanel class.
Following the F.I.R.S.T. principles: Fast, Independent, Repeatable, Self-Validating, Timely.
"""

import pytest
from airwar.components.tutorial import TutorialPanel
from airwar.config.tutorial import PanelConfig


class TestTutorialPanel:
    """Test suite for TutorialPanel class."""

    def test_initialization(self):
        """Test that panel initializes correctly."""
        panel = TutorialPanel()
        assert panel.get_config() is not None
        assert isinstance(panel.get_config(), PanelConfig)

    def test_calculate_layout_centered(self):
        """Test that panel is centered on screen."""
        panel = TutorialPanel()
        screen_width = 1280
        screen_height = 720
        
        layout = panel.calculate_layout(screen_width, screen_height)
        
        assert layout['width'] > 0
        assert layout['height'] > 0
        assert layout['x'] >= 0
        assert layout['y'] >= 0
        assert layout['x'] + layout['width'] <= screen_width
        assert layout['y'] + layout['height'] <= screen_height

    def test_calculate_layout_different_sizes(self):
        """Test layout calculation for different screen sizes."""
        panel = TutorialPanel()
        sizes = [
            (800, 600),
            (1280, 720),
            (1920, 1080),
            (640, 480),
        ]
        
        for width, height in sizes:
            layout = panel.calculate_layout(width, height)
            assert layout['x'] + layout['width'] <= width
            assert layout['y'] + layout['height'] <= height

    def test_get_content_area(self):
        """Test content area calculation."""
        panel = TutorialPanel()
        layout = panel.calculate_layout(1280, 720)
        
        content = panel.get_content_area(layout)
        
        assert content['x'] >= layout['x']
        assert content['y'] >= layout['y']
        assert content['width'] < layout['width']
        assert content['height'] < layout['height']

    def test_get_content_area_with_none_layout(self):
        """Test that get_content_area handles None layout."""
        panel = TutorialPanel()
        content = panel.get_content_area(None)
        assert content is None

    def test_get_navigation_area(self):
        """Test navigation area calculation."""
        panel = TutorialPanel()
        layout = panel.calculate_layout(1280, 720)
        
        nav_area = panel.get_navigation_area(layout)
        
        assert nav_area['x'] == layout['x']
        assert nav_area['width'] == layout['width']
        assert nav_area['y'] < layout['y'] + layout['height']
        assert nav_area['y'] + nav_area['height'] <= layout['y'] + layout['height']

    def test_get_progress_area(self):
        """Test progress area calculation."""
        panel = TutorialPanel()
        layout = panel.calculate_layout(1280, 720)
        
        progress_area = panel.get_progress_area(layout)
        
        assert progress_area['x'] == layout['x']
        assert progress_area['width'] == layout['width']

    def test_reset(self):
        """Test that reset clears cached layout."""
        panel = TutorialPanel()
        panel.calculate_layout(1280, 720)
        assert panel.get_current_layout() is not None
        
        panel.reset()
        assert panel.get_current_layout() is None

    def test_get_current_layout_before_calculation(self):
        """Test that get_current_layout returns None before calculation."""
        panel = TutorialPanel()
        assert panel.get_current_layout() is None

    def test_layout_consistency(self):
        """Test that repeated calculations return consistent results."""
        panel = TutorialPanel()
        layout1 = panel.calculate_layout(1280, 720)
        layout2 = panel.calculate_layout(1280, 720)
        
        assert layout1 == layout2

    def test_layout_scales_proportionally(self):
        """Test that layout scales proportionally with screen size."""
        panel = TutorialPanel()
        layout1 = panel.calculate_layout(1280, 720)
        layout2 = panel.calculate_layout(2560, 1440)
        
        ratio1 = layout1['width'] / layout1['height']
        ratio2 = layout2['width'] / layout2['height']
        assert abs(ratio1 - ratio2) < 0.01
