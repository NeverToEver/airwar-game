"""Tests for Boss entity and BossManager boundary fixes (batch F2, F5, F7)."""

from types import SimpleNamespace

from airwar.entities.enemy.boss.boss import Boss, BossData
from airwar.game.managers.boss_manager import BossManager


def test_max_health_zero_does_not_raise_on_enrage_check():
    """F2: max_health <= 0 guard must precede the health ratio division."""
    boss = Boss(100, 100, BossData(health=0))
    # Should not raise ZeroDivisionError.
    boss._trigger_enrage_if_needed()
    assert boss._state.enraged is False


def test_clear_boss_resets_spawn_timer():
    """F5: BossManager.clear_boss delegates to SpawnController.clear_boss."""
    spawn_controller = SimpleNamespace(
        boss=None,
        boss_spawn_timer=999,
        clear_boss=lambda: setattr(spawn_controller, "boss_spawn_timer", 0) or True,
    )
    game_controller = SimpleNamespace(state=SimpleNamespace(score=0))
    reward_system = SimpleNamespace()
    bullet_manager = SimpleNamespace()

    boss_manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
    boss_manager.clear_boss()
    assert spawn_controller.boss_spawn_timer == 0


def test_boss_dead_methods_removed():
    """F7: unused enrage sub-state helpers are no longer defined."""
    boss = Boss(100, 100, BossData())
    assert not hasattr(boss, "_update_enrage_transition")
    assert not hasattr(boss, "_update_enrage_release_hold")
    assert not hasattr(boss, "_update_enrage_return")
