import random
from typing import Dict

from airwar.config.difficulty_config import MOVEMENT_PATTERNS


class MovementPatternGenerator:
    DEFAULT_SPEED_MULTIPLIER: float = 1.0

    _ENHANCEMENT_COEFFICIENTS: Dict[str, Dict[str, float]] = {
        'straight': {
            'speed_multiplier': 0.3,
        },
        'sine': {
            'amplitude_multiplier': 0.2,
            'frequency_multiplier': 0.1,
        },
        'zigzag': {
            'speed_multiplier': 0.25,
            'direction_change_multiplier': 0.15,
        },
        'hover': {
            'hover_speed_multiplier': 0.3,
            'amplitude_multiplier': 0.2,
        },
        'dive': {
            'speed_multiplier': 0.35,
            'dive_trigger_multiplier': 0.1,
        },
        'spiral': {
            'spiral_speed_multiplier': 0.35,
            'spiral_tightness': 0.1,
        },
    }

    @classmethod
    def get_pattern(cls, complexity: int) -> str:
        complexity = max(1, min(complexity, len(MOVEMENT_PATTERNS)))
        available_patterns = MOVEMENT_PATTERNS.get(complexity, ['straight'])
        return random.choice(available_patterns)

    @classmethod
    def enhance_pattern(cls, pattern: str, difficulty: float) -> Dict:
        base_enhancement = difficulty - 1.0
        coefficients = cls._ENHANCEMENT_COEFFICIENTS.get(pattern, {})

        enhancements = {}
        for key, coeff in coefficients.items():
            enhancements[key] = 1.0 + base_enhancement * coeff

        if not enhancements:
            enhancements['speed_multiplier'] = cls.DEFAULT_SPEED_MULTIPLIER

        return enhancements
