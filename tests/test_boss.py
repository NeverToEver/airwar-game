"""Tests for Boss entity and BossManager boundary fixes (batch F2, F5, F7)."""

from types import SimpleNamespace

import pygame

from airwar.config import get_screen_height, get_screen_width
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


def _boss_ready_to_enrage() -> Boss:
    boss = Boss(100, 100, BossData(health=100))
    boss.health = 10  # below ENRAGE_TRIGGER_RATIO
    return boss


def test_enrage_trigger_skips_player_centering_when_position_locked():
    """P1-A: while the pipeline marks the player position as locked
    (mothership docking), the enrage trigger must not move the player
    rect; the grab targets the player's current position instead."""
    boss = _boss_ready_to_enrage()
    boss.player_position_locked = True
    hitbox_syncs = []
    player = SimpleNamespace(
        rect=pygame.Rect(300, 200, 40, 30),
        sync_hitbox=lambda: hitbox_syncs.append(True),
    )

    boss._trigger_enrage_if_needed(None, player)

    assert boss._state.enraged is True
    assert (player.rect.x, player.rect.y) == (300, 200)
    assert boss._state.enrage_snapshot_target == (320.0, 215.0)  # player center
    assert not hitbox_syncs  # rect untouched → no hitbox re-sync


def test_enrage_trigger_centers_player_when_position_unlocked():
    """P1-A: default behavior (not docked) still drags the player to
    the screen center and re-syncs the hitbox."""
    boss = _boss_ready_to_enrage()
    hitbox_syncs = []
    player = SimpleNamespace(
        rect=pygame.Rect(300, 200, 40, 30),
        sync_hitbox=lambda: hitbox_syncs.append(True),
    )

    boss._trigger_enrage_if_needed(None, player)

    assert boss._state.enraged is True
    assert player.rect.centerx == get_screen_width() // 2
    assert player.rect.centery == get_screen_height() // 2
    assert boss._state.enrage_snapshot_target == (get_screen_width() / 2, get_screen_height() / 2)
    assert hitbox_syncs


def test_is_enrage_engaged_predicate():
    """P1-B: the public predicate the mothership integrator consults must
    be False before the trigger and True once the grab sequence starts."""
    boss = _boss_ready_to_enrage()
    assert boss.is_enrage_engaged() is False

    player = SimpleNamespace(
        rect=pygame.Rect(300, 200, 40, 30),
        sync_hitbox=lambda: None,
    )
    boss._trigger_enrage_if_needed(None, player)

    assert boss.is_enrage_engaged() is True
