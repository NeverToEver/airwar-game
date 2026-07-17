"""Tests for enemy-bullet-vs-player single-hit semantics.

The Rust batch path and the Python fallback must agree: at most one enemy
bullet damages the player per frame. The Rust path previously applied damage
from every intersecting bullet (until the player died), diverging from the
fallback's first-hit return — a difference masked only by the scene clearing
nearby bullets after a hit.
"""

from types import SimpleNamespace

import pygame
import pytest

from airwar.entities.bullet import Bullet, BulletData
from airwar.game.managers import collision_controller
from airwar.game.managers.collisions.enemy_bullet_vs_player import EnemyBulletVsPlayerStrategy


def _make_strategy(use_rust: bool) -> EnemyBulletVsPlayerStrategy:
    return EnemyBulletVsPlayerStrategy(
        grid_cell_size=100,
        enemy_bullet_data=[],
        enemy_bullet_map={},
        player_entity_data=[],
        get_use_rust=lambda: use_rust,
    )


def _make_bullet(damage: int = 7) -> Bullet:
    return Bullet(100.0, 100.0, BulletData(damage=damage, speed=0.0, owner="enemy"))


def _make_player() -> SimpleNamespace:
    return SimpleNamespace(active=True, get_hitbox=lambda: pygame.Rect(90, 90, 40, 40))


@pytest.mark.parametrize("use_rust", [True, False])
def test_only_first_hit_applies_damage(monkeypatch, use_rust):
    """Two bullets intersecting the player on the same frame deal damage once."""
    bullets = [_make_bullet(), _make_bullet()]
    player = _make_player()
    if use_rust:
        monkeypatch.setattr(
            collision_controller,
            "batch_collide_bullets_vs_entities",
            lambda eb_data, player_data, cell_size: [(0, -1), (1, -1)],
        )

    damages = []
    hit = _make_strategy(use_rust).check_enemy_bullets_vs_player(
        bullets, player, lambda d: d, lambda dmg, p: damages.append(dmg)
    )

    assert hit is True
    assert damages == [7]
    assert bullets[0].active is False  # the hitting bullet is consumed
    assert bullets[1].active is True  # the second bullet survives to next frame


def test_rust_path_skips_inactive_hit(monkeypatch):
    """An inactive bullet returned by the batch pass must not apply damage."""
    bullets = [_make_bullet(), _make_bullet()]
    bullets[0].active = False
    player = _make_player()
    monkeypatch.setattr(
        collision_controller,
        "batch_collide_bullets_vs_entities",
        lambda eb_data, player_data, cell_size: [(0, -1), (1, -1)],
    )

    damages = []
    hit = _make_strategy(True).check_enemy_bullets_vs_player(
        bullets, player, lambda d: d, lambda dmg, p: damages.append(dmg)
    )

    assert hit is True
    assert damages == [7]  # from the second bullet only
    assert bullets[1].active is False
