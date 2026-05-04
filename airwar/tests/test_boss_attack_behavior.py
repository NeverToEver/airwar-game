import math
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from airwar.config.game_config import set_screen_size
from airwar.entities.base import BulletData, Rect, Vector2
from airwar.entities.bullet import Bullet
from airwar.entities.enemy import Boss, BossData
from airwar.game.managers.bullet_manager import BulletManager
from airwar.game.managers.collision_controller import CollisionController
from airwar.scenes.game_scene import GameScene


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
    assert boss.is_enrage_transitioning() is True
    assert (player.rect.x, player.rect.y) == (466, 359)
    assert boss.enrage_visual_intensity() > 0

    boss.take_damage(1)
    boss.update(player=player, player_pos=(500, 400))

    assert boss.is_enraged() is True


def test_boss_enrage_transition_delays_snapshot_attacks_and_eases_to_release_anchor():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)

    boss.take_damage(700)
    boss.update(player_pos=(500, 400))

    assert boss.is_enrage_transitioning() is True
    assert collector.bullets == []
    assert boss._enrage_trail == []

    for _ in range(boss.ENRAGE_TRANSITION_DURATION - 1):
        boss.update(player_pos=(500, 400))

    assert boss.is_enrage_transitioning() is False
    assert collector.bullets == []

    for _ in range(boss.ENRAGE_ATTACK_WINDUP):
        boss.update(player_pos=(500, 400))

    assert collector.bullets
    assert all(getattr(bullet, "held", False) for bullet in collector.bullets)


def test_boss_enrage_locks_health_at_thirty_percent_until_bullets_release():
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)

    boss.take_damage(800)
    boss.update(player_pos=(500, 400))

    assert boss.health == 300
    assert boss.is_enrage_active() is True

    boss.take_damage(500)

    assert boss.health == 300
    assert boss.active is True

    for _ in range(boss.ENRAGE_DURATION):
        boss.update(player_pos=(500, 400))

    assert boss.is_enrage_active() is False
    assert boss.take_damage(500) == boss.data.score
    assert boss.active is False


def test_boss_enrage_reports_player_movement_lock_until_release():
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)
    boss.update(player_pos=(500, 400))

    assert boss.should_lock_player_movement() is True

    for _ in range(boss.ENRAGE_DURATION):
        boss.update(player_pos=(500, 400))

    assert boss.should_lock_player_movement() is False


def test_boss_enrage_release_hold_does_not_recenter_unlocked_player():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())

    class Player:
        def __init__(self):
            self.rect = type("Rect", (), {"width": 68, "height": 82, "x": 120, "y": 640})()

    player = Player()
    boss.take_damage(700)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player=player, player_pos=(player.rect.x + 34, player.rect.y + 41))

    player.rect.x = 220
    player.rect.y = 620
    boss.update(player=player, player_pos=(254, 661))

    assert boss.should_lock_player_movement() is False
    assert (player.rect.x, player.rect.y) == (220, 620)


def test_boss_enrage_finishes_at_players_six_oclock_release_anchor():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player_pos=player_center)

    assert boss.is_enrage_active() is False
    assert boss.rect.centerx == pytest.approx(player_center[0])
    assert boss.rect.centery == pytest.approx(player_center[1] + boss._enrage_path_radius(player_center))


def test_boss_enrage_holds_snapshot_attacks_until_flow_finishes():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)
    boss.take_damage(700)

    player_center = (500, 400)
    boss.update(player_pos=player_center)
    initial_count = len(collector.bullets)

    assert initial_count == 0

    for _ in range(boss.ENRAGE_TRANSITION_DURATION + boss.ENRAGE_ATTACK_WINDUP):
        boss.update(player_pos=player_center)

    assert collector.bullets
    assert all(getattr(bullet, "clear_immune", False) for bullet in collector.bullets)
    assert all(getattr(bullet, "held", False) for bullet in collector.bullets)
    assert all(bullet.velocity.length() == 0 for bullet in collector.bullets)
    first_wave_count = len(collector.bullets)

    for _ in range(boss.ENRAGE_ATTACK_INTERVAL):
        boss.update(player_pos=player_center)

    assert len(collector.bullets) > first_wave_count
    assert all(getattr(bullet, "held", False) for bullet in collector.bullets)
    assert all(bullet.velocity.length() == 0 for bullet in collector.bullets)


