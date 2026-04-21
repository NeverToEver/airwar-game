"""
Tutorial System Configuration Module

This module contains all configuration constants for the tutorial system.
Following the design principles of separation of concerns and single responsibility.
"""

from dataclasses import dataclass
from typing import Tuple, List, Dict


@dataclass
class PanelConfig:
    """Panel layout configuration"""
    WIDTH: int = 700
    HEIGHT: int = 600
    BORDER_RADIUS: int = 15
    PADDING: int = 30
    BORDER_WIDTH: int = 2


@dataclass
class ButtonConfig:
    """Button styling configuration"""
    WIDTH: int = 180
    HEIGHT: int = 50
    BORDER_RADIUS: int = 10
    SPACING: int = 20


@dataclass
class ProgressIndicatorConfig:
    """Progress indicator configuration"""
    WIDTH: int = 12
    HEIGHT: int = 12
    SPACING: int = 8


@dataclass
class ContentCardConfig:
    """Content card styling configuration"""
    PADDING: int = 20
    SPACING: int = 15
    BORDER_RADIUS: int = 10


@dataclass
class KeyBoxConfig:
    """Key display box configuration"""
    WIDTH: int = 120
    HEIGHT: int = 40
    BORDER_RADIUS: int = 6


@dataclass
class AnimationConfig:
    """Animation timing configuration"""
    SPEED: float = 0.05
    TRANSITION_DURATION: int = 200
    GLOW_PULSE_SPEED: float = 0.03
    STAR_TWINKLE_SPEED: float = 0.05


TUTORIAL_COLORS = {
    'background': (8, 8, 25),
    'background_gradient': (15, 15, 50),
    'panel_background': (15, 20, 40),
    'panel_border': (50, 80, 140),
    'panel_border_highlight': (100, 150, 200),
    'title': (255, 255, 255),
    'title_glow': (100, 200, 255),
    'section_title': (100, 200, 255),
    'key_highlight': (0, 255, 150),
    'description': (200, 210, 240),
    'button_normal': (25, 50, 90),
    'button_hover': (35, 70, 120),
    'button_disabled': (40, 40, 60),
    'progress_active': (0, 200, 255),
    'progress_inactive': (50, 50, 80),
    'particle': (100, 180, 255),
    'hint': (70, 70, 110),
}


TUTORIAL_FONTS = {
    'title': {'size': 72, 'style': 'bold'},
    'section': {'size': 36, 'style': 'bold'},
    'key': {'size': 28, 'style': 'normal'},
    'description': {'size': 26, 'style': 'normal'},
    'hint': {'size': 22, 'style': 'normal'},
    'button': {'size': 32, 'style': 'bold'},
}


TUTORIAL_STEPS: List[Dict] = [
    {
        'id': 'movement',
        'title': 'Fighter Controls',
        'content': [
            {'key': 'W', 'description': 'Move Up'},
            {'key': 'S', 'description': 'Move Down'},
            {'key': 'A', 'description': 'Move Left'},
            {'key': 'D', 'description': 'Move Right'},
            {'key': 'SPACE', 'description': 'Fire Weapon (Auto-fire)'},
        ],
    },
    {
        'id': 'mother_ship',
        'title': 'Mother Ship System',
        'content': [
            {'key': 'H (Hold)', 'description': 'Summon/Dock Mother Ship'},
            {'key': 'H (Hold)', 'description': 'Launch from Mother Ship'},
            {'key': '1-4', 'description': 'Select Power-up Effect'},
        ],
        'note': 'Choose buffs to enhance your fighter inside the Mother Ship',
    },
    {
        'id': 'pause',
        'title': 'Game Controls',
        'content': [
            {'key': 'ESC', 'description': 'Pause Game'},
            {'key': 'K (Hold 3s)', 'description': 'Abandon Current Game'},
        ],
    },
    {
        'id': 'complete',
        'title': 'Ready to Begin',
        'content': [],
        'is_complete': True,
    },
]
