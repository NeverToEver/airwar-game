"""Movement strategies for Enemy entities.

Extracts movement pattern logic into strategy classes to improve maintainability
and reduce complexity in Enemy.update(). Each strategy handles one movement type.
"""
from abc import ABC, abstractmethod
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.enemy import Enemy


class MovementStrategy(ABC):
    """Abstract base class for enemy movement strategies."""

    @abstractmethod
    def update(self, enemy: 'Enemy') -> None:
        """Update enemy position based on movement pattern.

        Args:
            enemy: The enemy entity to move.
        """
        pass


class StraightMovement(MovementStrategy):
    """Straight movement with small vertical oscillation."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.rect.x = enemy._active_position_x
        enemy.rect.y = enemy._active_position_y + math.sin(enemy._lifetime * 0.05) * 15
        enemy._sync_rects()


class SineMovement(MovementStrategy):
    """Sine wave movement pattern."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.move_timer += 1
        enemy.rect.x = enemy._active_position_x + math.sin(
            enemy.move_timer * enemy.move_frequency + enemy.move_offset
        ) * 80
        enemy.rect.y = enemy._active_position_y + math.sin(
            enemy.move_timer * enemy.move_frequency * 0.5
        ) * 50
        enemy._sync_rects()


class ZigzagMovement(MovementStrategy):
    """Zigzag movement with direction changes at intervals."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.zigzag_timer += 1
        if enemy.zigzag_timer >= enemy.zigzag_interval:
            enemy.zigzag_timer = 0
            enemy.direction *= -1
        new_x = enemy.rect.x + enemy.direction * enemy.zigzag_speed
        enemy.rect.x = max(
            enemy._active_position_x - 80,
            min(new_x, enemy._active_position_x + 80)
        )
        enemy.rect.y = enemy._active_position_y + math.sin(enemy._lifetime * 0.1) * 25
        enemy._sync_rects()


class DiveMovement(MovementStrategy):
    """Dive movement with wave-based patterns."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.dive_timer += 1
        wave = math.sin(enemy.dive_timer * 0.05) * 24
        enemy.rect.x = enemy._active_position_x + wave
        enemy.rect.y = enemy._active_position_y + math.sin(enemy.dive_timer * 0.03) * 15
        enemy._sync_rects()


class HoverMovement(MovementStrategy):
    """Hover movement with smooth sin-based oscillation."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.hover_timer += 0.08
        enemy.rect.x = enemy._active_position_x + math.sin(enemy.hover_timer) * 80
        enemy.rect.y = enemy._active_position_y + math.sin(enemy.hover_timer * 0.7) * 25
        enemy._sync_rects()


class SpiralMovement(MovementStrategy):
    """Spiral movement pattern."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.spiral_timer += 1
        spiral_x = math.cos(enemy.spiral_timer * enemy.spiral_frequency) * 40
        spiral_y = math.sin(enemy.spiral_timer * enemy.spiral_frequency * 2) * 15
        enemy.rect.x = enemy._active_position_x + spiral_x
        enemy.rect.y = enemy._active_position_y + spiral_y
        enemy._sync_rects()


class NoiseMovement(MovementStrategy):
    """Organic noise-based movement with smooth transitions."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.noise_timer += enemy.noise_speed
        noise_x = _smooth_noise(enemy.noise_timer * enemy.noise_scale_x, enemy.noise_seed) * enemy.noise_amplitude_x
        noise_y = _smooth_noise(enemy.noise_timer * enemy.noise_scale_y, enemy.noise_seed + 500) * enemy.noise_amplitude_y

        new_x = enemy._active_position_x + noise_x * 80
        new_y = enemy._active_position_y + noise_y * 50

        max_delta = 6
        dx = new_x - enemy.rect.x
        dy = new_y - enemy.rect.y
        if abs(dx) > max_delta:
            new_x = enemy.rect.x + (max_delta if dx > 0 else -max_delta)
        if abs(dy) > max_delta:
            new_y = enemy.rect.y + (max_delta if dy > 0 else -max_delta)

        enemy.rect.x = new_x
        enemy.rect.y = new_y
        enemy._sync_rects()


class AggressiveMovement(MovementStrategy):
    """Aggressive noise movement with downward drift toward player."""

    def update(self, enemy: 'Enemy') -> None:
        enemy.agg_timer += enemy.agg_speed
        noise_x = _smooth_noise(enemy.agg_timer * enemy.agg_scale_x, enemy.agg_seed) * enemy.agg_amplitude_x
        noise_y = _smooth_noise(enemy.agg_timer * enemy.agg_scale_y, enemy.agg_seed + 500) * enemy.agg_amplitude_y
        noise_y = noise_y + 0.15

        agg_range_x = 96
        agg_range_y = 60
        new_x = enemy._active_position_x + noise_x * agg_range_x
        new_y = enemy._active_position_y + noise_y * agg_range_y

        max_delta = 8
        dx = new_x - enemy.rect.x
        dy = new_y - enemy.rect.y
        if abs(dx) > max_delta:
            new_x = enemy.rect.x + (max_delta if dx > 0 else -max_delta)
        if abs(dy) > max_delta:
            new_y = enemy.rect.y + (max_delta if dy > 0 else -max_delta)

        enemy.rect.x = new_x
        enemy.rect.y = new_y
        enemy._sync_rects()


def _smooth_noise(x: float, seed: int) -> float:
    """Smooth continuous noise function using cosine interpolation.

    Returns value in range [-1, 1] with continuous derivatives.
    """
    int_x = int(x)
    frac_x = x - int_x

    v1 = math.sin(int_x * 1.0 + seed * 0.1) * 0.5
    v2 = math.sin(int_x * 2.3 + seed * 0.2) * 0.3
    v3 = math.sin(int_x * 4.7 + seed * 0.3) * 0.2
    v4 = math.sin((int_x + 1) * 1.0 + seed * 0.1) * 0.5
    v5 = math.sin((int_x + 1) * 2.3 + seed * 0.2) * 0.3
    v6 = math.sin((int_x + 1) * 4.7 + seed * 0.3) * 0.2

    t = 0.5 - 0.5 * math.cos(frac_x * math.pi)
    val0 = v1 + v2 + v3
    val1 = v4 + v5 + v6

    result = val0 + (val1 - val0) * t
    return max(-1.0, min(1.0, result * 1.2))


# Factory to get strategy by movement type name
_STRATEGY_MAP = {
    "straight": StraightMovement,
    "sine": SineMovement,
    "zigzag": ZigzagMovement,
    "dive": DiveMovement,
    "hover": HoverMovement,
    "spiral": SpiralMovement,
    "noise": NoiseMovement,
    "aggressive": AggressiveMovement,
}


def get_movement_strategy(move_type: str) -> MovementStrategy:
    """Get movement strategy instance for the given movement type.

    Args:
        move_type: Movement type string ('straight', 'sine', 'zigzag', etc.)

    Returns:
        MovementStrategy instance for the given type.
    """
    strategy_class = _STRATEGY_MAP.get(move_type, StraightMovement)
    return strategy_class()
