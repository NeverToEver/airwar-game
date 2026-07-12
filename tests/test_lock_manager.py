"""Tests for the layered lock arbitration system."""

import dataclasses
import logging
import time
from types import SimpleNamespace

import pytest

from airwar.game.systems.lock_manager import (
    LockLayer,
    LockLayerConflict,
    LockManager,
    LockRequest,
    LockToken,
)


@pytest.fixture
def game_state():
    return SimpleNamespace(
        is_paused=False,
        is_player_invincible=False,
        invincibility_timer=0,
        is_silent_invincible=False,
    )


@pytest.fixture
def player():
    return SimpleNamespace(is_controls_locked=False)


@pytest.fixture
def manager(game_state, player):
    return LockManager(game_state, player)


class TestLockManagerBasics:
    def test_initial_state(self, manager):
        assert not manager.has_locks()
        assert not manager.is_locked(LockLayer.GAME_PAUSE)

    def test_acquire_applies_invincibility(self, manager, game_state):
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=30),
        )
        assert game_state.is_player_invincible is True
        assert game_state.invincibility_timer == 30
        assert game_state.is_silent_invincible is False

    def test_acquire_applies_control_lock(self, manager, player):
        manager.acquire(
            LockLayer.GAME_PAUSE,
            LockRequest(lock_controls=True),
        )
        assert player.is_controls_locked is True

    def test_acquire_applies_pause(self, manager, game_state):
        manager.acquire(
            LockLayer.GAME_PAUSE,
            LockRequest(is_paused=True),
        )
        assert game_state.is_paused is True

    def test_release_removes_effects(self, manager, game_state, player):
        manager.acquire(
            LockLayer.GAME_PAUSE,
            LockRequest(lock_controls=True, is_paused=True),
        )
        manager.release(LockLayer.GAME_PAUSE)
        assert game_state.is_paused is False
        assert player.is_controls_locked is False
        assert not manager.has_locks()

    def test_clear_removes_all_locks(self, manager, game_state):
        manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True))
        manager.acquire(LockLayer.GAME_PAUSE, LockRequest(is_paused=True))
        manager.clear()
        assert not manager.has_locks()
        assert game_state.is_paused is False
        assert game_state.is_player_invincible is False


class TestLockManagerPriority:
    def test_higher_priority_wins_invincibility(self, manager, game_state):
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=10),
        )
        manager.acquire(
            LockLayer.HOMECOMING,
            LockRequest(invincible=True, invincibility_duration=60),
        )
        assert game_state.invincibility_timer == 60

    def test_lower_priority_does_not_override_invincibility(self, manager, game_state):
        manager.acquire(
            LockLayer.HOMECOMING,
            LockRequest(invincible=True, invincibility_duration=60),
        )
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=10),
        )
        assert game_state.invincibility_timer == 60

    def test_control_lock_combines_across_layers(self, manager, player):
        manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True))
        manager.acquire(LockLayer.GAME_PAUSE, LockRequest(lock_controls=True))
        assert player.is_controls_locked is True

    def test_silent_invincible_from_higher_priority(self, manager, game_state):
        manager.acquire(
            LockLayer.HOMECOMING,
            LockRequest(invincible=True, is_silent_invincible=True),
        )
        assert game_state.is_silent_invincible is True


class TestLockManagerStrict:
    def test_strict_raises_on_conflict(self, manager):
        req = LockRequest(invincible=True)
        manager.acquire_strict(LockLayer.PHASE_DASH, req)
        with pytest.raises(LockLayerConflict):
            manager.acquire_strict(LockLayer.PHASE_DASH, LockRequest(lock_controls=True))

    def test_strict_accepts_identical_request(self, manager):
        req = LockRequest(invincible=True)
        manager.acquire_strict(LockLayer.PHASE_DASH, req)
        # Same request should not raise.
        manager.acquire_strict(LockLayer.PHASE_DASH, req)


class TestLockManagerUpdate:
    def test_acquire_or_update_merges_booleans_and_max_duration(self, manager, game_state, player):
        manager.acquire_or_update(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=10),
        )
        manager.acquire_or_update(
            LockLayer.PHASE_DASH,
            LockRequest(lock_controls=True, invincibility_duration=30),
        )
        assert game_state.is_player_invincible is True
        assert player.is_controls_locked is True


class TestLockManagerSetGameState:
    def test_set_game_state_recomputes(self, manager, game_state):
        manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True))
        new_state = SimpleNamespace(
            is_paused=False,
            is_player_invincible=False,
            invincibility_timer=0,
            is_silent_invincible=False,
        )
        manager.set_game_state(new_state)
        assert new_state.is_player_invincible is True


