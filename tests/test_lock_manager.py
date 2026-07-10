"""Tests for the layered lock arbitration system."""

from types import SimpleNamespace

import pytest

from airwar.game.systems.lock_manager import (
    LockLayer,
    LockLayerConflict,
    LockManager,
    LockRequest,
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
