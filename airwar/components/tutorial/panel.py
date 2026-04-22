"""
Tutorial Panel Component

This module implements the TutorialPanel class, which is responsible for
managing the layout and dimensions of the tutorial interface panel.
Following the Single Responsibility Principle - it only handles layout calculations.
Visual style follows DesignTokens for consistency with other scenes.
"""

from typing import Tuple, Dict
from airwar.config.tutorial import PanelConfig, StepType
from airwar.utils.responsive import ResponsiveHelper


class TutorialPanel:
    """
    Tutorial panel component responsible for layout calculations.

    This class follows the Single Responsibility Principle by only handling
    panel layout and dimension calculations. It does not handle rendering
    or content display.
    """

    def __init__(self):
        self._config = PanelConfig()
        self._background_cache = None
        self._layout = None

        self._base_panel_width = 400
        self._base_panel_height = 460
        self._base_option_height = 70
        self._base_option_gap = 12
        self._base_button_width = 160
        self._base_button_height = 48

    def calculate_layout(self, screen_width: int, screen_height: int) -> Dict[str, int]:
        """
        Calculate the panel layout based on screen dimensions.

        Args:
            screen_width: Width of the screen in pixels
            screen_height: Height of the screen in pixels

        Returns:
            Dictionary containing panel position and dimensions
        """
        scale = ResponsiveHelper.get_scale_factor(screen_width, screen_height)

        panel_width = int(self._base_panel_width * scale)
        panel_height = int(self._base_panel_height * scale)

        self._layout = {
            'x': (screen_width - panel_width) // 2,
            'y': (screen_height - panel_height) // 2,
            'width': panel_width,
            'height': panel_height,
        }

        return self._layout

    def get_button_rect(
        self,
        screen_width: int,
        screen_height: int,
        button_type: str
    ) -> Tuple[int, int, int, int]:
        """
        Get the button rectangle for click detection.

        Args:
            screen_width: Width of the screen
            screen_height: Height of the screen
            button_type: 'prev', 'next', or 'exit'

        Returns:
            Tuple of (x, y, width, height)
        """
        scale = ResponsiveHelper.get_scale_factor(screen_width, screen_height)

        panel_width = int(self._base_panel_width * scale)
        panel_height = int(self._base_panel_height * scale)
        panel_x = (screen_width - panel_width) // 2
        panel_y = (screen_height - panel_height) // 2

        button_width = int(self._base_button_width * scale)
        button_height = int(self._base_button_height * scale)
        button_y = panel_y + panel_height - int(80 * scale)

        if button_type == 'prev':
            button_x = screen_width // 2 - button_width - int(15 * scale)
        elif button_type == 'exit':
            button_x = screen_width // 2 - button_width // 2
        else:
            button_x = screen_width // 2 + int(15 * scale)

        return (button_x, button_y, button_width, button_height)

    def get_content_area(self, layout: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate the content area within the panel.

        Args:
            layout: Panel layout dictionary

        Returns:
            Dictionary containing content area dimensions
        """
        if layout is None:
            return None

        scale = ResponsiveHelper.get_scale_factor(layout['width'], layout['height'])
        padding = int(20 * scale)

        return {
            'x': layout['x'] + padding,
            'y': layout['y'] + padding,
            'width': layout['width'] - padding * 2,
            'height': layout['height'] - padding * 2,
        }

    def get_navigation_area(self, layout: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate the navigation button area at the bottom of the panel.

        Args:
            layout: Panel layout dictionary

        Returns:
            Dictionary containing navigation area dimensions
        """
        if layout is None:
            return None

        scale = ResponsiveHelper.get_scale_factor(layout['width'], layout['height'])
        bottom_padding = int(30 * scale)
        nav_height = int(60 * scale)

        return {
            'x': layout['x'],
            'y': layout['y'] + layout['height'] - bottom_padding - nav_height,
            'width': layout['width'],
            'height': nav_height,
        }

    def get_progress_area(self, layout: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate the progress indicator area at the top of the content.

        Args:
            layout: Panel layout dictionary

        Returns:
            Dictionary containing progress area dimensions
        """
        if layout is None:
            return None

        return {
            'x': layout['x'],
            'y': layout['y'] + 50,
            'width': layout['width'],
            'height': 30,
        }

    def get_current_layout(self) -> Dict[str, int]:
        """
        Get the currently calculated layout.

        Returns:
            Dictionary containing panel position and dimensions, or None if not yet calculated
        """
        return self._layout

    def reset(self) -> None:
        """
        Reset the panel state and clear cached data.
        """
        self._layout = None
        self._background_cache = None

    def get_config(self) -> PanelConfig:
        """
        Get the panel configuration.

        Returns:
            PanelConfig instance
        """
        return self._config

    def calculate_content_layout(self, step_type: str, item_count: int, layout: Dict[str, int]) -> Dict[str, int]:
        """
        Calculate layout for step content based on step type.

        Args:
            step_type: Type of step ('welcome', 'key_list', etc.)
            item_count: Number of content items
            layout: Current panel layout

        Returns:
            Dictionary containing content layout
        """
        scale = ResponsiveHelper.get_scale_factor(layout['width'], layout['height'])
        padding = int(20 * scale)

        title_area_height = int(120 * scale)
        nav_area_height = int(130 * scale)

        available_height = layout['height'] - padding * 2 - title_area_height - nav_area_height
        available_width = layout['width'] - padding * 2

        start_y = layout['y'] + padding + title_area_height

        option_height = int(70 * scale)
        option_gap = int(12 * scale)
        max_items = (available_height + option_gap) // (option_height + option_gap)
        visible_items = min(item_count, max_items)

        return {
            'x': layout['x'] + padding,
            'y': start_y,
            'width': available_width,
            'height': available_height,
            'item_gap': option_gap,
            'item_count': item_count,
            'visible_items': visible_items,
            'option_height': option_height,
        }
