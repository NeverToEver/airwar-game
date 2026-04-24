DIFFICULTY_CONFIGS = {
    'easy': {
        'growth_rate': 0.5,
        'base_multiplier': 0.8,
        'max_multiplier': 3.0,
        'speed_bonus': 0.1,
        'fire_rate_bonus': 0.15,
        'aggression_bonus': 0.1,
    },
    'medium': {
        'growth_rate': 1.0,
        'base_multiplier': 1.0,
        'max_multiplier': 5.0,
        'speed_bonus': 0.2,
        'fire_rate_bonus': 0.25,
        'aggression_bonus': 0.2,
    },
    'hard': {
        'growth_rate': 1.5,
        'base_multiplier': 1.2,
        'max_multiplier': 8.0,
        'speed_bonus': 0.35,
        'fire_rate_bonus': 0.4,
        'aggression_bonus': 0.35,
    },
}

MOVEMENT_PATTERNS = {
    1: ['straight'],
    2: ['straight', 'sine'],
    3: ['straight', 'sine', 'zigzag'],
    4: ['straight', 'sine', 'zigzag', 'hover'],
    5: ['straight', 'sine', 'zigzag', 'hover', 'spiral'],
}

BASE_ENEMY_PARAMS = {
    'speed': 2.0,
    'fire_rate': 150,
    'aggression': 0.5,
    'spawn_rate': 30,
}
