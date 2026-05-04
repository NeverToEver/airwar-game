from types import SimpleNamespace

from airwar.game.managers.game_controller import GameplayState
from airwar.game.managers.game_loop_manager import GameLoopManager


class _Player:
    def __init__(self):
        self.active = True
        self.controls_locked = False
        self.bullet_damage = 50
        self.fire_interval = 8
        self.rect = SimpleNamespace(centerx=400, centery=500)
        self.update_calls = 0
        self.auto_fire_calls = 0
        self.locked_seen_during_update = []

    def get_weapon_status(self):
        return {"spread": False, "laser": False, "explosive": False}

    def update(self):
        self.update_calls += 1
        self.locked_seen_during_update.append(self.controls_locked)

    def auto_fire(self):
        self.auto_fire_calls += 1

    def cleanup_inactive_bullets(self):
        pass


class _Boss:
    def __init__(self):
        self.lock_player = False
        self.active = True
        self.rect = SimpleNamespace(centerx=300, centery=180, width=210, height=170)

    def should_lock_player_movement(self):
        return self.lock_player

    def get_hitbox(self):
        return self.rect


class _Spawn:
    def __init__(self, boss):
        self.enemies = []
        self.boss = boss
        self.player_dps_seen = []
        self.spawn_boss_args = []

    def update(self, *args):
        return False

    def cleanup(self):
        pass

    def balance_for_player_dps(self, player_dps):
        self.player_dps_seen.append(player_dps)

    def spawn_boss(self, *args):
        self.spawn_boss_args.append(args)
        return SimpleNamespace(data=SimpleNamespace(escape_time=1200))


def _make_loop(boss, spawn=None):
    controller = SimpleNamespace(
        state=SimpleNamespace(
            gameplay_state=GameplayState.PLAYING,
            running=True,
        ),
        update=lambda player, has_regen: None,
        show_notification=lambda message: None,
    )
    renderer = SimpleNamespace(update_death_animation=lambda: None)
    spawn = spawn or _Spawn(boss)
    reward = SimpleNamespace(unlocked_buffs=[], slow_factor=1.0, base_bullet_damage=10)
    bullet = SimpleNamespace(update_all=lambda: None, cleanup=lambda: None, clear_enemy_bullets=lambda **kwargs: None)
    boss_killed_calls = []
    boss_manager = SimpleNamespace(
        boss=boss,
        update=lambda player: None,
        on_boss_hit=lambda score: None,
        on_boss_killed=lambda: boss_killed_calls.append(True),
        boss_killed_calls=boss_killed_calls,
    )
    collision = SimpleNamespace(set_explosion_callback=lambda callback: None)
    return GameLoopManager(controller, renderer, spawn, reward, bullet, boss_manager, collision)


def test_game_loop_locks_player_controls_during_boss_enrage_update_only() -> None:
    boss = _Boss()
    player = _Player()
    loop = _make_loop(boss)

    boss.lock_player = True
    loop.update_game(player)

    assert player.locked_seen_during_update[-1] is True
    assert player.controls_locked is False

    boss.lock_player = False
    loop.update_game(player)

    assert player.locked_seen_during_update[-1] is False
    assert player.controls_locked is False


def test_game_loop_preserves_external_player_lock_after_boss_enrage_update() -> None:
    boss = _Boss()
    player = _Player()
    player.controls_locked = True
    loop = _make_loop(boss)

    boss.lock_player = True
    loop.update_game(player)

    assert player.locked_seen_during_update[-1] is True
    assert player.controls_locked is True


def test_game_loop_balances_spawn_controller_from_current_player_dps() -> None:
    boss = _Boss()
    player = _Player()
    spawn = _Spawn(boss)
    loop = _make_loop(boss, spawn)

    loop.update_game(player)

    assert spawn.player_dps_seen[-1] == 750


def test_game_loop_counts_spread_shot_in_current_player_dps() -> None:
    boss = _Boss()
    player = _Player()
    player.get_weapon_status = lambda: {"spread": True, "laser": False, "explosive": False}
    spawn = _Spawn(boss)
    loop = _make_loop(boss, spawn)

    loop.update_game(player)

    assert spawn.player_dps_seen[-1] == 2250


def test_game_loop_queues_boss_death_explosion_before_cleanup() -> None:
    boss = _Boss()
    spawn = _Spawn(boss)
    loop = _make_loop(boss, spawn)

    loop._on_boss_destroyed()
    stats = loop.get_explosion_stats()

    assert stats["active_count"] > 0
    assert stats["queued_count"] > 0
    assert loop._boss_manager.boss_killed_calls == [True]
