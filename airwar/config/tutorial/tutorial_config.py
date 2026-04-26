"""
Tutorial System Configuration Module

This module contains tutorial-specific configuration constants.
Visual styling is now handled by DesignTokens for consistency.
Only tutorial-specific logic configurations remain here.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, List, Dict


class StepType(Enum):
    """Tutorial step type enum — panel, button, or content card."""
    WELCOME = 'welcome'
    KEY_LIST = 'key_list'


@dataclass
class PanelConfig:
    """Tutorial panel config dataclass — position and size for a step panel."""
    WIDTH: int = 800
    HEIGHT: int = 700
    BORDER_RADIUS: int = 15
    PADDING: int = 20


@dataclass
class ButtonConfig:
    """Tutorial button config dataclass — label and action for a step button."""
    WIDTH: int = 200
    HEIGHT: int = 55
    BORDER_RADIUS: int = 10
    SPACING: int = 15


@dataclass
class ContentCardConfig:
    """Tutorial content card config dataclass — title and body for a step."""
    PADDING: int = 20
    SPACING: int = 12
    BORDER_RADIUS: int = 10


# Single-page tutorial content
TUTORIAL_CONTENT: Dict = {
    'title': 'TRAINING MANUAL',
    'subtitle': 'Air War Commander Training Program',
    'sections': [
        {
            'title': 'Movement',
            'icon': '-',
            'items': [
                {'key': 'W / UP', 'desc': 'Move Up'},
                {'key': 'S / DOWN', 'desc': 'Move Down'},
                {'key': 'A / LEFT', 'desc': 'Move Left'},
                {'key': 'D / RIGHT', 'desc': 'Move Right'},
                {'key': 'SPACE', 'desc': 'Fire (hold for auto-fire)'},
            ],
        },
        {
            'title': 'Special',
            'icon': '-',
            'items': [
                {'key': 'H (hold)', 'desc': 'Dock with Mother Ship to save'},
                {'key': 'K (hold 3s)', 'desc': 'Surrender (when docked)'},
            ],
        },
        {
            'title': 'Interface',
            'icon': '-',
            'items': [
                {'key': 'ESC', 'desc': 'Pause game'},
                {'key': 'L', 'desc': 'Toggle HUD panel'},
                {'key': '1-4', 'desc': 'Select power-up at milestone'},
            ],
        },
        {
            'title': 'Progression',
            'icon': '-',
            'items': [
                {'key': 'Milestones', 'desc': 'Score targets unlock buffs'},
                {'key': 'Boss Kills', 'desc': 'Increase difficulty'},
            ],
        },
    ],
}
