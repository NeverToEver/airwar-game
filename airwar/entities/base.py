"""Base entity classes for the Air War game.

Provides foundational data structures (Vector2, Rect) and the Entity base class
used by all game entities (Player, Enemy, Boss, Bullet).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pygame

from airwar.core_bindings import (
    RUST_AVAILABLE,
    vec2_add,
    vec2_angle,
    vec2_clamp_length,
    vec2_distance,
    vec2_dot,
    vec2_from_angle,
    vec2_length,
    vec2_lerp,
    vec2_normalize,
    vec2_scale,
    vec2_sub,
)


@dataclass
class Vector2:
    """2D vector with basic arithmetic operations.

    Arithmetic operators use Rust bindings when available (single
    FFI call per op, avoids creating a Python Vector2 just to add
    two floats). All 11 vec2_* bindings are exercised by this class.
    """

    x: float = 0
    y: float = 0

    def __add__(self, other: Vector2) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_add(self.x, self.y, other.x, other.y)
            return Vector2(nx, ny)
        return Vector2(self.x + other.x, self.y + other.y)

    def __radd__(self, other: Vector2) -> Vector2:
        # `sum([v1, v2])` starts with `0 + v1`; treat numeric 0 as identity.
        if isinstance(other, (int, float)) and other == 0:
            return Vector2(self.x, self.y)
        return self.__add__(other)

    def __sub__(self, other: Vector2) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_sub(self.x, self.y, other.x, other.y)
            return Vector2(nx, ny)
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_scale(self.x, self.y, float(scalar))
            return Vector2(nx, ny)
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __abs__(self) -> Vector2:
        return Vector2(abs(self.x), abs(self.y))

    def length(self) -> float:
        if RUST_AVAILABLE:
            return vec2_length(self.x, self.y)
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_normalize(self.x, self.y)
            return Vector2(nx, ny)
        length = self.length()
        if length > 0:
            return Vector2(self.x / length, self.y / length)
        return Vector2(0, 0)

    def dot(self, other: Vector2) -> float:
        if RUST_AVAILABLE:
            return vec2_dot(self.x, self.y, other.x, other.y)
        return self.x * other.x + self.y * other.y

    def distance(self, other: Vector2) -> float:
        if RUST_AVAILABLE:
            return vec2_distance(self.x, self.y, other.x, other.y)
        return math.hypot(self.x - other.x, self.y - other.y)

    def angle(self) -> float:
        """Angle in radians, 0 = +X axis, counter-clockwise."""
        if RUST_AVAILABLE:
            return vec2_angle(self.x, self.y)
        return math.atan2(self.y, self.x)

    @classmethod
    def from_angle(cls, angle: float, magnitude: float = 1.0) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_from_angle(angle, magnitude)
            return cls(nx, ny)
        return cls(math.cos(angle) * magnitude, math.sin(angle) * magnitude)

    def lerp(self, other: Vector2, t: float) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_lerp(self.x, self.y, other.x, other.y, float(t))
            return Vector2(nx, ny)
        return Vector2(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
        )

    def clamp_length(self, max_length: float) -> Vector2:
        if RUST_AVAILABLE:
            nx, ny = vec2_clamp_length(self.x, self.y, float(max_length))
            return Vector2(nx, ny)
        length = self.length()
        if length > max_length and length > 0:
            scale = max_length / length
            return Vector2(self.x * scale, self.y * scale)
        return Vector2(self.x, self.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Rect:
    """Axis-aligned rectangle for collision detection and positioning."""

    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> tuple[float, float]:
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

    def colliderect(self, other: Rect) -> bool:
        return (
            self.x < other.x + other.width
            and self.x + self.width > other.x
            and self.y < other.y + other.height
            and self.y + self.height > other.y
        )


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
        self._sprite: pygame.Surface | None = None

    @property
    def position(self) -> tuple[float, float]:
        return (self.rect.x, self.rect.y)

    @position.setter
    def position(self, pos: tuple[float, float]):
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
