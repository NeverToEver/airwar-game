"""
Tutorial Panel Component

This module implements the TutorialPanel class, which is responsible for
managing the layout and dimensions of the tutorial interface panel.
Following the Single Responsibility Principle - it only handles layout calculations.
"""

from typing import Tuple, Dict
from airwar.configs.tutorial import PanelConfig
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
        
        panel_width = int(self._config.WIDTH * scale)
        panel_height = int(self._config.HEIGHT * scale)
        
        self._layout = {
            'x': (screen_width - panel_width) // 2,
            'y': (screen_height - panel_height) // 2,
            'width': panel_width,
            'height': panel_height,
        }
        
        return self._layout

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
        padding = int(self._config.PADDING * scale)
        
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
