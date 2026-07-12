"""Tests for Enemy movement/difficulty boundary fixes (batch F10)."""

import pytest

from airwar.entities.enemy.enemy import Enemy, EnemyState
from airwar.entities.base import EnemyData


def test_set_difficulty_speed_multiplier_applies_in_fallback_path():
    """F10: _difficulty_multiplier must affect Python fallback movement."""
    enemy = Enemy(100, 100, EnemyData(enemy_type="aggressive"))
    enemy._state = EnemyState.ACTIVE
    enemy.active_position_x = 100.0
    enemy.active_position_y = 100.0
    base_agg_speed = enemy.agg_speed

    recorded_speeds = []
    original_update = type(enemy._movement_strategy).update

    def _recording_update(strategy, enemy, slow_factor=1.0, player_pos=None):
        recorded_speeds.append(enemy.agg_speed)
        # Keep the original logic but we only need to observe the speed used.
        enemy.agg_timer += enemy.agg_speed
        enemy.sync_rects()

    # Force the Python fallback path for this frame.
    enemy._can_use_rust_movement = lambda: False
    type(enemy._movement_strategy).update = _recording_update
    try:
        enemy.set_difficulty(2.0, 1.0)
        enemy.update(player_pos=(200, 200), slow_factor=1.0)
    finally:
        type(enemy._movement_strategy).update = original_update

    assert len(recorded_speeds) == 1
    # The strategy saw the speed scaled by the difficulty multiplier.
    assert recorded_speeds[0] == pytest.approx(base_agg_speed * 2.0)
    # The original attribute is restored after the update.
    assert enemy.agg_speed == pytest.approx(base_agg_speed)
