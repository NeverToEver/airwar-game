import math

import pygame
import pytest

from airwar.entities import Bullet, BulletData, Player
from airwar.entities.base import Vector2
from airwar.input import MockInputHandler
from airwar.ui.aim_crosshair import AimCrosshair


@pytest.fixture(scope="module", autouse=True)
def _init_pygame():
    pygame.init()
    yield


def _make_player() -> Player:
    player = Player(400, 900, MockInputHandler())
    player.fire_cooldown = 0
    return player


def _bullet_origin(player: Player) -> tuple[float, float]:
    return (
        player.rect.x + player.rect.width / 2,
        player.rect.y - player.BULLET_SPAWN_Y_OFFSET,
    )


def test_player_single_bullet_aims_at_crosshair() -> None:
    player = _make_player()
    origin_x, origin_y = _bullet_origin(player)
    player.set_aim_target(origin_x + 300, origin_y)

    player.auto_fire()

    bullet = player.get_bullets()[0]
    assert bullet.velocity.x > 0
    assert math.isclose(bullet.velocity.y, 0.0, abs_tol=1e-6)
    assert math.isclose(bullet.velocity.length(), bullet.data.speed, rel_tol=1e-6)


def test_player_spread_rotates_around_crosshair_direction() -> None:
    player = _make_player()
    player.activate_shotgun()
    origin_x, origin_y = _bullet_origin(player)
    player.set_aim_target(origin_x + 300, origin_y)

    player.auto_fire()

    bullets = player.get_bullets()
    assert len(bullets) == 3
    assert all(bullet.velocity.x > 0 for bullet in bullets)
    assert bullets[0].velocity.y < 0
    assert math.isclose(bullets[1].velocity.y, 0.0, abs_tol=1e-6)
    assert bullets[2].velocity.y > 0


@pytest.mark.parametrize("weapon_mode", ["laser", "explosive", "laser_explosive"])
def test_player_special_weapon_modes_aim_at_crosshair(weapon_mode: str) -> None:
    player = _make_player()
    if "laser" in weapon_mode:
        player.activate_laser(duration=120)
    if "explosive" in weapon_mode:
        player.activate_explosive()
    origin_x, origin_y = _bullet_origin(player)
    player.set_aim_target(origin_x, origin_y + 300)

    player.auto_fire()

    bullet = player.get_bullets()[0]
    assert math.isclose(bullet.velocity.x, 0.0, abs_tol=1e-6)
    assert bullet.velocity.y > 0
    assert math.isclose(bullet.velocity.length(), bullet.data.speed, rel_tol=1e-6)
    assert bullet.data.is_laser is ("laser" in weapon_mode)
    assert bullet.data.is_explosive is ("explosive" in weapon_mode)


def test_bullet_deactivates_when_leaving_horizontal_bounds() -> None:
    bullet = Bullet(2010, 200, BulletData(speed=20))
    bullet.velocity = Vector2(40, 0)

    bullet.update()

    assert bullet.active is False


def test_aim_crosshair_draws_visible_pixels() -> None:
    surface = pygame.Surface((120, 120), pygame.SRCALPHA)
    crosshair = AimCrosshair()

    crosshair.update()
    crosshair.render(surface, (60, 60))

    assert surface.get_bounding_rect().width > 0
