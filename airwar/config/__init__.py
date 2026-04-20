from .settings import *
from .game_config import GameConfig, get_screen_width, get_screen_height, set_screen_size

__all__ = [
    'SCREEN_WIDTH', 'SCREEN_HEIGHT', 'FPS',
    'get_screen_width', 'get_screen_height', 'set_screen_size',
    'GameConfig',
    'HEALTH_REGEN', 'DIFFICULTY_SETTINGS',
    'PLAYER_SPEED', 'BULLET_SPEED', 'ENEMY_SPEED',
    'PLAYER_FIRE_RATE', 'ENEMY_SPAWN_RATE',
    'ENEMY_HITBOX_SIZE', 'ENEMY_HITBOX_PADDING',
    'WHITE', 'BLACK', 'RED', 'GREEN', 'BLUE',
    'ASSETS_PATH', 'IMAGES_PATH', 'SOUNDS_PATH',
    'EXPLOSION_RADIUS',
]
