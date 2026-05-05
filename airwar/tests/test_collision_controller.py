from dataclasses import dataclass

import airwar.game.managers.collision_controller as collision_module
from airwar.entities.base import BulletData, EnemyData, Rect
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.managers.collision_controller import CollisionController


@dataclass
class FakeBullet:
    rect: Rect
    data: BulletData
    active: bool = True

    def __post_init__(self):
        self._hit_enemies = []

    def get_rect(self):
        return self.rect

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)


class FakeEnemy:
    def __init__(self, rect, health=10, score=25):
        self.rect = rect
        self._hitbox = rect
        self.data = EnemyData(health=health, score=score)
        self.health = health
        self.active = True

    def get_hitbox(self):
        return self._hitbox

    def get_rect(self):
        return self.rect

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False


class FakePlayer:
    def __init__(self, rect):
        self._hitbox = rect
        self.rect = rect
        self.health = 100

    def get_hitbox(self):
        return self._hitbox

    def take_damage(self, damage):
        self.health -= damage


def test_player_bullet_kills_enemy_and_deactivates_without_piercing():
    controller = CollisionController()
    controller._use_rust = False
    bullet = FakeBullet(Rect(0, 0, 10, 10), BulletData(damage=20, owner="player"))
    enemy = FakeEnemy(Rect(0, 0, 20, 20), health=10, score=30)

    score, kills = controller.check_player_bullets_vs_enemies(
        [bullet],
        [enemy],
        score_multiplier=2,
        explosive_level=0,
        piercing_level=0,
    )

    assert score == 60
    assert kills == 1
    assert enemy.active is False
    assert bullet.active is False


def test_enemy_kill_triggers_lifesteal_callback():
    controller = CollisionController()
    controller._use_rust = False
    bullet = FakeBullet(Rect(0, 0, 10, 10), BulletData(damage=20, owner="player"))
    enemy = FakeEnemy(Rect(0, 0, 20, 20), health=10, score=30)
    player = FakePlayer(Rect(100, 100, 20, 20))
    player.get_bullets = lambda: [bullet]
    healed = []

    controller.check_all_collisions(
        player=player,
        enemies=[enemy],
        boss=None,
        enemy_bullets=[],
        reward_system=type(
            "RewardSystem",
            (),
            {
                "calculate_damage_taken": lambda self, damage: damage,
                "try_dodge": lambda self: False,
                "piercing_level": 0,
            },
        )(),
        explosive_level=0,
        piercing_level=0,
        on_enemy_killed=lambda score: None,
        on_lifesteal=lambda hit_player, score: healed.append((hit_player, score)),
    )

    assert healed == [(player, 30)]


def test_rust_collision_path_skips_python_spatial_grid(monkeypatch):
    controller = CollisionController()
    controller._use_rust = True
    bullet = FakeBullet(Rect(0, 0, 10, 10), BulletData(damage=20, owner="player"))
    enemy = FakeEnemy(Rect(0, 0, 20, 20), health=10, score=30)
    player = FakePlayer(Rect(100, 100, 20, 20))
    player.get_bullets = lambda: [bullet]
    added_to_grid = []

    def fake_batch_collide(bullets, enemies, grid_cell_size):
        return [(bullets[0][0], enemies[0][0])]

    monkeypatch.setattr(collision_module, "batch_collide_bullets_vs_entities", fake_batch_collide)
    monkeypatch.setattr(controller, "_add_to_grid", lambda entity, rect: added_to_grid.append((entity, rect)))

    controller.check_all_collisions(
        player=player,
        enemies=[enemy],
        boss=None,
        enemy_bullets=[],
        reward_system=type(
            "RewardSystem",
            (),
            {
                "calculate_damage_taken": lambda self, damage: damage,
                "try_dodge": lambda self: False,
                "piercing_level": 0,
            },
        )(),
        explosive_level=0,
        piercing_level=0,
    )

    assert added_to_grid == []
    assert enemy.active is False


def test_rust_collision_data_uses_rect_dimensions_not_square_radius(monkeypatch):
    controller = CollisionController()
    controller._use_rust = True
    bullet = FakeBullet(Rect(0, 0, 80, 4), BulletData(damage=20, owner="player"))
    enemy = FakeEnemy(Rect(30, 30, 4, 4), health=10, score=30)
    captured = {}

    def fake_batch_collide(bullets, enemies, grid_cell_size):
        captured["bullets"] = bullets
        captured["enemies"] = enemies
        return []

    monkeypatch.setattr(collision_module, "batch_collide_bullets_vs_entities", fake_batch_collide)

    score, kills = controller.check_player_bullets_vs_enemies(
        [bullet],
        [enemy],
        score_multiplier=1,
        explosive_level=0,
        piercing_level=0,
    )

    assert score == 0
    assert kills == 0
    assert captured["bullets"] == [(0, 0.0, 0.0, 80.0, 4.0)]
    assert captured["enemies"] == [(-1, 30.0, 30.0, 4.0, 4.0)]


