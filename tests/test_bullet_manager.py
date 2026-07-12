"""Tests for BulletManager boundary fixes (batch F3)."""

from types import SimpleNamespace

import pytest

from airwar.entities.bullet import Bullet, BulletData
from airwar.game.managers.bullet_manager import BulletManager


@pytest.fixture
def manager():
    player = SimpleNamespace(
        get_bullets=lambda: [],
        cleanup_inactive_bullets=lambda: None,
    )
    spawn_controller = SimpleNamespace(enemy_bullets=[])
    return BulletManager(player, spawn_controller)


def test_data_none_bullet_is_skipped(manager):
    """A bullet whose ``data`` is None must not enter the batch buffer."""
    good_bullet = Bullet(10.0, 20.0, BulletData(speed=1.0))
    bad_bullet = Bullet(30.0, 40.0, BulletData(speed=1.0))
    bad_bullet.data = None

    bullets = [good_bullet, bad_bullet]
    manager._update_bullets_batch(bullets, cleanup=False)

    # The good bullet moved one frame; the bad bullet was left untouched.
    assert good_bullet.rect.x == pytest.approx(10.0)
    assert good_bullet.rect.y == pytest.approx(19.0)
    assert bad_bullet.rect.x == pytest.approx(30.0)
    assert bad_bullet.rect.y == pytest.approx(40.0)
    assert bad_bullet.active is True


def test_data_none_bullet_does_not_shift_buffer_index(manager):
    """Indices in the binary buffer must stay aligned with active bullets."""
    b1 = Bullet(0.0, 0.0, BulletData(speed=2.0))
    b2 = Bullet(100.0, 100.0, BulletData(speed=2.0))
    b2.data = None
    b3 = Bullet(5.0, 5.0, BulletData(speed=3.0))

    bullets = [b1, b2, b3]
    manager._update_bullets_batch(bullets, cleanup=False)

    # b3 should be treated as the second active bullet, not be skipped or
    # be misaligned because of the None-data bullet in the middle.
    assert b1.rect.x == pytest.approx(0.0)
    assert b1.rect.y == pytest.approx(-2.0)
    assert b3.rect.x == pytest.approx(5.0)
    assert b3.rect.y == pytest.approx(2.0)
    assert b2.active is True
