"""Property-based tests for LockManager.

Verifies invariants of the lock-arbitration layer:

1. The highest-priority active layer determines the aggregate state
   (invincibility / silent_invincible / paused / lock_controls).
2. ``acquire`` + ``release`` returns the aggregate to the pre-acquire state.
3. ``clear()`` removes every active layer.
4. A freshly-cleared LockManager has no active layers.

The five ``LockLayer`` values are ordered by ``IntEnum`` priority; the
manager iterates ``sorted(self._locks.keys(), reverse=True)`` and uses
the first match for invincibility. Paused/controls are OR'd across all
active layers.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.game.systems.lock_manager import LockLayer, LockManager, LockRequest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_subject():
    """Create a fresh game_state/player/manager triple for one property run."""
    game_state = SimpleNamespace(
        player_invincible=False,
        is_player_invincible=False,
        invincibility_timer=0,
        is_silent_invincible=False,
        is_paused=False,
    )
    player = SimpleNamespace(is_controls_locked=False)
    return LockManager(game_state, player), game_state, player


all_layers = st.sampled_from(list(LockLayer))
layer_lists = st.lists(all_layers, min_size=1, max_size=6, unique=True)
# Subsets of layers (possibly empty).
layer_subsets = st.lists(all_layers, max_size=6, unique=True)


# ---------------------------------------------------------------------------
# Property 1: highest-priority active layer wins invincibility / silent mode.
# ---------------------------------------------------------------------------


@given(layer_lists)
@settings(max_examples=20)
def test_highest_priority_layer_wins_invincibility(active_layers):
    """The aggregate invincible + silent mode match the highest-priority
    active layer's request, not any lower-priority contender.

    IntEnum sorts numerically with the highest priority first; ``reverse=True``
    in ``_recompute`` means the first match in iteration order wins.
    """
    manager, game_state, _player = _make_subject()
    requests: dict[LockLayer, LockRequest] = {}
    for layer in active_layers:
        # Each layer uses a distinct invincibility_duration so we can
        # detect the winner without ambiguity.
        manager.acquire(
            layer,
            LockRequest(
                invincible=True,
                is_silent_invincible=(layer is not active_layers[0]),  # not deterministic
                invincibility_duration=layer.value,
            ),
        )
        requests[layer] = manager._locks[layer]

    # The highest-priority layer is the one with the largest IntEnum value.
    winner = max(active_layers, key=lambda layer: layer.value)
    winner_req = requests[winner]

    assert game_state.is_player_invincible is True
    assert game_state.is_silent_invincible == winner_req.is_silent_invincible
    assert game_state.invincibility_timer == winner_req.invincibility_duration


# ---------------------------------------------------------------------------
# Property 2: acquire + release returns aggregate to pre-acquire state.
# ---------------------------------------------------------------------------


@given(all_layers)
@settings(max_examples=20)
def test_acquire_release_round_trip(layer):
    """Acquiring then releasing a single layer must return the manager
    to its pre-acquire aggregate state.
    """
    manager, game_state, player = _make_subject()

    # Capture the pre-acquire snapshot.
    pre_state = (
        game_state.is_player_invincible,
        game_state.is_silent_invincible,
        game_state.is_paused,
        game_state.invincibility_timer,
        player.is_controls_locked,
    )

    manager.acquire(
        layer,
        LockRequest(
            invincible=True,
            lock_controls=True,
            is_paused=True,
            is_silent_invincible=True,
            invincibility_duration=999,
        ),
    )
    # Confirm the lock actually applied.
    assert manager.is_locked(layer) is True
    assert game_state.is_player_invincible is True

    manager.release(layer)

    post_state = (
        game_state.is_player_invincible,
        game_state.is_silent_invincible,
        game_state.is_paused,
        game_state.invincibility_timer,
        player.is_controls_locked,
    )
    assert post_state == pre_state
    assert manager.is_locked(layer) is False


# ---------------------------------------------------------------------------
# Property 3: clear() removes every active layer.
# ---------------------------------------------------------------------------


@given(layer_subsets)
@settings(max_examples=20)
def test_clear_removes_all_active_layers(layers):
    """After clear(), is_locked() must be False for every layer and
    has_locks() must be False.
    """
    manager, game_state, player = _make_subject()
    for layer in layers:
        manager.acquire(
            layer,
            LockRequest(invincible=True, lock_controls=True, invincibility_duration=100),
        )

    if layers:
        assert manager.has_locks() is True

    manager.clear()

    assert manager.has_locks() is False
    for layer in LockLayer:
        assert manager.is_locked(layer) is False
    assert game_state.is_player_invincible is False
    assert game_state.is_paused is False
    assert game_state.is_silent_invincible is False
    assert player.is_controls_locked is False


# ---------------------------------------------------------------------------
# Property 4: a freshly-instantiated LockManager has no active layers.
# ---------------------------------------------------------------------------


def test_fresh_lock_manager_has_no_active_layers() -> None:
    """A brand-new LockManager exposes no locks and reports empty state."""
    manager, _game_state, _player = _make_subject()
    assert manager.has_locks() is False
    for layer in LockLayer:
        assert manager.is_locked(layer) is False


# ---------------------------------------------------------------------------
# Property 5: priority order is fixed (regression guard for IntEnum values).
# ---------------------------------------------------------------------------


def test_lock_layer_priority_order_is_stable() -> None:
    """Pinned: HOMECOMING(100) > MOTHERSHIP(80) > BOSS_ENRAGE(60) >
    PHASE_DASH(40) > GIVE_UP(20) > GAME_PAUSE(10).
    """
    assert sorted(LockLayer, reverse=True) == [
        LockLayer.HOMECOMING,
        LockLayer.MOTHERSHIP,
        LockLayer.BOSS_ENRAGE,
        LockLayer.PHASE_DASH,
        LockLayer.GIVE_UP,
        LockLayer.GAME_PAUSE,
    ]


# ---------------------------------------------------------------------------
# Property 6: paused and lock_controls are OR-aggregated across all active
# layers (independent of priority).
# ---------------------------------------------------------------------------


@given(
    st.booleans(),
    st.booleans(),
    st.sampled_from(list(LockLayer)),
)
@settings(max_examples=20)
def test_paused_and_controls_are_or_aggregated(paused_flag, controls_flag, layer):
    """is_paused and is_controls_locked are OR-aggregated across all
    active layers regardless of priority ordering.
    """
    manager, game_state, player = _make_subject()
    manager.acquire(
        layer,
        LockRequest(invincible=False, is_paused=paused_flag, lock_controls=controls_flag),
    )
    assert game_state.is_paused == paused_flag
    assert player.is_controls_locked == controls_flag
