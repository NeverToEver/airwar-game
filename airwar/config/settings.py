from airwar.config.game_config import GameConfig, get_screen_width, get_screen_height, set_screen_size

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
FPS = 60

HEALTH_REGEN = {
    'easy': {'delay': 180, 'rate': 3, 'interval': 45},
    'medium': {'delay': 240, 'rate': 2, 'interval': 60},
    'hard': {'delay': 300, 'rate': 1, 'interval': 90},
}

def get_adaptive_screen_size():
    return GameConfig.get_instance().get_adaptive_screen_size()

PLAYER_SPEED = 5
BULLET_SPEED = 10
ENEMY_SPEED = 3

PLAYER_FIRE_RATE = 8

ENEMY_SPAWN_RATE = 30

ENEMY_HITBOX_SIZE = 50
ENEMY_HITBOX_PADDING = 8

ENEMY_VISUAL_SCALE = 0.76
ENEMY_COLLISION_SCALE = 0.83

HITBOX_INDICATOR_PADDING = 10
HITBOX_INDICATOR_FREQUENCY = 0.4
HITBOX_INDICATOR_ALPHA_MIN = 50
HITBOX_INDICATOR_ALPHA_MAX = 255

RIPPLE_ALPHA_FACTOR = 0.6
RIPPLE_FADE_SPEED = 6

DIFFICULTY_SETTINGS = {
    'easy': {
        'enemy_health': 300,
        'bullet_damage': 100,
        'enemy_speed': 2.5,
        'spawn_rate': 40,
        'max_delta': 1500,
        'difficulty_multiplier': 0.8,
    },
    'medium': {
        'enemy_health': 200,
        'bullet_damage': 50,
        'enemy_speed': 3,
        'spawn_rate': 30,
        'max_delta': 2000,
        'difficulty_multiplier': 1.0,
    },
    'hard': {
        'enemy_health': 170,
        'bullet_damage': 34,
        'enemy_speed': 3.5,
        'spawn_rate': 25,
        'max_delta': 3000,
        'difficulty_multiplier': 1.5,
    },
}

VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

ENEMY_BULLET_DAMAGE = {
    'spread': 8,
    'laser': 25,
    'single': 15,
}

BOSS_BULLET_DAMAGE_BASE = 10
BOSS_AIM_BULLET_DAMAGE_BASE = 15
BOSS_WAVE_BULLET_DAMAGE = 8

BOSS_SPREAD_SPEED = 5.0
BOSS_AIM_SPEED = 7.0
BOSS_WAVE_SPEED = 4.0

BOSS_SPREAD_ANGLE_RANGE = 180
BOSS_WAVE_ANGLE_INTERVAL = 22.5
BOSS_SIDE_ANGLE_RANGE = 45
BOSS_SIDE_ANGLE_OFFSET = 22.5

BOSS_ATTACK_DISTANCE = 500
BOSS_BULLET_OFFSET_X = 30

BOSS_FIRE_RATE_BASE = 60
BOSS_PHASE_INTERVAL = 300
BOSS_SPREAD_BULLET_COUNT_BASE = 5

EXPLOSION_RADIUS = 50

ASSETS_PATH = "airwar/assets"
IMAGES_PATH = f"{ASSETS_PATH}/images"
SOUNDS_PATH = f"{ASSETS_PATH}/sounds"
