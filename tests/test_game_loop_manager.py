"""Tests for GameLoopManager boundary fixes (batch F4, F6)."""

from types import SimpleNamespace

import pytest

from airwar.game.managers.game_loop_manager import GameLoopManager


def _make_manager_kwargs(missing=None):
    """Return a full set of valid dependencies, optionally omitting one."""
    collision_controller = SimpleNamespace(set_explosion_callback=lambda cb: None)
    kwargs = {
        "game_controller": SimpleNamespace(state=SimpleNamespace(gameplay_state=0)),
        "game_renderer": SimpleNamespace(update_death_animation=lambda: None),
        "spawn_controller": SimpleNamespace(
            enemies=[],
            boss=None,
            enemy_bullets=[],
        ),
        "reward_system": SimpleNamespace(slow_factor=1.0, unlocked_buffs=set()),
        "bullet_manager": SimpleNamespace(update_all=lambda: None),
        "boss_manager": SimpleNamespace(boss=None, update=lambda p: None),
        "collision_controller": collision_controller,
        "lock_manager": SimpleNamespace(),
    }
    if missing is not None:
        kwargs[missing] = None
    return kwargs


@pytest.mark.parametrize(
    "missing",
    [
        "game_controller",
        "game_renderer",
        "spawn_controller",
        "reward_system",
        "bullet_manager",
        "boss_manager",
        "collision_controller",
        "lock_manager",
    ],
)
def test_constructor_rejects_none_dependency(missing):
    """F4: missing dependencies must raise ValueError at construction time."""
    kwargs = _make_manager_kwargs(missing=missing)
    with pytest.raises(ValueError, match=missing):
        GameLoopManager(**kwargs)


def test_update_entities_passes_player_pos_to_enemies():
    """F6: enemy.update receives the player's position as player_pos."""
    captured = []

    class _RecordingEnemy:
        active = True
        is_ready_for_batch_movement = staticmethod(lambda: False)

        def update(self, *args, **kwargs):
            captured.append((args, kwargs))

    enemy = _RecordingEnemy()
    kwargs = _make_manager_kwargs()
    kwargs["spawn_controller"] = SimpleNamespace(enemies=[enemy])

    manager = GameLoopManager(**kwargs)
    player = SimpleNamespace(rect=SimpleNamespace(centerx=123, centery=456))
    manager._update_entities(player)

    assert len(captured) == 1
    args, kwargs = captured[0]
    assert kwargs.get("player_pos") == (123, 456)
