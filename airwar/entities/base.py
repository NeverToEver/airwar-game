"""Base entity classes for the Air War game.

Provides foundational data structures (Vector2, Rect) and the Entity base class
used by all game entities (Player, Enemy, Boss, Bullet).
"""

from abc import ABC, abstractmethod
import math
import pygame
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class Vector2:
    """2D vector with basic arithmetic operations."""

    x: float = 0
    y: float = 0

    def __add__(self, other: 'Vector2') -> 'Vector2':
        return Vector2(self.x + other.x, self.y + other.y)

    def __radd__(self, other: 'Vector2') -> 'Vector2':
        return self.__add__(other)

    def __mul__(self, scalar: float) -> 'Vector2':
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vector2':
        return self.__mul__(scalar)

    def __abs__(self) -> 'Vector2':
        return Vector2(abs(self.x), abs(self.y))
    
    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalize(self) -> 'Vector2':
        length = self.length()
        if length > 0:
            return Vector2(self.x / length, self.y / length)
        return Vector2(0, 0)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Rect:
    """Axis-aligned rectangle for collision detection and positioning."""
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
    
    @property
    def left(self) -> float:
        return self.x
    
    @property
    def top(self) -> float:
        return self.y

    def colliderect(self, other: 'Rect') -> bool:
        return (self.x < other.x + other.width and
                self.x + self.width > other.x and
                self.y < other.y + other.height and
                self.y + self.height > other.y)


class Entity(ABC):
    """Abstract base class for all game entities.

    Provides common functionality for positioning, velocity, rendering,
    and collision detection. Subclasses must implement update() and render().

    Attributes:
        rect: Position and dimensions of the entity.
        velocity: Current velocity vector.
        active: Whether the entity is active and should be updated/rendered.
    """

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
    """Data class for bullet configuration.

    Attributes:
        damage: Damage dealt by the bullet.
        speed: Movement speed in pixels per frame.
        owner: Owner of the bullet ("player" or "enemy").
        bullet_type: Type of bullet ("single", "spread", "laser", etc.).
        angle_offset: Angle offset in degrees for spread patterns.
        is_laser: Whether the bullet is a laser beam.
        is_explosive: Whether the bullet explodes on impact.
    """
    damage: int = 10
    speed: float = 14.0
    owner: str = "player"
    bullet_type: str = "single"
    angle_offset: float = 0.0
    is_laser: bool = False
    is_explosive: bool = False


@dataclass
class EnemyData:
    """Data class for enemy configuration.

    Attributes:
        health: Maximum health points.
        speed: Movement speed in pixels per frame.
        score: Score awarded when destroyed.
        enemy_type: Type of enemy movement pattern.
        fire_rate: Fire rate in frames between shots.
        bullet_type: Type of bullet fired by the enemy.
    """
    health: int = 100
    speed: float = 3.0
    score: int = 100
    enemy_type: str = "basic"
    fire_rate: int = 120
    bullet_type: str = "single"