def test_piercing_bullet_stays_active_after_enemy_hit():
    controller = CollisionController()
    controller._use_rust = False
    bullet = FakeBullet(Rect(0, 0, 10, 10), BulletData(damage=5, owner="player"))
    enemy = FakeEnemy(Rect(0, 0, 20, 20), health=10, score=30)

    score, kills = controller.check_player_bullets_vs_enemies(
        [bullet],
        [enemy],
        score_multiplier=1,
        explosive_level=0,
        piercing_level=1,
    )

    assert score == 0
    assert kills == 0
    assert enemy.health == 5
    assert bullet.active is True


def test_piercing_bullet_does_not_damage_same_enemy_twice():
    controller = CollisionController()
    controller._use_rust = False
    bullet = FakeBullet(Rect(0, 0, 10, 10), BulletData(damage=5, owner="player"))
    enemy = FakeEnemy(Rect(0, 0, 20, 20), health=15, score=30)

    controller.check_player_bullets_vs_enemies(
        [bullet],
        [enemy],
        score_multiplier=1,
        explosive_level=0,
        piercing_level=1,
    )
    score, kills = controller.check_player_bullets_vs_enemies(
        [bullet],
        [enemy],
        score_multiplier=1,
        explosive_level=0,
        piercing_level=1,
    )

    assert score == 0
    assert kills == 0
    assert enemy.health == 10
    assert bullet.active is True


def test_player_collision_uses_enemy_hitbox_not_visual_rect():
    controller = CollisionController()
    player = FakePlayer(Rect(0, 0, 10, 10))
    enemy = FakeEnemy(Rect(100, 100, 20, 20))
    enemy._hitbox = Rect(0, 0, 20, 20)
    hits = []

    did_hit = controller.check_player_vs_enemies(
        player.get_hitbox(),
        [enemy],
        lambda: False,
        lambda damage: hits.append(damage),
    )

    assert did_hit is True
    assert hits == [GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE]


def test_enemy_bullet_hits_player_once():
    controller = CollisionController()
    player = FakePlayer(Rect(0, 0, 20, 20))
    bullet = FakeBullet(
        Rect(5, 5, 5, 5),
        BulletData(damage=40, owner="enemy"),
    )
    hits = []

    did_hit = controller.check_enemy_bullets_vs_player(
        [bullet],
        player,
        lambda damage: damage // 2,
        lambda damage, target: hits.append((damage, target)),
    )

    assert did_hit is True
    assert hits == [(20, player)]


def test_boss_collision_ignores_entering_boss():
    controller = CollisionController()
    player = FakePlayer(Rect(0, 0, 20, 20))

    class Boss(FakeEnemy):
        def is_entering(self):
            return True

    boss = Boss(Rect(0, 0, 20, 20))

    did_hit = controller.check_boss_vs_player(
        boss,
        player,
        lambda damage: damage,
        lambda damage, target: target.take_damage(damage),
    )

    assert did_hit is False
    assert player.health == 100


def test_boss_collision_applies_configured_damage_after_entering():
    controller = CollisionController()
    player = FakePlayer(Rect(0, 0, 20, 20))

    class Boss(FakeEnemy):
        def is_entering(self):
            return False

    boss = Boss(Rect(0, 0, 20, 20))

    did_hit = controller.check_boss_vs_player(
        boss,
        player,
        lambda damage: damage,
        lambda damage, target: target.take_damage(damage),
    )

    assert did_hit is True
    assert player.health == 100 - GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE


def test_boss_collision_uses_boss_hitbox():
    controller = CollisionController()
    player = FakePlayer(Rect(0, 0, 10, 10))

    class Boss(FakeEnemy):
        def __init__(self):
            super().__init__(Rect(100, 100, 20, 20))
            self._hitbox = Rect(0, 0, 20, 20)

        def is_entering(self):
            return False

    boss = Boss()

    did_hit = controller.check_boss_vs_player(
        boss,
        player,
        lambda damage: damage,
        lambda damage, target: target.take_damage(damage),
    )

    assert did_hit is True
