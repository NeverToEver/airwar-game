from types import SimpleNamespace

import pygame

from airwar.entities.base import Rect
from airwar.entities.enemy import Enemy, EnemySpawner
from airwar.config import DIFFICULTY_SETTINGS
from airwar.game.managers.spawn_controller import SpawnController
from airwar.game.systems.aim_assist_system import AimAssistSystem


def test_spawn_controller_applies_spread_enemy_caps_by_difficulty() -> None:
    for difficulty, cap in [("easy", 1), ("medium", 2), ("hard", 3)]:
        settings = DIFFICULTY_SETTINGS[difficulty]
        controller = SpawnController(settings)

        assert settings["spread_enemy_cap"] == cap
        assert controller.enemy_spawner._spread_enemy_cap == cap


def test_enemy_wave_limits_spread_bullet_types() -> None:
    spawner = EnemySpawner()
    spawner.set_spread_enemy_cap(2)
    spawn_data = [
        (0, 0, "spread", "aggressive", True),
        (0, 0, "spread", "straight", False),
        (0, 0, "spread", "noise", True),
        (0, 0, "spread", "sine", False),
    ]

    limited = spawner._limit_spread_bullet_types(spawn_data)

    assert sum(1 for item in limited if item[2] == "spread") == 2
    assert limited[2][2] == "laser"
    assert limited[3][2] == "single"


def test_enemy_spread_fire_pattern_is_narrowed() -> None:
    assert Enemy.SPREAD_FIRE_OFFSETS == (-28, -14, 0, 14, 28)


def test_aim_assist_sticks_while_mouse_stays_near_target() -> None:
    aim_assist = AimAssistSystem()
    target = SimpleNamespace(
        active=True,
        rect=Rect(100, 100, 80, 60),
    )
    spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    assisted = aim_assist.update(spawn_controller, (120, 120))

    assert assisted == target.rect.center

    aim_assist.update(spawn_controller, (165, 130))

    assert aim_assist.get_aim_position() == target.rect.center


def test_aim_assist_defaults_to_nearest_enemy_when_cursor_is_not_on_target() -> None:
    aim_assist = AimAssistSystem()
    near = SimpleNamespace(active=True, rect=pygame.Rect(200, 160, 80, 60))
    far = SimpleNamespace(active=True, rect=pygame.Rect(700, 500, 80, 60))
    spawn_controller = SimpleNamespace(enemies=[far, near], boss=None)

    aim_assist.update(spawn_controller, (40, 40))

    assert aim_assist.get_aim_position() == near.rect.center


def test_aim_assist_crosshair_overlaps_locked_enemy_center() -> None:
    aim_assist = AimAssistSystem()
    target = SimpleNamespace(active=True, rect=pygame.Rect(200, 160, 80, 60))
    spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    aim_assist.update(spawn_controller, (40, 40))

    assert aim_assist.get_aim_position() == target.rect.center


def test_aim_assist_switches_to_enemy_in_mouse_movement_direction() -> None:
    aim_assist = AimAssistSystem()
    center = SimpleNamespace(
        active=True,
        rect=pygame.Rect(450, 340, 80, 60),
    )
    right = SimpleNamespace(
        active=True,
        rect=pygame.Rect(780, 340, 80, 60),
    )
    spawn_controller = SimpleNamespace(enemies=[center, right], boss=None)

    aim_assist.update(spawn_controller, (490, 370))
    aim_assist.update(spawn_controller, (490 + AimAssistSystem.AIM_ASSIST_SWITCH_DISTANCE + 12, 372))

    assert aim_assist.get_aim_position() == right.rect.center


def test_aim_assist_delays_raw_input_to_reduce_cursor_snapping() -> None:
    aim_assist = AimAssistSystem()
    target = SimpleNamespace(active=True, rect=pygame.Rect(500, 300, 80, 60))
    spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    aim_assist.update(spawn_controller, (100, 100))
    aim_assist.update(spawn_controller, (500, 300))

    assert aim_assist._smoothed_raw_aim_position != aim_assist._raw_aim_position
    assert 100 < aim_assist._smoothed_raw_aim_position[0] < 500
    assert 100 < aim_assist._smoothed_raw_aim_position[1] < 300


def test_aim_assist_delayed_input_catches_up_over_repeated_updates() -> None:
    aim_assist = AimAssistSystem()
    target = SimpleNamespace(active=True, rect=pygame.Rect(500, 300, 80, 60))
    spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    aim_assist.update(spawn_controller, (100, 100))
    aim_assist.set_raw_aim_position((500, 300))
    for _ in range(20):
        aim_assist.update_aim_assist(spawn_controller)

    assert abs(aim_assist._smoothed_raw_aim_position[0] - 500) < 10
    assert abs(aim_assist._smoothed_raw_aim_position[1] - 300) < 10


def test_aim_assist_releases_after_stronger_decisive_mouse_movement() -> None:
    aim_assist = AimAssistSystem()
    target = SimpleNamespace(active=True, rect=pygame.Rect(100, 100, 80, 60))
    spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    aim_assist.update(spawn_controller, (120, 120))
    aim_assist.update(spawn_controller, (120 + AimAssistSystem.AIM_ASSIST_RELEASE_DISTANCE + 12, 120))

    assert aim_assist.get_aim_position() == aim_assist._smoothed_raw_aim_position
    assert aim_assist.get_aim_position() != aim_assist._raw_aim_position
