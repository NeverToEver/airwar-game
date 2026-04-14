from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple


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
