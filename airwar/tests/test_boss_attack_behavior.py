import math

import pytest

from airwar.config.game_config import set_screen_size
from airwar.entities.enemy import Boss, BossData
from airwar.game.managers.bullet_manager import BulletManager


class BulletCollector:
    def __init__(self):
        self.bullets = []

    def spawn_bullet(self, bullet):
        self.bullets.append(bullet)


@pytest.fixture(autouse=True)
def restore_screen_size():
    yield
    set_screen_size(1920, 1080)


def test_boss_aim_attack_dashes_toward_player_before_snapshot_lasers():
    boss = Boss(400, 180, BossData(width=170, height=140))
    boss.entering = False
    boss.attack_pattern = 1
    boss.attack_direction = "down"
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)

    start_center = boss.rect.center
    player_pos = (start_center[0] + 220, start_center[1] + 320)

    boss._fire(player_pos)

    assert collector.bullets == []
    assert boss.rect.center == start_center

    last_center = start_center
    for _ in range(boss.AIM_DASH_DURATION):
        boss.update(player_pos=player_pos)
        assert boss.rect.centerx >= last_center[0]
        assert boss.rect.centery >= last_center[1]
        last_center = boss.rect.center

    assert boss.rect.centerx - start_center[0] > 100
    assert boss.rect.centery - start_center[1] > 120
    assert len(collector.bullets) == boss.AIM_BULLET_COUNT
    assert {bullet.data.bullet_type for bullet in collector.bullets} == {"laser"}

    for bullet in collector.bullets:
        target_angle = math.atan2(player_pos[1] - bullet.rect.y, player_pos[0] - bullet.rect.x)
        bullet_angle = math.atan2(bullet.velocity.y, bullet.velocity.x)
        assert abs(target_angle - bullet_angle) < 0.02


def test_boss_aim_attack_does_not_home_after_fire():
    boss = Boss(400, 180, BossData(width=170, height=140))
    boss.entering = False
    bullets = boss._aim_attack((650, 520))

    bullet = bullets[0]
    velocity_before = (bullet.velocity.x, bullet.velocity.y)
    bullet.update()

    assert (bullet.velocity.x, bullet.velocity.y) == velocity_before


def test_boss_enrage_triggers_once_at_thirty_percent_and_pulls_player_to_center():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)

    class Player:
        def __init__(self):
            self.rect = type("Rect", (), {"width": 68, "height": 82, "x": 120, "y": 640})()

    player = Player()
    boss.take_damage(700)
    boss.update(player=player, player_pos=(player.rect.x + 34, player.rect.y + 41))

    assert boss.is_enraged() is True
    assert boss.is_enrage_active() is True
    assert (player.rect.x, player.rect.y) == (466, 359)
    assert boss.enrage_visual_intensity() > 0

    boss.take_damage(1)
    boss.update(player=player, player_pos=(500, 400))

    assert boss.is_enraged() is True


def test_boss_enrage_bullets_hold_then_release_slowly_toward_player():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_DURATION - 1):
        boss.update(player_pos=player_center)

    assert collector.bullets
    assert all(getattr(bullet, "clear_immune", False) for bullet in collector.bullets)
    assert all(getattr(bullet, "held", False) for bullet in collector.bullets)
    assert all((bullet.velocity.x, bullet.velocity.y) == (0, 0) for bullet in collector.bullets)

    boss.update(player_pos=player_center)

    assert boss.is_enrage_active() is False
    assert all(not getattr(bullet, "held", False) for bullet in collector.bullets)
    assert all(0 < bullet.velocity.length() <= boss.ENRAGE_BULLET_SPEED for bullet in collector.bullets)


def test_bullet_manager_clear_enemy_bullets_keeps_clear_immune_bullets():
    clearable = type("Bullet", (), {"active": True})()
    immune = type("Bullet", (), {"active": True, "clear_immune": True})()
    spawn_controller = type("SpawnController", (), {"enemy_bullets": [clearable, immune]})()
    player = type("Player", (), {"get_bullets": lambda self: []})()
    manager = BulletManager(player, spawn_controller)

    manager.clear_enemy_bullets()

    assert clearable.active is False
    assert immune.active is True
    assert spawn_controller.enemy_bullets == [immune]


def test_bullet_manager_can_force_clear_enrage_bullets():
    immune = type("Bullet", (), {"active": True, "clear_immune": True})()
    spawn_controller = type("SpawnController", (), {"enemy_bullets": [immune]})()
    player = type("Player", (), {"get_bullets": lambda self: []})()
    manager = BulletManager(player, spawn_controller)

    manager.clear_enemy_bullets(include_clear_immune=True)

    assert immune.active is False
    assert spawn_controller.enemy_bullets == []
