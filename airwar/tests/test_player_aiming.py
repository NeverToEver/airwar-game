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


def _turn_player_to_target(player: Player, aim_target: tuple[float, float], frames: int = 60) -> None:
    player.set_aim_target(*aim_target)
    for _ in range(frames):
        player.update()


def _local_side_offset(player: Player, bullet: Bullet) -> float:
    facing = player.get_facing_direction()
    right = (-facing.y, facing.x)
    dx = bullet.rect.centerx - player.rect.centerx
    dy = bullet.rect.centery - player.rect.centery
    return dx * right[0] + dy * right[1]


def test_player_single_bullet_aims_at_crosshair() -> None:
    player = _make_player()
    aim_target = (player.rect.centerx + 300, player.rect.centery - 120)
    _turn_player_to_target(player, aim_target)

    player.auto_fire()

    bullets = player.get_bullets()
    facing = player.get_facing_direction()
    assert len(bullets) == 2
    assert _local_side_offset(player, bullets[0]) < 0 < _local_side_offset(player, bullets[1])
    assert all(bullet.velocity.x > 0 for bullet in bullets)
    assert all(bullet.velocity.y < 0 for bullet in bullets)
    assert all(math.isclose(bullet.velocity.x, facing.x * bullet.data.speed, rel_tol=1e-6) for bullet in bullets)
    assert all(math.isclose(bullet.velocity.y, facing.y * bullet.data.speed, rel_tol=1e-6) for bullet in bullets)
    assert all(math.isclose(bullet.velocity.length(), bullet.data.speed, rel_tol=1e-6) for bullet in bullets)


def test_player_spread_rotates_around_crosshair_direction() -> None:
    player = _make_player()
    player.activate_shotgun()
    _turn_player_to_target(player, (player.rect.centerx + 300, player.rect.centery))

    player.auto_fire()

    bullets = player.get_bullets()
    assert len(bullets) == 6
    assert all(bullet.velocity.x > 0 for bullet in bullets)
    left_wing = bullets[:3]
    right_wing = bullets[3:]
    assert left_wing[0].velocity.y < left_wing[1].velocity.y < left_wing[2].velocity.y
    assert right_wing[0].velocity.y < right_wing[1].velocity.y < right_wing[2].velocity.y
    assert player.SPREAD_ANGLES == (-10, 0, 10)


def test_player_turns_toward_new_aim_target_without_snapping() -> None:
    player = _make_player()
    center = (player.rect.centerx, player.rect.centery)
    player.set_aim_target(center[0], center[1] - 400)
    player.update()

    player.set_aim_target(center[0] + 400, center[1])
    player.update()

    facing = player.get_facing_direction()
    assert math.isclose(player.get_facing_angle_degrees(), player.AIM_TURN_RATE_DEGREES, abs_tol=0.1)
    assert 0 < facing.x < 1
    assert facing.y < 0

    for _ in range(20):
        player.update()

    facing = player.get_facing_direction()
    assert facing.x > 0.99
    assert abs(facing.y) < 0.05


def test_auto_fire_uses_current_fighter_facing_while_turning() -> None:
    player = _make_player()
    center = (player.rect.centerx, player.rect.centery)
    player.set_aim_target(center[0] + 400, center[1])

    player.update()
    player.auto_fire()

    bullets = player.get_bullets()
    assert len(bullets) == 2
    assert all(0 < bullet.velocity.x < bullet.data.speed * 0.5 for bullet in bullets)
    assert all(bullet.velocity.y < 0 for bullet in bullets)


@pytest.mark.parametrize("weapon_mode", ["laser", "explosive", "laser_explosive"])
def test_player_special_weapon_modes_aim_at_crosshair(weapon_mode: str) -> None:
    player = _make_player()
    if "laser" in weapon_mode:
        player.activate_laser(duration=120)
    if "explosive" in weapon_mode:
        player.activate_explosive()
    _turn_player_to_target(player, (player.rect.centerx, player.rect.centery + 300))

    player.auto_fire()

    bullets = player.get_bullets()
    assert len(bullets) == 2
    assert all(abs(bullet.velocity.x) < 1e-6 for bullet in bullets)
    assert all(bullet.velocity.y > 0 for bullet in bullets)
    assert all(math.isclose(bullet.velocity.length(), bullet.data.speed, rel_tol=1e-6) for bullet in bullets)
    assert {bullet.data.is_laser for bullet in bullets} == {"laser" in weapon_mode}
    assert {bullet.data.is_explosive for bullet in bullets} == {"explosive" in weapon_mode}


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
