from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class BuffResult:
    name: str
    notification: str
    color: Tuple[int, int, int]


class Buff(ABC):
    @abstractmethod
    def apply(self, player) -> BuffResult:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_color(self) -> Tuple[int, int, int]:
        pass

    @abstractmethod
    def calculate_value(self, base_value: int, current_level: int) -> int:
        pass

    @abstractmethod
    def calculate_increment(self, base_value: int) -> int:
        pass

    @abstractmethod
    def get_notification(self, level: int) -> str:
        pass
