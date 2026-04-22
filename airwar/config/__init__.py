from .settings import *
from .game_config import GameConfig, get_screen_width, get_screen_height, set_screen_size
from .difficulty_config import DIFFICULTY_CONFIGS, MOVEMENT_PATTERNS, BASE_ENEMY_PARAMS
from airwar.configs.tutorial import TUTORIAL_COLORS, TUTORIAL_FONTS, TUTORIAL_STEPS

__all__ = [
    'SCREEN_WIDTH', 'SCREEN_HEIGHT', 'FPS',
    'get_screen_width', 'get_screen_height', 'set_screen_size',
    'GameConfig',
    'HEALTH_REGEN', 'DIFFICULTY_SETTINGS', 'DIFFICULTY_CONFIGS',
    'MOVEMENT_PATTERNS', 'BASE_ENEMY_PARAMS',
    'PLAYER_SPEED', 'BULLET_SPEED', 'ENEMY_SPEED',
    'PLAYER_FIRE_RATE', 'ENEMY_SPAWN_RATE',
    'ENEMY_HITBOX_SIZE', 'ENEMY_HITBOX_PADDING',
    'WHITE', 'BLACK', 'RED', 'GREEN', 'BLUE',
    'ASSETS_PATH', 'IMAGES_PATH', 'SOUNDS_PATH',
    'EXPLOSION_RADIUS',
    'VALID_DIFFICULTIES',
    'TUTORIAL_COLORS', 'TUTORIAL_FONTS', 'TUTORIAL_STEPS',
]
