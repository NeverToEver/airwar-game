import airwar.game.managers.collision_controller as collision_module
from airwar.entities.base import BulletData, Rect
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.managers.collision_controller import CollisionController
from airwar.tests.conftest import StubEnemy


def test_player_bullet_kills_enemy_and_deactivates_without_piercing(stub_player, stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = False
    bullet = stub_bullet
    bullet.data = BulletData(damage=20, owner="player")
    enemy = stub_enemy
    enemy.data.score = 30

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


def test_enemy_kill_triggers_lifesteal_callback(stub_player, stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = False
    bullet = stub_bullet
    bullet.data = BulletData(damage=20, owner="player")
    enemy = stub_enemy
    player = stub_player
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

    assert healed == [(player, 25)]


def test_rust_collision_path_skips_python_spatial_grid(monkeypatch, stub_player, stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = True
    bullet = stub_bullet
    bullet.data = BulletData(damage=20, owner="player")
    enemy = stub_enemy
    player = stub_player
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


def test_rust_collision_data_uses_rect_dimensions_not_square_radius(monkeypatch, stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = True
    bullet = stub_bullet
    bullet.rect = Rect(0, 0, 80, 4)
    bullet.data = BulletData(damage=20, owner="player")
    enemy = stub_enemy
    enemy.rect = Rect(30, 30, 4, 4)
    enemy._hitbox = Rect(30, 30, 4, 4)
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


def test_piercing_bullet_stays_active_after_enemy_hit(stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = False
    bullet = stub_bullet
    bullet.data = BulletData(damage=5, owner="player")
    enemy = stub_enemy

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


def test_piercing_bullet_does_not_damage_same_enemy_twice(stub_enemy, stub_bullet):
    controller = CollisionController()
    controller._use_rust = False
    bullet = stub_bullet
    bullet.data = BulletData(damage=5, owner="player")
    enemy = stub_enemy
    enemy.health = 15

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


def test_player_collision_uses_enemy_hitbox_not_visual_rect(stub_player, stub_enemy):
    controller = CollisionController()
    player = stub_player
    enemy = stub_enemy
    enemy.rect = Rect(100, 100, 20, 20)
    enemy._hitbox = Rect(0, 0, 20, 20)
    hits = []

    did_hit = controller.check_player_vs_enemies(
        player.get_hitbox(),
        [enemy],
        lambda: False,
        hits.append,
    )

    assert did_hit is True
    assert hits == [GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE]


def test_enemy_bullet_hits_player_once(stub_player, stub_bullet):
    controller = CollisionController()
    player = stub_player
    bullet = stub_bullet
    bullet.rect = Rect(5, 5, 5, 5)
    bullet.data = BulletData(damage=40, owner="enemy")
    hits = []

    did_hit = controller.check_enemy_bullets_vs_player(
        [bullet],
        player,
        lambda damage: damage // 2,
        lambda damage, target: hits.append((damage, target)),
    )

    assert did_hit is True
    assert hits == [(20, player)]


def test_boss_collision_ignores_entering_boss(stub_player):
    controller = CollisionController()
    player = stub_player

    class Boss(StubEnemy):
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


def test_boss_collision_applies_configured_damage_after_entering(stub_player):
    controller = CollisionController()
    player = stub_player

    class Boss(StubEnemy):
        def __init__(self, rect):
            super().__init__(rect)
            self.is_entering = False

    boss = Boss(Rect(0, 0, 20, 20))

    did_hit = controller.check_boss_vs_player(
        boss,
        player,
        lambda damage: damage,
        lambda damage, target: target.take_damage(damage),
    )

    assert did_hit is True
    assert player.health == 100 - GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE


def test_boss_collision_uses_boss_hitbox(stub_player):
    controller = CollisionController()
    player = stub_player

    class Boss(StubEnemy):
        def __init__(self):
            super().__init__(Rect(100, 100, 20, 20))
            self._hitbox = Rect(0, 0, 20, 20)
            self.is_entering = False

    boss = Boss()

    did_hit = controller.check_boss_vs_player(
        boss,
        player,
        lambda damage: damage,
        lambda damage, target: target.take_damage(damage),
    )

    assert did_hit is True
