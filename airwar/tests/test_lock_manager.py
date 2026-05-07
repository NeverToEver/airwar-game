from types import SimpleNamespace

import pytest

from airwar.game.systems.lock_manager import LockLayer, LockManager, LockRequest


HOMECOMING_LOCK_TIMER = 999999


def _make_subject():
    game_state = SimpleNamespace(
        player_invincible=False,
        invincibility_timer=0,
        silent_invincible=False,
        paused=False,
    )
    player = SimpleNamespace(controls_locked=False)
    return LockManager(game_state, player), game_state, player


def test_single_system_acquire_and_release() -> None:
    manager, game_state, player = _make_subject()

    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(
            invincible=True,
            lock_controls=True,
            paused=True,
            silent_invincible=True,
            invincibility_duration=HOMECOMING_LOCK_TIMER,
        ),
    )

    assert manager.is_locked(LockLayer.HOMECOMING) is True
    assert manager.has_locks() is True
    assert game_state.player_invincible is True
    assert game_state.invincibility_timer == HOMECOMING_LOCK_TIMER
    assert game_state.silent_invincible is True
    assert game_state.paused is True
    assert player.controls_locked is True

    manager.release(LockLayer.HOMECOMING)

    assert manager.is_locked(LockLayer.HOMECOMING) is False
    assert manager.has_locks() is False
    assert game_state.player_invincible is False
    assert game_state.invincibility_timer == 0
    assert game_state.silent_invincible is False
    assert game_state.paused is False
    assert player.controls_locked is False


def test_higher_priority_layer_overrides_lower_priority_invincibility_mode() -> None:
    manager, game_state, _player = _make_subject()

    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, silent_invincible=True, invincibility_duration=1200),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(invincible=True, silent_invincible=False, invincibility_duration=900),
    )

    assert game_state.player_invincible is True
    assert game_state.silent_invincible is False
    assert game_state.invincibility_timer == 900

    manager.release(LockLayer.HOMECOMING)

    assert game_state.player_invincible is True
    assert game_state.silent_invincible is True
    assert game_state.invincibility_timer == 1200


def test_homecoming_release_preserves_mothership_lock() -> None:
    manager, game_state, player = _make_subject()
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(
            invincible=True,
            lock_controls=True,
            silent_invincible=True,
            invincibility_duration=1200,
        ),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(
            invincible=True,
            lock_controls=True,
            paused=True,
            silent_invincible=True,
            invincibility_duration=HOMECOMING_LOCK_TIMER,
        ),
    )

    manager.release(LockLayer.HOMECOMING)

    assert manager.is_locked(LockLayer.MOTHERSHIP) is True
    assert game_state.player_invincible is True
    assert game_state.invincibility_timer == 1200
    assert game_state.silent_invincible is True
    assert game_state.paused is False
    assert player.controls_locked is True


def test_lock_layer_priority_order_is_explicit() -> None:
    assert list(sorted(LockLayer, reverse=True)) == [
        LockLayer.HOMECOMING,
        LockLayer.MOTHERSHIP,
        LockLayer.BOSS_ENRAGE,
        LockLayer.PHASE_DASH,
        LockLayer.GIVE_UP,
    ]


@pytest.mark.parametrize("winner", list(LockLayer))
def test_each_lock_layer_can_win_invincibility_mode_by_priority(winner: LockLayer) -> None:
    manager, game_state, _player = _make_subject()
    for layer in LockLayer:
        if layer.value > winner.value:
            continue
        duration = int(layer.value)
        manager.acquire(
            layer,
            LockRequest(
                invincible=True,
                silent_invincible=layer is not winner,
                invincibility_duration=duration,
            ),
        )

    assert game_state.player_invincible is True
    assert game_state.silent_invincible is False
    assert game_state.invincibility_timer == winner.value


def test_all_lock_layers_combine_independent_state_flags() -> None:
    manager, game_state, player = _make_subject()

    manager.acquire(LockLayer.GIVE_UP, LockRequest(paused=True))
    manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True, invincibility_duration=40))
    manager.acquire(LockLayer.BOSS_ENRAGE, LockRequest(lock_controls=True))
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, lock_controls=True, silent_invincible=True, invincibility_duration=1200),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(invincible=True, paused=True, silent_invincible=False, invincibility_duration=900),
    )

    assert game_state.player_invincible is True
    assert game_state.invincibility_timer == 900
    assert game_state.silent_invincible is False
    assert game_state.paused is True
    assert player.controls_locked is True

    manager.clear()

    assert game_state.player_invincible is False
    assert game_state.invincibility_timer == 0
    assert game_state.silent_invincible is False
    assert game_state.paused is False
    assert player.controls_locked is False


def test_transient_state_can_apply_short_invincibility_without_registering_lock() -> None:
    manager, game_state, player = _make_subject()
    player.controls_locked = True

    manager.apply_transient_state(
        paused=False,
        invincible=True,
        invincibility_duration=120,
        silent_invincible=False,
    )

    assert manager.has_locks() is False
    assert game_state.paused is False
    assert game_state.player_invincible is True
    assert game_state.invincibility_timer == 120
    assert game_state.silent_invincible is False
    assert player.controls_locked is True
