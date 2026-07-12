"""Tests for the unified Entity base-class interface (batch F1)."""

from types import SimpleNamespace

import pytest

from airwar.entities.base import Entity
from airwar.entities.bullet import Bullet, BulletData
from airwar.entities.enemy.boss.boss import Boss, BossData
from airwar.entities.enemy.enemy import Enemy, EnemyData
from airwar.entities.player import Player


class IncompleteEntity(Entity):
    """Subclass that forgets to implement ``take_damage``."""

    def update(self, *args, **kwargs) -> None:
        pass

    def render(self, surface) -> None:
        pass


class _DummyInputHandler(SimpleNamespace):
    """Minimal input handler that satisfies Player construction."""

    def __init__(self):
        super().__init__(
            tick=lambda: None,
            is_boost_pressed=lambda: False,
            is_fire_pressed=lambda: False,
            is_precision_pressed=lambda: False,
            get_movement_direction=lambda: (0.0, 0.0),
            get_aim_direction=lambda: (0.0, -1.0),
        )


def test_abstract_take_damage_prevents_instantiation():
    with pytest.raises(TypeError):
        IncompleteEntity(0, 0, 10, 10)


def test_entity_kill_sets_inactive():
    bullet = Bullet(0, 0, BulletData())
    assert bullet.active is True
    bullet.kill()
    assert bullet.active is False


def test_player_implements_take_damage():
    player = Player(100, 100, _DummyInputHandler())
    assert callable(getattr(player, "take_damage", None))


def test_enemy_implements_take_damage():
    enemy = Enemy(100, 100, EnemyData())
    assert callable(getattr(enemy, "take_damage", None))
    enemy.take_damage(50)
    assert enemy.health == EnemyData().health - 50


def test_boss_implements_take_damage():
    boss = Boss(100, 100, BossData())
    assert callable(getattr(boss, "take_damage", None))


def test_take_damage_signatures_accept_single_damage_arg():
    """All concrete entities accept ``take_damage(damage: int)``."""
    player = Player(100, 100, _DummyInputHandler())
    enemy = Enemy(100, 100, EnemyData())
    boss = Boss(100, 100, BossData())

    for entity in (player, enemy, boss):
        # Should not raise when called with a single integer.
        entity.take_damage(0)
