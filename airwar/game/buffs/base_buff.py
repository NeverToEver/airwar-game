"""Base buff classes — Buff and BuffResult for the buff system."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class BuffResult:
    """Buff result dataclass — computed value, duration, and effect description."""
    name: str
    notification: str
    color: Tuple[int, int, int]


class Buff(ABC):
    """Abstract base class for all player buffs.
    
        Each buff type extends this class and provides calculate_value()
        to compute the buff effect based on current level.
    
        Attributes:
            name: Display name of the buff.
            description: Human-readable effect description.
            category: Buff category (health, offense, defense, utility).
            max_level: Maximum stackable level for this buff.
        """
    # Class-level metadata — subclasses override these
    NAME: str = ""
    COLOR: Tuple[int, int, int] = (0, 0, 0)

    def get_name(self) -> str:
        return self.NAME

    def get_color(self) -> Tuple[int, int, int]:
        return self.COLOR

    def get_notification(self, level: int) -> str:
        return f'获得: {self.NAME}'

    @abstractmethod
    def apply(self, player) -> BuffResult:
        pass

    @abstractmethod
    def calculate_value(self, base_value: int, current_level: int) -> int:
        pass

    @abstractmethod
    def calculate_increment(self, base_value: int) -> int:
        pass
