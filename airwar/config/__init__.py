"""Config package — game settings, design tokens, and difficulty configuration."""
from .settings import *
from .game_config import GameConfig, get_screen_width, get_screen_height, set_screen_size
from .difficulty_config import DIFFICULTY_CONFIGS, MOVEMENT_PATTERNS, BASE_ENEMY_PARAMS
from .tutorial import TUTORIAL_PAGES
from .design_tokens import get_design_tokens, get_colors

__all__ = [
    'SCREEN_WIDTH', 'SCREEN_HEIGHT', 'FPS',
    'get_screen_width', 'get_screen_height', 'set_screen_size',
    'GameConfig',
    'HEALTH_REGEN', 'DIFFICULTY_SETTINGS', 'DIFFICULTY_CONFIGS',
    'MOVEMENT_PATTERNS', 'BASE_ENEMY_PARAMS',
    'ENEMY_HITBOX_SIZE', 'ENEMY_HITBOX_PADDING',
    'ENEMY_VISUAL_SCALE', 'ENEMY_COLLISION_SCALE',
    'HITBOX_INDICATOR_PADDING', 'HITBOX_INDICATOR_ALPHA_MIN', 'HITBOX_INDICATOR_ALPHA_MAX',
    'HITBOX_INDICATOR_FREQUENCY',
    'RIPPLE_FADE_SPEED', 'BOOST_CONFIG',
    'VALID_DIFFICULTIES',
    'TUTORIAL_PAGES',
    'get_design_tokens', 'get_colors',
]
