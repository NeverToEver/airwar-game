import math

import pytest

from airwar.config import DIFFICULTY_SETTINGS, set_display_size
from airwar.entities.enemy import Boss, BossData
from airwar.game.managers.spawn_controller import SpawnController


class BulletCollector:
    def __init__(self):
        self.bullets = []

    def spawn_bullet(self, bullet):
        self.bullets.append(bullet)


@pytest.fixture(autouse=True)
def restore_screen_size():
    yield
    set_display_size(1920, 1080)


def test_spawned_boss_health_is_four_elite_enemies_across_difficulties():
    for settings in DIFFICULTY_SETTINGS.values():
        controller = SpawnController(settings)
        boss = controller.spawn_boss(0, settings["bullet_damage"])
        elite_health = int(settings["enemy_health"] * 2.5)

        assert boss.data.health == elite_health * 4


def test_enemy_health_balances_against_current_player_dps():
    settings = DIFFICULTY_SETTINGS["medium"]
    controller = SpawnController(settings)

    controller.balance_for_player_dps(750)
    baseline_health = controller.enemy_spawner.health
    controller.balance_for_player_dps(1500)

    assert baseline_health == 900
    assert controller.enemy_spawner.health == baseline_health * 2


def test_spawned_boss_uses_dps_balanced_enemy_health():
    settings = DIFFICULTY_SETTINGS["medium"]
    controller = SpawnController(settings)
    controller.balance_for_player_dps(1500)

    boss = controller.spawn_boss(0, settings["bullet_damage"], player_dps=1500)
    elite_health = int(controller.enemy_spawner.health * 2.5)

    assert boss.data.health == elite_health * 4


def test_spawned_boss_escape_time_scales_with_health_and_player_output():
    settings = DIFFICULTY_SETTINGS["medium"]
    controller = SpawnController(settings)
    controller.MIN_ESCAPE_TIME = 0
    controller.MAX_ESCAPE_TIME = 99999

    boss = controller.spawn_boss(4, settings["bullet_damage"])
    estimated_damage_per_frame = settings["bullet_damage"] * 2 / 8
    estimated_kill_frames = math.ceil(boss.data.health / estimated_damage_per_frame)

    assert boss.data.escape_time >= estimated_kill_frames * 2

    stronger_player_controller = SpawnController(settings)
    stronger_player_controller.MIN_ESCAPE_TIME = 0
    stronger_player_controller.MAX_ESCAPE_TIME = 99999
    stronger_player_boss = stronger_player_controller.spawn_boss(4, settings["bullet_damage"] * 2)

    assert stronger_player_boss.data.escape_time < boss.data.escape_time


def test_boss_enrage_duration_is_about_six_seconds():
    assert Boss.ENRAGE_DURATION == 6 * 60


def test_boss_enrage_visual_intensity_eases_in_before_reaching_cap():
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())

    boss.take_damage(700)
    boss.update(player_pos=(500, 400))

    initial_intensity = boss.enrage_visual_intensity()
    for _ in range(boss.ENRAGE_DURATION // 3):
        boss.update(player_pos=(500, 400))
    ramped_intensity = boss.enrage_visual_intensity()

    assert 0 < initial_intensity < 0.2
    assert ramped_intensity > initial_intensity
    assert ramped_intensity <= 0.8