def test_boss_enrage_releases_held_bullets_gradually_after_flow_finishes():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player_pos=player_center)

    held_bullets = [bullet for bullet in collector.bullets if getattr(bullet, "held", False)]
    assert held_bullets
    assert any(getattr(bullet, "enrage_release_delay", 0) > 0 for bullet in held_bullets)
    assert all(getattr(bullet, "enrage_release_pending", False) for bullet in held_bullets)

    spawn_controller = SimpleNamespace(enemy_bullets=collector.bullets)
    player = SimpleNamespace(get_bullets=lambda: [], cleanup_inactive_bullets=lambda: None)
    manager = BulletManager(player, spawn_controller)
    manager._use_rust = False

    manager.update_all()
    first_released = [bullet for bullet in collector.bullets if not getattr(bullet, "held", False)]
    still_held = [bullet for bullet in collector.bullets if getattr(bullet, "held", False)]

    assert first_released
    assert still_held
    assert all(
        0 < bullet.velocity.length() <= bullet.enrage_release_speed + 1e-6
        for bullet in first_released
    )

    for _ in range(boss.ENRAGE_RELEASE_INTERVAL * (boss._enrage_attack_index + 1)):
        manager.update_all()

    assert all(not getattr(bullet, "held", False) for bullet in collector.bullets)


def test_boss_enrage_path_completes_one_square_and_one_circle():
    set_screen_size(1200, 900)
    boss = Boss(500, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)

    player_center = (600, 450)
    radius = boss._enrage_path_radius(player_center)
    square = boss.ENRAGE_SQUARE_PATH_RATIO

    assert boss._enrage_path_center(player_center, 0.0) == pytest.approx((600, 450 + radius))
    assert boss._enrage_path_center(player_center, square * 0.25) == pytest.approx((600 + radius, 450))
    assert boss._enrage_path_center(player_center, square * 0.50) == pytest.approx((600, 450 - radius))
    assert boss._enrage_path_center(player_center, square * 0.75) == pytest.approx((600 - radius, 450))
    assert boss._enrage_path_center(player_center, square) == pytest.approx((600, 450 + radius))
    assert boss._enrage_path_center(player_center, 1.0) == pytest.approx((600, 450 + radius))


def test_boss_enrage_uses_slower_snapshot_cadence_for_fewer_bullets():
    set_screen_size(1200, 900)
    boss = Boss(500, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)
    boss.take_damage(700)

    player_center = (600, 450)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player_pos=player_center)

    assert 0 < len(collector.bullets) <= 110
    assert boss.ENRAGE_ATTACK_INTERVAL >= 56
    assert boss.ENRAGE_SNAPSHOT_LASER_COUNT <= 4
    assert boss.ENRAGE_SNAPSHOT_RING_COUNT <= 8


def test_boss_enrage_faces_player_and_aims_muzzles_during_all_direction_movement():
    set_screen_size(1200, 900)
    boss = Boss(500, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)

    player_center = (600, 450)
    for _ in range(boss.ENRAGE_TRANSITION_DURATION + boss.ENRAGE_ATTACK_WINDUP + 1):
        boss.update(player_pos=player_center)

    forward = boss._facing_vector()
    target_vector = Vector2(player_center[0] - boss.rect.centerx, player_center[1] - boss.rect.centery).normalize()
    assert forward.x * target_vector.x + forward.y * target_vector.y > 0.999

    muzzles = boss._boss_muzzle_positions()
    average_muzzle = (
        sum(muzzle[0] for muzzle in muzzles) / len(muzzles),
        sum(muzzle[1] for muzzle in muzzles) / len(muzzles),
    )
    muzzle_vector = Vector2(average_muzzle[0] - boss.rect.centerx, average_muzzle[1] - boss.rect.centery).normalize()
    assert muzzle_vector.x * target_vector.x + muzzle_vector.y * target_vector.y > 0.999
    assert boss._muzzle_flash_timer > 0
    assert boss._muzzle_flash_positions
    assert boss.ENRAGE_MUZZLE_FLASH_PULSES >= 4


def test_boss_enrage_trail_is_longer_and_half_resolution_blurred():
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_TRANSITION_DURATION + boss.ENRAGE_TRAIL_LENGTH + 20):
        boss.update(player_pos=player_center)

    assert len(boss._enrage_trail) == boss.ENRAGE_TRAIL_LENGTH
    assert boss.ENRAGE_TRAIL_LENGTH >= 32

    ghost = boss._get_enrage_trail_ghost(0.5)
    render_width, render_height = boss._enrage_trail_render_size()

    assert render_width == int(boss.rect.width * boss.ENRAGE_TRAIL_FINAL_SCALE)
    assert render_height == int(boss.rect.height * boss.ENRAGE_TRAIL_FINAL_SCALE)
    assert ghost.get_width() == int(render_width * boss.ENRAGE_TRAIL_SCALE)
    assert ghost.get_height() == int(render_height * boss.ENRAGE_TRAIL_SCALE)
    assert boss.ENRAGE_TRAIL_BLUR_PASSES >= 2


