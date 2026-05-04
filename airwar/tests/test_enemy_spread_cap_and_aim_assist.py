from types import SimpleNamespace

import pygame

from airwar.entities.base import Rect
from airwar.entities.enemy import Enemy, EnemySpawner
from airwar.config import DIFFICULTY_SETTINGS
from airwar.game.managers.spawn_controller import SpawnController
from airwar.scenes.game_scene import GameScene


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
    scene = GameScene()
    target = SimpleNamespace(
        active=True,
        rect=Rect(100, 100, 80, 60),
    )
    scene.spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    scene._set_raw_aim_position((120, 120))
    scene._update_aim_assist()
    assisted = scene._aim_position

    assert assisted != scene._raw_aim_position
    assert assisted[0] > 120
    assert assisted[1] > 120

    scene._set_raw_aim_position((165, 130))
    scene._update_aim_assist()

    assert scene._aim_assist_target is target


def test_aim_assist_defaults_to_nearest_enemy_when_cursor_is_not_on_target() -> None:
    scene = GameScene()
    near = SimpleNamespace(active=True, rect=pygame.Rect(200, 160, 80, 60))
    far = SimpleNamespace(active=True, rect=pygame.Rect(700, 500, 80, 60))
    scene.spawn_controller = SimpleNamespace(enemies=[far, near], boss=None)

    scene._set_raw_aim_position((40, 40))
    scene._update_aim_assist()

    assert scene._aim_assist_target is near


def test_aim_assist_switches_to_enemy_in_mouse_movement_direction() -> None:
    scene = GameScene()
    center = SimpleNamespace(
        active=True,
        rect=pygame.Rect(450, 340, 80, 60),
    )
    right = SimpleNamespace(
        active=True,
        rect=pygame.Rect(780, 340, 80, 60),
    )
    scene.spawn_controller = SimpleNamespace(enemies=[center, right], boss=None)

    scene._set_raw_aim_position((490, 370))
    scene._update_aim_assist()
    scene._set_raw_aim_position((490 + scene.AIM_ASSIST_SWITCH_DISTANCE + 12, 372))
    scene._update_aim_assist()

    assert scene._aim_assist_target is right


def test_aim_assist_delays_raw_input_to_reduce_cursor_snapping() -> None:
    scene = GameScene()
    target = SimpleNamespace(active=True, rect=pygame.Rect(500, 300, 80, 60))
    scene.spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    scene._set_raw_aim_position((100, 100))
    scene._update_aim_assist()
    scene._set_raw_aim_position((500, 300))
    scene._update_aim_assist()

    assert scene._smoothed_raw_aim_position != scene._raw_aim_position
    assert 100 < scene._smoothed_raw_aim_position[0] < 500
    assert 100 < scene._smoothed_raw_aim_position[1] < 300


def test_aim_assist_delayed_input_catches_up_over_repeated_updates() -> None:
    scene = GameScene()
    target = SimpleNamespace(active=True, rect=pygame.Rect(500, 300, 80, 60))
    scene.spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    scene._set_raw_aim_position((100, 100))
    scene._update_aim_assist()
    scene._set_raw_aim_position((500, 300))
    for _ in range(20):
        scene._update_aim_assist()

    assert abs(scene._smoothed_raw_aim_position[0] - 500) < 10
    assert abs(scene._smoothed_raw_aim_position[1] - 300) < 10


def test_aim_assist_releases_after_stronger_decisive_mouse_movement() -> None:
    scene = GameScene()
    target = SimpleNamespace(active=True, rect=pygame.Rect(100, 100, 80, 60))
    scene.spawn_controller = SimpleNamespace(enemies=[target], boss=None)

    scene._set_raw_aim_position((120, 120))
    scene._update_aim_assist()
    scene._set_raw_aim_position((120 + scene.AIM_ASSIST_RELEASE_DISTANCE + 12, 120))
    scene._update_aim_assist()

    assert scene._aim_assist_target is None
    assert scene._aim_position == scene._smoothed_raw_aim_position
    assert scene._aim_position != scene._raw_aim_position
