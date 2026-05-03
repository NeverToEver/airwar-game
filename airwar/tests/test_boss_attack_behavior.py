import math

from airwar.entities.enemy import Boss, BossData


class BulletCollector:
    def __init__(self):
        self.bullets = []

    def spawn_bullet(self, bullet):
        self.bullets.append(bullet)


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