def test_boss_enrage_finish_clears_trail_artifacts():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    collector = BulletCollector()
    boss.set_bullet_spawner(collector)
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player_pos=player_center)

    assert boss.is_enrage_active() is False
    assert boss._enrage_trail == []


def test_boss_enrage_visuals_fade_through_release_hold_and_return_without_jump():
    set_screen_size(1000, 800)
    boss = Boss(400, 120, BossData(health=1000, width=170, height=140))
    boss.entering = False
    boss.set_bullet_spawner(BulletCollector())
    boss.take_damage(700)

    player_center = (500, 400)
    for _ in range(boss.ENRAGE_DURATION + 1):
        boss.update(player_pos=player_center)

    release_center = boss.rect.center
    assert boss.is_enrage_active() is False
    assert boss.enrage_visual_intensity() > 0

    boss.update(player_pos=player_center)
    assert math.hypot(boss.rect.centerx - release_center[0], boss.rect.centery - release_center[1]) < 1

    for _ in range(boss.ENRAGE_RELEASE_HOLD_DURATION):
        boss.update(player_pos=player_center)

    return_start = boss.rect.center
    boss.update(player_pos=player_center)
    assert 0 < math.hypot(boss.rect.centerx - return_start[0], boss.rect.centery - return_start[1]) < 12
    assert boss.enrage_visual_intensity() > 0


def test_bullet_manager_keeps_held_enrage_bullets_stationary_on_rust_path():
    set_screen_size(1000, 800)
    held = Bullet(100, 120, BulletData(damage=1, speed=5, owner="enemy", bullet_type="single"))
    held.held = True
    held.velocity = Vector2(9, 4)
    moving = Bullet(40, 60, BulletData(damage=1, speed=5, owner="enemy", bullet_type="single"))
    moving.velocity = Vector2(3, 2)
    spawn_controller = SimpleNamespace(enemy_bullets=[held, moving])
    player = SimpleNamespace(get_bullets=lambda: [], cleanup_inactive_bullets=lambda: None)
    manager = BulletManager(player, spawn_controller)
    manager._use_rust = True

    with patch("airwar.game.managers.bullet_manager.batch_update_bullets") as batch_update:
        batch_update.return_value = [(id(moving), moving.rect.x + 3, moving.rect.y + 2, True)]
        manager.update_all()

    assert batch_update.call_args.args[0] == [
        (id(moving), 40, 60, 3, 2, 0, False, 800.0)
    ]
    assert (held.rect.x, held.rect.y) == (100, 120)
    assert (moving.rect.x, moving.rect.y) == (43, 62)


def test_held_enemy_bullets_do_not_damage_player_until_released():
    controller = CollisionController()
    player = SimpleNamespace(get_hitbox=lambda: Rect(0, 0, 30, 30))
    held = SimpleNamespace(
        active=True,
        held=True,
        rect=Rect(0, 0, 10, 10),
        data=BulletData(damage=50, owner="enemy"),
    )
    hits = []

    on_hit = lambda damage, target: hits.append((damage, target))

    assert controller.check_enemy_bullets_vs_player([held], player, lambda damage: damage, on_hit) is False
    assert hits == []

    held.held = False

    assert controller.check_enemy_bullets_vs_player([held], player, lambda damage: damage, on_hit) is True
    assert hits == [(50, player)]


def test_boss_enrage_overlay_no_longer_draws_orange_warning_ring():
    pygame = pytest.importorskip("pygame")
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    scene = GameScene()
    scene.spawn_controller = SimpleNamespace(
        boss=SimpleNamespace(
            is_enrage_active=lambda: True,
            enrage_visual_intensity=lambda: 0.8,
            rect=SimpleNamespace(centerx=320, centery=220),
        )
    )

    with patch("airwar.scenes.game_scene.pygame.draw.circle") as draw_circle:
        scene._render_boss_enrage_overlay(surface)

    colors = [call.args[2] for call in draw_circle.call_args_list]
    assert not any(color[:3] == (224, 106, 72) for color in colors)


def test_boss_enrage_overlay_uses_visual_intensity_after_active_phase():
    pygame = pytest.importorskip("pygame")
    surface = pygame.Surface((160, 120), pygame.SRCALPHA)
    surface.fill((20, 30, 40))
    scene = GameScene()
    scene.spawn_controller = SimpleNamespace(
        boss=SimpleNamespace(
            is_enrage_active=lambda: False,
            enrage_visual_intensity=lambda: 0.5,
            rect=SimpleNamespace(centerx=80, centery=60),
        )
    )

    before = surface.copy()
    scene._render_boss_enrage_overlay(surface)

    assert pygame.image.tostring(surface, "RGBA") != pygame.image.tostring(before, "RGBA")


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
