SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
FPS = 60

_screen_width = SCREEN_WIDTH
_screen_height = SCREEN_HEIGHT

def get_screen_width():
    return _screen_width

def get_screen_height():
    return _screen_height

def set_screen_size(width: int, height: int) -> None:
    global _screen_width, _screen_height
    _screen_width = width
    _screen_height = height

HEALTH_REGEN = {
    'easy': {'delay': 180, 'rate': 3, 'interval': 45},
    'medium': {'delay': 240, 'rate': 2, 'interval': 60},
    'hard': {'delay': 300, 'rate': 1, 'interval': 90},
}

def get_adaptive_screen_size():
    import pygame
    info = pygame.display.Info()
    max_width = info.current_w - 40
    max_height = info.current_h - 80
    
    target_width = SCREEN_WIDTH
    target_height = SCREEN_HEIGHT
    
    if target_width > max_width:
        scale = max_width / target_width
        target_width = max_width
        target_height = int(target_height * scale)
    
    if target_height > max_height:
        scale = max_height / target_height
        target_height = max_height
        target_width = int(target_width * scale)
    
    return (target_width, target_height)

PLAYER_SPEED = 5
BULLET_SPEED = 10
ENEMY_SPEED = 3

PLAYER_FIRE_RATE = 8

ENEMY_SPAWN_RATE = 30

DIFFICULTY_SETTINGS = {
    'easy': {
        'enemy_health': 300,
        'bullet_damage': 100,
        'enemy_speed': 2.5,
        'spawn_rate': 40,
    },
    'medium': {
        'enemy_health': 200,
        'bullet_damage': 50,
        'enemy_speed': 3,
        'spawn_rate': 30,
    },
    'hard': {
        'enemy_health': 170,
        'bullet_damage': 34,
        'enemy_speed': 3.5,
        'spawn_rate': 25,
    },
}

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

ASSETS_PATH = "airwar/assets"
IMAGES_PATH = f"{ASSETS_PATH}/images"
SOUNDS_PATH = f"{ASSETS_PATH}/sounds"
