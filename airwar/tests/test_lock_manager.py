from types import SimpleNamespace

import pytest

from airwar.game.systems.lock_manager import LockLayer, LockLayerConflict, LockManager, LockRequest

# LockManager arbitrates invincibility / control locks across all gameplay
# systems (homecoming, mothership, boss enrage, phase dash, give-up, pause).
# Pure logic, no I/O — include in smoke.
pytestmark = pytest.mark.smoke

HOMECOMING_LOCK_TIMER = 999999


def _make_subject():
    game_state = SimpleNamespace(
        player_invincible=False,
        invincibility_timer=0,
        is_silent_invincible=False,
        is_paused=False,
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
            is_paused=True,
            is_silent_invincible=True,
            invincibility_duration=HOMECOMING_LOCK_TIMER,
        ),
    )

    assert manager.is_locked(LockLayer.HOMECOMING) is True
    assert manager.has_locks() is True
    assert game_state.is_player_invincible is True
    assert game_state.invincibility_timer == HOMECOMING_LOCK_TIMER
    assert game_state.is_silent_invincible is True
    assert game_state.is_paused is True
    assert player.is_controls_locked is True

    manager.release(LockLayer.HOMECOMING)

    assert manager.is_locked(LockLayer.HOMECOMING) is False
    assert manager.has_locks() is False
    assert game_state.is_player_invincible is False
    assert game_state.invincibility_timer == 0
    assert game_state.is_silent_invincible is False
    assert game_state.is_paused is False
    assert player.is_controls_locked is False


def test_higher_priority_layer_overrides_lower_priority_invincibility_mode() -> None:
    manager, game_state, _player = _make_subject()

    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, is_silent_invincible=True, invincibility_duration=1200),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(invincible=True, is_silent_invincible=False, invincibility_duration=900),
    )

    assert game_state.is_player_invincible is True
    assert game_state.is_silent_invincible is False
    assert game_state.invincibility_timer == 900

    manager.release(LockLayer.HOMECOMING)

    assert game_state.is_player_invincible is True
    assert game_state.is_silent_invincible is True
    assert game_state.invincibility_timer == 1200


def test_homecoming_release_preserves_mothership_lock() -> None:
    manager, game_state, player = _make_subject()
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(
            invincible=True,
            lock_controls=True,
            is_silent_invincible=True,
            invincibility_duration=1200,
        ),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(
            invincible=True,
            lock_controls=True,
            is_paused=True,
            is_silent_invincible=True,
            invincibility_duration=HOMECOMING_LOCK_TIMER,
        ),
    )

    manager.release(LockLayer.HOMECOMING)

    assert manager.is_locked(LockLayer.MOTHERSHIP) is True
    assert game_state.is_player_invincible is True
    assert game_state.invincibility_timer == 1200
    assert game_state.is_silent_invincible is True
    assert game_state.is_paused is False
    assert player.is_controls_locked is True


def test_lock_layer_priority_order_is_explicit() -> None:
    assert sorted(LockLayer, reverse=True) == [
        LockLayer.HOMECOMING,
        LockLayer.MOTHERSHIP,
        LockLayer.BOSS_ENRAGE,
        LockLayer.PHASE_DASH,
        LockLayer.GIVE_UP,
        LockLayer.GAME_PAUSE,
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
                is_silent_invincible=layer is not winner,
                invincibility_duration=duration,
            ),
        )

    assert game_state.is_player_invincible is True
    assert game_state.is_silent_invincible is False
    assert game_state.invincibility_timer == winner.value


def test_all_lock_layers_combine_independent_state_flags() -> None:
    manager, game_state, player = _make_subject()

    manager.acquire(LockLayer.GIVE_UP, LockRequest(is_paused=True))
    manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True, invincibility_duration=40))
    manager.acquire(LockLayer.BOSS_ENRAGE, LockRequest(lock_controls=True))
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, lock_controls=True, is_silent_invincible=True, invincibility_duration=1200),
    )
    manager.acquire(
        LockLayer.HOMECOMING,
        LockRequest(invincible=True, is_paused=True, is_silent_invincible=False, invincibility_duration=900),
    )

    assert game_state.is_player_invincible is True
    assert game_state.invincibility_timer == 900
    assert game_state.is_silent_invincible is False
    assert game_state.is_paused is True
    assert player.is_controls_locked is True

    manager.clear()

    assert game_state.is_player_invincible is False
    assert game_state.invincibility_timer == 0
    assert game_state.is_silent_invincible is False
    assert game_state.is_paused is False
    assert player.is_controls_locked is False


