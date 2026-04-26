"""Difficulty strategy implementations — Easy, Medium, Hard progression."""
from abc import ABC
import logging


class DifficultyStrategy(ABC):
    """Abstract base class for difficulty scaling strategies."""
    GROWTH_RATE: float = 1.0
    BASE_MULTIPLIER: float = 1.0
    MAX_MULTIPLIER: float = 5.0
    SPEED_BONUS: float = 0.2
    FIRE_RATE_BONUS: float = 0.25
    AGGRESSION_BONUS: float = 0.2

    @property
    def growth_rate(self) -> float:
        return self.GROWTH_RATE

    @property
    def base_multiplier(self) -> float:
        return self.BASE_MULTIPLIER

    @property
    def max_multiplier(self) -> float:
        return self.MAX_MULTIPLIER

    @property
    def speed_bonus(self) -> float:
        return self.SPEED_BONUS

    @property
    def fire_rate_bonus(self) -> float:
        return self.FIRE_RATE_BONUS

    @property
    def aggression_bonus(self) -> float:
        return self.AGGRESSION_BONUS


class EasyStrategy(DifficultyStrategy):
    """Easy difficulty strategy — slow scaling, low caps."""
    GROWTH_RATE = 0.5
    BASE_MULTIPLIER = 0.8
    MAX_MULTIPLIER = 3.0
    SPEED_BONUS = 0.1
    FIRE_RATE_BONUS = 0.15
    AGGRESSION_BONUS = 0.1


class MediumStrategy(DifficultyStrategy):
    """Medium difficulty strategy — balanced scaling and caps."""
    GROWTH_RATE = 1.0
    BASE_MULTIPLIER = 1.0
    MAX_MULTIPLIER = 5.0
    SPEED_BONUS = 0.2
    FIRE_RATE_BONUS = 0.25
    AGGRESSION_BONUS = 0.2


class HardStrategy(DifficultyStrategy):
    """Hard difficulty strategy — aggressive scaling, high caps."""
    GROWTH_RATE = 1.5
    BASE_MULTIPLIER = 1.2
    MAX_MULTIPLIER = 8.0
    SPEED_BONUS = 0.35
    FIRE_RATE_BONUS = 0.4
    AGGRESSION_BONUS = 0.35


class DifficultyStrategyFactory:
    """Factory for creating DifficultyStrategy instances by difficulty name."""
    _STRATEGIES = {
        'easy': EasyStrategy,
        'medium': MediumStrategy,
        'hard': HardStrategy,
    }

    @classmethod
    def create(cls, difficulty: str) -> DifficultyStrategy:
        if difficulty not in cls._STRATEGIES:
            logging.warning(f"Invalid difficulty '{difficulty}', defaulting to 'medium'")
            difficulty = 'medium'

        return cls._STRATEGIES[difficulty]()
