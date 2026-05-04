"""Settings — global constants for dimensions, speeds, and rendering."""
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60

HEALTH_REGEN = {
    'easy': {'delay': 180, 'rate': 3, 'interval': 45},
    'medium': {'delay': 240, 'rate': 2, 'interval': 60},
    'hard': {'delay': 300, 'rate': 1, 'interval': 90},
}

BOOST_CONFIG = {
    'easy': {'max_boost': 300, 'recovery_rate': 1.2, 'speed_mult': 1.7,
             'recovery_delay': 90, 'recovery_ramp': 120},
    'medium': {'max_boost': 200, 'recovery_rate': 1.0, 'speed_mult': 1.7,
               'recovery_delay': 90, 'recovery_ramp': 120},
    'hard': {'max_boost': 120, 'recovery_rate': 0.8, 'speed_mult': 1.7,
             'recovery_delay': 90, 'recovery_ramp': 120},
}

ENEMY_HITBOX_SIZE = 50
ENEMY_HITBOX_PADDING = 8

ENEMY_VISUAL_SCALE = 0.76
ENEMY_COLLISION_SCALE = 0.94

HITBOX_INDICATOR_PADDING = 10
HITBOX_INDICATOR_FREQUENCY = 0.18
HITBOX_INDICATOR_ALPHA_MIN = 110
HITBOX_INDICATOR_ALPHA_MAX = 255

RIPPLE_FADE_SPEED = 6

DIFFICULTY_SETTINGS = {
    'easy': {
        'enemy_health': 300,
        'bullet_damage': 100,
        'enemy_speed': 2.5,
        'spawn_rate': 40,
        'max_delta': 6000,
        'difficulty_multiplier': 0.8,
        'spread_enemy_cap': 1,
    },
    'medium': {
        'enemy_health': 200,
        'bullet_damage': 50,
        'enemy_speed': 3,
        'spawn_rate': 30,
        'max_delta': 8000,
        'difficulty_multiplier': 1.0,
        'spread_enemy_cap': 2,
    },
    'hard': {
        'enemy_health': 170,
        'bullet_damage': 34,
        'enemy_speed': 3.5,
        'spawn_rate': 25,
        'max_delta': 12000,
        'difficulty_multiplier': 1.5,
        'spread_enemy_cap': 3,
    },
}

VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}