class TestLockManagerTransient:
    def test_transient_layer_is_lowest_priority(self):
        assert hasattr(LockLayer, "TRANSIENT")
        assert LockLayer.TRANSIENT == 5
        assert min(LockLayer) == LockLayer.TRANSIENT

    def test_transient_state_merges_booleans(self, manager, game_state):
        manager.apply_transient_state(paused=True)
        manager.apply_transient_state(invincible=True, invincibility_duration=30)
        assert game_state.is_paused is True
        assert game_state.is_player_invincible is True
        assert manager.is_locked(LockLayer.TRANSIENT)

    def test_transient_state_release_clears_layer(self, manager, game_state):
        manager.apply_transient_state(paused=True)
        manager.apply_transient_state(paused=False)
        assert game_state.is_paused is False
        assert not manager.is_locked(LockLayer.TRANSIENT)


class TestLockManagerToken:
    def test_acquire_returns_token(self, manager):
        token = manager.acquire(LockLayer.GAME_PAUSE, LockRequest(is_paused=True))
        assert isinstance(token, LockToken)
        assert token.layer is LockLayer.GAME_PAUSE

    def test_release_with_token_succeeds(self, manager, game_state, player):
        token = manager.acquire(
            LockLayer.GAME_PAUSE,
            LockRequest(lock_controls=True, is_paused=True),
        )
        assert manager.release(token) is True
        assert game_state.is_paused is False
        assert player.is_controls_locked is False
        assert not manager.has_locks()

    def test_release_with_layer_logs_warning(self, manager, caplog):
        manager.acquire(LockLayer.GAME_PAUSE, LockRequest(is_paused=True))
        with caplog.at_level(logging.WARNING, logger="airwar.game.systems.lock_manager"):
            manager.release(LockLayer.GAME_PAUSE)
        assert "without token" in caplog.text

    def test_release_with_stale_token_warns_and_ignores(self, manager, game_state, caplog):
        stale_token = manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=10),
        )
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, invincibility_duration=20),
        )
        with caplog.at_level(logging.WARNING, logger="airwar.game.systems.lock_manager"):
            result = manager.release(stale_token)
        assert result is False
        assert manager.is_locked(LockLayer.PHASE_DASH)
        assert game_state.invincibility_timer == 20
        assert "stale" in caplog.text or "mismatched" in caplog.text


class TestLockManagerPriorityArbitration:
    def test_high_priority_control_lock_suppresses_lower(self, manager, player):
        low = manager.acquire(LockLayer.GAME_PAUSE, LockRequest(lock_controls=True))
        high = manager.acquire(LockLayer.PLAYER_HIT, LockRequest(lock_controls=True))
        assert player.is_controls_locked is True
        manager.release(high)
        assert player.is_controls_locked is True
        manager.release(low)
        assert player.is_controls_locked is False

    def test_high_priority_pause_suppresses_lower(self, manager, game_state):
        low = manager.acquire(LockLayer.GAME_PAUSE, LockRequest(is_paused=True))
        high = manager.acquire(LockLayer.HOMECOMING, LockRequest(is_paused=True))
        assert game_state.is_paused is True
        manager.release(high)
        assert game_state.is_paused is True
        manager.release(low)
        assert game_state.is_paused is False

    def test_lower_priority_controls_apply_when_high_does_not_lock(self, manager, player):
        manager.acquire(LockLayer.PHASE_DASH, LockRequest(invincible=True))
        manager.acquire(LockLayer.GAME_PAUSE, LockRequest(lock_controls=True))
        assert player.is_controls_locked is True


class TestLockManagerExpiration:
    def test_expired_lock_is_automatically_removed(self, manager):
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(invincible=True, expires_at=time.monotonic() + 0.01),
        )
        assert manager.is_locked(LockLayer.PHASE_DASH) is True
        time.sleep(0.02)
        manager.refresh()
        assert manager.is_locked(LockLayer.PHASE_DASH) is False

    def test_permanent_lock_not_cleaned(self, manager):
        manager.acquire(
            LockLayer.PHASE_DASH,
            LockRequest(
                invincible=True,
                invincibility_duration=LockManager.PERMANENT_INVINCIBILITY_FRAMES,
            ),
        )
        manager.refresh()
        assert manager.is_locked(LockLayer.PHASE_DASH) is True


class TestLockManagerImmutability:
    def test_acquire_does_not_mutate_request(self, manager):
        req = LockRequest(invincible=True, invincibility_duration=10)
        original = dataclasses.asdict(req)
        manager.acquire(LockLayer.PHASE_DASH, req)
        assert dataclasses.asdict(req) == original

    def test_acquire_or_update_does_not_mutate_request(self, manager):
        req = LockRequest(invincible=True, invincibility_duration=10)
        original = dataclasses.asdict(req)
        manager.acquire_or_update(LockLayer.PHASE_DASH, req)
        assert dataclasses.asdict(req) == original

    def test_acquire_strict_does_not_mutate_request(self, manager):
        req = LockRequest(invincible=True, invincibility_duration=10)
        original = dataclasses.asdict(req)
        manager.acquire_strict(LockLayer.PHASE_DASH, req)
        assert dataclasses.asdict(req) == original