def test_transient_state_can_apply_short_invincibility_without_registering_lock() -> None:
    manager, game_state, player = _make_subject()
    player.is_controls_locked = True

    manager.apply_transient_state(
        paused=False,
        invincible=True,
        invincibility_duration=120,
        silent_invincible=False,
    )

    assert manager.has_locks() is False
    assert game_state.is_paused is False
    assert game_state.is_player_invincible is True
    assert game_state.invincibility_timer == 120
    assert game_state.is_silent_invincible is False
    assert player.is_controls_locked is True


# ---------------------------------------------------------------------------
# Same-layer regression tests (M-10)
#
# Pre-M-10, a second `acquire(layer, ...)` on the same layer silently
# overwrote the prior request. These tests pin the post-M-10 contract:
#   * `acquire` still overwrites but logs a debug line (silent bug
#     surface is now observable)
#   * `acquire_strict` raises LockLayerConflict
#   * `acquire_or_update` merges the two requests (booleans OR, duration
#     max)
# ---------------------------------------------------------------------------


def test_same_layer_acquire_logs_but_silently_overwrites(caplog) -> None:
    """A second `acquire(layer, ...)` on an already-locked layer must NOT
    raise — it silently replaces the prior request (legacy behaviour, kept
    for backward compatibility) and emits a `logger.debug` line so the
    overwrite is no longer invisible in production logs.

    Callers that want hard-fail or merge semantics should opt in via
    `acquire_strict` / `acquire_or_update`.
    """
    manager, game_state, _player = _make_subject()
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, invincibility_duration=1200),
    )

    import logging
    with caplog.at_level(logging.DEBUG, logger="airwar.game.systems.lock_manager"):
        manager.acquire(
            LockLayer.MOTHERSHIP,
            LockRequest(lock_controls=True, is_paused=True),
        )

    # The second request fully replaced the first — that's the legacy
    # behaviour we keep for backward compatibility.
    assert manager.is_locked(LockLayer.MOTHERSHIP) is True
    assert game_state.is_player_invincible is False  # overwritten to False
    assert game_state.is_paused is True
    assert game_state.invincibility_timer == 0
    # The overwrite must have been logged at DEBUG level.
    assert any("overwriting prior request" in rec.message for rec in caplog.records)


def test_acquire_strict_raises_on_conflict() -> None:
    manager, _game_state, _player = _make_subject()
    manager.acquire(
        LockLayer.PHASE_DASH,
        LockRequest(invincible=True, invincibility_duration=27),
    )

    with pytest.raises(LockLayerConflict):
        manager.acquire_strict(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=30),
        )


def test_acquire_strict_succeeds_when_request_unchanged() -> None:
    """An identical re-acquire is a no-op (idempotent), not a conflict."""
    manager, _game_state, _player = _make_subject()
    req = LockRequest(invincible=True, invincibility_duration=27)
    manager.acquire(LockLayer.PHASE_DASH, req)
    manager.acquire_strict(LockLayer.PHASE_DASH, req)  # no raise
    assert manager.is_locked(LockLayer.PHASE_DASH) is True


def test_acquire_or_update_merges_booleans_and_keeps_max_duration() -> None:
    manager, game_state, _player = _make_subject()
    manager.acquire(
        LockLayer.MOTHERSHIP,
        LockRequest(invincible=True, invincibility_duration=1200),
    )
    manager.acquire_or_update(
        LockLayer.MOTHERSHIP,
        LockRequest(lock_controls=True, is_paused=True, invincibility_duration=600),
    )

    # Booleans: OR-merged (existing invincible=True kept + new lock_controls
    # and is_paused).
    # Duration: max(1200, 600) = 1200.
    assert game_state.is_player_invincible is True
    assert game_state.invincibility_timer == 1200
    assert game_state.is_paused is True


def test_acquire_or_update_extends_invincibility_duration() -> None:
    """If a new request has a longer invincibility, it must win."""
    manager, game_state, _player = _make_subject()
    manager.acquire(
        LockLayer.PHASE_DASH,
        LockRequest(invincible=True, invincibility_duration=20),
    )
    manager.acquire_or_update(
        LockLayer.PHASE_DASH,
        LockRequest(invincible=True, invincibility_duration=90),
    )

    assert game_state.invincibility_timer == 90


def test_acquire_or_update_with_no_existing_layer_is_plain_acquire() -> None:
    manager, game_state, _player = _make_subject()
    manager.acquire_or_update(
        LockLayer.GAME_PAUSE,
        LockRequest(is_paused=True),
    )
    assert manager.is_locked(LockLayer.GAME_PAUSE) is True
    assert game_state.is_paused is True

