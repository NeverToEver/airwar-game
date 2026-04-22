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
    WELCOME = 'welcome'
    KEY_LIST = 'key_list'


@dataclass
class PanelConfig:
    WIDTH: int = 400
    HEIGHT: int = 460
    BORDER_RADIUS: int = 15
    PADDING: int = 20


@dataclass
class ButtonConfig:
    WIDTH: int = 160
    HEIGHT: int = 48
    BORDER_RADIUS: int = 10
    SPACING: int = 15


@dataclass
class ContentCardConfig:
    PADDING: int = 20
    SPACING: int = 12
    BORDER_RADIUS: int = 10


TUTORIAL_STEPS: List[Dict] = [
    {
        'id': 'welcome',
        'type': 'welcome',
        'title': 'Welcome Commander',
        'content': [
            {'text': 'Welcome to Air War training program'},
            {'text': 'Complete this tutorial to master basic operations'},
            {'text': 'Use arrow keys or mouse to navigate'},
        ],
    },
    {
        'id': 'movement',
        'type': 'key_list',
        'title': 'Fighter Controls',
        'content': [
            {'key': 'W / UP', 'description': 'Move Up'},
            {'key': 'S / DOWN', 'description': 'Move Down'},
            {'key': 'A / LEFT', 'description': 'Move Left'},
            {'key': 'D / RIGHT', 'description': 'Move Right'},
            {'key': 'SPACE', 'description': 'Fire Weapon'},
        ],
        'note': 'Auto-fire enabled: hold SPACE for continuous fire',
    },
    {
        'id': 'buff',
        'type': 'key_list',
        'title': 'Buff System',
        'content': [
            {'key': 'H (Hold)', 'description': 'Dock with Mother Ship'},
            {'key': '1-4', 'description': 'Select power-up to purchase'},
            {'key': 'Mouse Click', 'description': 'Confirm selection'},
        ],
        'note': 'Buffs last until next milestone or game over',
    },
    {
        'id': 'mechanics',
        'type': 'key_list',
        'title': 'Game Mechanics',
        'content': [
            {'key': 'ESC', 'description': 'Pause game'},
            {'key': 'L', 'description': 'Toggle HUD panel'},
            {'key': 'K (Hold 3s)', 'description': 'Surrender (when docked)'},
            {'key': 'Milestones', 'description': 'Score targets to unlock buffs'},
            {'key': 'Difficulty', 'description': 'Increases with boss kills'},
        ],
    },
    {
        'id': 'ready',
        'type': 'key_list',
        'title': 'Ready to Begin',
        'content': [],
        'is_complete': True,
    },
]
