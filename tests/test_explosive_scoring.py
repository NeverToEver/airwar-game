"""Tests for explosive-bullet AoE kill scoring.

Bug: enemies killed by the splash of an explosive bullet were neither
counted in ``enemies_killed`` nor awarded score — only the directly-hit
enemy was scored. Splash kills must score like direct kills, and the
directly-hit enemy must never be double-counted when the splash
finishes it off.
"""

from types import SimpleNamespace

import pygame
import pytest

from airwar.entities.bullet import Bullet, BulletData
from airwar.game.managers.collision_controller import CollisionController


class _FakeEnemy:
    def __init__(self, x: float, y: float, health: int, score: int) -> None:
        self.active = True
        self.health = health
        self.data = SimpleNamespace(score=score)
        self.rect = pygame.Rect(x, y, 40, 40)
        self._hitbox = pygame.Rect(x, y, 40, 40)

    def get_hitbox(self) -> pygame.Rect:
        return self._hitbox

    def take_damage(self, damage: int) -> None:
        self.health -= damage
        if self.health <= 0:
            self.active = False


def _make_controller(use_rust: bool) -> CollisionController:
    controller = CollisionController()
    controller._use_rust = use_rust
    return controller


def _make_bullet(x: float, y: float, damage: int = 10) -> Bullet:
    return Bullet(x, y, BulletData(damage=damage, speed=0.0, owner="player"))


@pytest.mark.parametrize("use_rust", [True, False])
def test_splash_kill_is_scored(use_rust):
    """An enemy killed only by the explosion splash must count and score."""
    controller = _make_controller(use_rust)
    bullet = _make_bullet(100.0, 100.0)
    direct = _FakeEnemy(95, 95, health=1000, score=100)  # survives direct hit + splash
    splash = _FakeEnemy(130, 95, health=30, score=50)  # dies to splash only (30 dmg)
    bystander = _FakeEnemy(400, 400, health=30, score=999)  # outside radius

    score, killed = controller.check_player_bullets_vs_enemies(
        [bullet], [direct, splash, bystander], 1.0, explosive_level=1
    )

    assert splash.active is False
    assert direct.active is True
    assert bystander.active is True
    assert killed == 1
    assert score == 50


@pytest.mark.parametrize("use_rust", [True, False])
def test_direct_hit_finished_by_splash_is_not_double_counted(use_rust):
    """Directly-hit enemy killed by its own splash scores exactly once."""
    controller = _make_controller(use_rust)
    bullet = _make_bullet(100.0, 100.0, damage=10)
    direct = _FakeEnemy(95, 95, health=40, score=100)  # 10 direct + 30 splash -> dead
    splash = _FakeEnemy(130, 95, health=30, score=50)  # dies to splash

    score, killed = controller.check_player_bullets_vs_enemies(
        [bullet], [direct, splash], 1.0, explosive_level=1
    )

    assert direct.active is False
    assert splash.active is False
    assert killed == 2
    assert score == 150


def test_splash_score_respects_multiplier():
    controller = _make_controller(use_rust=True)
    bullet = _make_bullet(100.0, 100.0)
    direct = _FakeEnemy(95, 95, health=1000, score=100)
    splash = _FakeEnemy(130, 95, health=30, score=50)

    score, killed = controller.check_player_bullets_vs_enemies(
        [bullet], [direct, splash], 2.0, explosive_level=1
    )

    assert killed == 1
    assert score == 100
