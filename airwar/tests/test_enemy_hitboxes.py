from airwar.config import ENEMY_COLLISION_SCALE, ENEMY_HITBOX_PADDING, ENEMY_HITBOX_SIZE, ENEMY_VISUAL_SCALE
from airwar.entities.enemy import Boss, BossData, EliteEnemy, EliteEnemyData, Enemy, EnemyData


def test_regular_enemy_hitbox_is_larger_than_render_rect_but_within_sprite_footprint():
    enemy = Enemy(100, 120, EnemyData())
    hitbox = enemy.get_hitbox()
    expected_render = int((ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2) * ENEMY_VISUAL_SCALE)
    expected_collision = int((ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2) * ENEMY_COLLISION_SCALE)

    assert enemy.rect.width == expected_render
    assert hitbox.width == expected_collision
    assert hitbox.height == expected_collision
    assert hitbox.center == enemy.get_rect().center
    assert hitbox.width > enemy.rect.width
    assert hitbox.width <= enemy.rect.width * 1.35


def test_elite_enemy_hitbox_tracks_elite_visual_scale():
    elite = EliteEnemy(100, 120, EliteEnemyData())
    hitbox = elite.get_hitbox()

    assert hitbox.center == elite.get_rect().center
    assert hitbox.width > elite.rect.width
    assert hitbox.width < elite.rect.width * elite.VISUAL_SCALE
    assert hitbox.height < elite.rect.height * elite.VISUAL_SCALE


def test_boss_hitbox_is_wider_but_not_taller_than_visual_footprint():
    boss = Boss(100, 120, BossData(width=120, height=100))
    hitbox = boss.get_hitbox()

    assert hitbox.center == boss.get_rect().center
    assert hitbox.width > boss.rect.width
    assert hitbox.height >= boss.rect.height
    assert hitbox.width <= boss.rect.width * 1.85
    assert hitbox.height <= boss.rect.height * 1.3
