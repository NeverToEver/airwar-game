"""Tests for airwar.game.managers.game_controller."""

from __future__ import annotations

from types import SimpleNamespace

from airwar.game.managers.game_controller import GameController, GameplayState


def test_update_invincibility_does_not_decrement_hit_stop() -> None:
    """hit_stop_timer must only be decremented by GameSceneUpdater step 0."""
    state = SimpleNamespace(
        gameplay_state=GameplayState.PLAYING,
        hit_stop_timer=4,
        is_player_invincible=False,
        invincibility_timer=0,
        damage_intensity=0.0,
    )
    gc = GameController.__new__(GameController)
    gc.state = state
    gc._player_ref = None

    gc._update_invincibility()

    assert state.hit_stop_timer == 4


def test_update_does_not_decrement_hit_stop() -> None:
    """The public update() path must not tick hit_stop_timer."""
    gc = GameController("medium", "Player")
    gc.state.hit_stop_timer = 4
    gc.state.gameplay_state = GameplayState.PLAYING
    player = SimpleNamespace(health=100, max_health=100)

    gc.update(player)

    assert gc.state.hit_stop_timer == 4
