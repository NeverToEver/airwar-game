"""Config package — game settings, design tokens, and difficulty configuration."""
from .settings import *
from .game_config import GameConfig, get_screen_width, get_screen_height, set_screen_size
from .difficulty_config import DIFFICULTY_CONFIGS, MOVEMENT_PATTERNS, BASE_ENEMY_PARAMS
from airwar.config.tutorial import TUTORIAL_PAGES
from airwar.config.design_tokens import get_design_tokens, get_colors

__all__ = [
    'SCREEN_WIDTH', 'SCREEN_HEIGHT', 'FPS',
    'get_screen_width', 'get_screen_height', 'set_screen_size',
    'GameConfig',
    'HEALTH_REGEN', 'DIFFICULTY_SETTINGS', 'DIFFICULTY_CONFIGS',
    'MOVEMENT_PATTERNS', 'BASE_ENEMY_PARAMS',
    'BULLET_SPEED',
    'ENEMY_HITBOX_SIZE', 'ENEMY_HITBOX_PADDING',
    'RED', 'GREEN',
    'EXPLOSION_RADIUS',
    'VALID_DIFFICULTIES',
    'TUTORIAL_PAGES',
    'get_design_tokens', 'get_colors',
]
