from abc import ABC, abstractmethod
import pygame
from typing import Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Vector2:
    x: float = 0
    y: float = 0

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def centerx(self) -> float:
        return self.x + self.width / 2

    @property
    def centery(self) -> float:
        return self.y + self.height / 2

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def right(self) -> float:
        return self.x + self.width

    def colliderect(self, other: 'Rect') -> bool:
        return (self.x < other.x + other.width and
                self.x + self.width > other.x and
                self.y < other.y + other.height and
                self.y + self.height > other.y)


class Entity(ABC):
    def __init__(self, x: float, y: float, width: float, height: float):
        self.rect = Rect(x, y, width, height)
        self.velocity = Vector2()
        self.active = True
        self._sprite: Optional[pygame.Surface] = None

    @property
    def position(self) -> Tuple[float, float]:
        return (self.rect.x, self.rect.y)

    @position.setter
    def position(self, pos: Tuple[float, float]):
        self.rect.x, self.rect.y = pos

    @abstractmethod
    def update(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        pass

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height)


@dataclass
class BulletData:
    damage: int = 10
    speed: float = 10.0
    owner: str = "player"
    bullet_type: str = "single"
    angle_offset: float = 0.0
    is_laser: bool = False


@dataclass
class EnemyData:
    health: int = 100
    speed: float = 3.0
    score: int = 100
    enemy_type: str = "basic"
    fire_rate: int = 120
    bullet_type: str = "single"
