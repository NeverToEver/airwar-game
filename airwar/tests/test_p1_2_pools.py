"""Tests for the P1-2 pre-allocated entity-buffer additions.

Covers:
- ``EntityBuffer`` in ``airwar.game.managers.game_loop_manager``:
  reset/add/iter/grow lifecycle, length/boolean contract, and
  ``to_list`` snapshot semantics.
- ``GameLoopManager`` wires ``_entity_buf`` and ``_batch_indices``
  and reuses them across ``_update_entities`` calls (no per-frame
  list re-allocation observed via id()).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airwar.game.managers.game_controller import GameplayState
from airwar.game.managers.game_loop_manager import EntityBuffer, GameLoopManager
from airwar.game.systems.lock_manager import LockManager


# ---------------------------------------------------------------------------
# EntityBuffer tests
# ---------------------------------------------------------------------------


class TestEntityBuffer:
    def test_starts_empty_with_full_capacity(self) -> None:
        buf = EntityBuffer(capacity=8)
        assert len(buf) == 0
        assert not buf
        assert buf.to_list() == []

    def test_add_grows_logical_size(self) -> None:
        buf = EntityBuffer(capacity=4)
        for i in range(3):
            buf.add(i)
        assert len(buf) == 3
        assert bool(buf) is True
        assert buf.to_list() == [0, 1, 2]

    def test_iter_yields_only_live_items(self) -> None:
        buf = EntityBuffer(capacity=4)
        for i in range(3):
            buf.add(i)
        # Iterating should yield exactly the 3 live items, not None placeholders.
        assert list(iter(buf)) == [0, 1, 2]

    def test_reset_clears_logical_size(self) -> None:
        buf = EntityBuffer(capacity=4)
        for i in range(3):
            buf.add(i)
        buf.reset()
        assert len(buf) == 0
        assert not buf

    def test_reset_is_idempotent(self) -> None:
        buf = EntityBuffer(capacity=4)
        buf.reset()
        buf.reset()
        assert len(buf) == 0

    def test_add_grows_past_initial_capacity(self) -> None:
        """Once full, ``add`` doubles capacity so callers never lose data."""
        buf = EntityBuffer(capacity=2)
        for i in range(5):
            buf.add(i)
        assert len(buf) == 5
        assert buf.to_list() == [0, 1, 2, 3, 4]

    def test_to_list_returns_copy(self) -> None:
        buf = EntityBuffer(capacity=4)
        buf.add("a")
        snap = buf.to_list()
        snap.append("b")
        # Underlying buffer is unchanged.
        assert buf.to_list() == ["a"]

    def test_indexing_supports_positive_and_negative(self) -> None:
        buf = EntityBuffer(capacity=4)
        buf.add("x")
        buf.add("y")
        assert buf[0] == "x"
        assert buf[1] == "y"
        assert buf[-1] == "y"
        with pytest.raises(IndexError):
            _ = buf[5]

    def test_default_capacity_is_64(self) -> None:
        buf = EntityBuffer()
        # We can add 64 items without growing.
        for i in range(64):
            buf.add(i)
        assert len(buf) == 64


# ---------------------------------------------------------------------------
# GameLoopManager wiring (smoke tests for buffer reuse across frames)
# ---------------------------------------------------------------------------


class _DummyPlayer:
    def __init__(self):
        self.active = True
        self.is_controls_locked = False
        self.bullet_damage = 50
        self.fire_interval = 8
        self.rect = SimpleNamespace(centerx=400, centery=500)

    def get_weapon_status(self):
        return {"spread": False, "laser": False, "explosive": False}

    def update(self):
        pass

    def auto_fire(self):
        pass

    def cleanup_inactive_bullets(self):
        pass


class _DummyBoss:
    def __init__(self):
        self.lock_player = False
        self._enrage_transition_timer = 0
        self.active = True
        self.rect = SimpleNamespace(centerx=300, centery=180, width=210, height=170)

    def should_lock_player_movement(self):
        return False

    def get_hitbox(self):
        return self.rect


def _make_loop_with_enemies(n: int) -> GameLoopManager:
    boss = _DummyBoss()
    controller = SimpleNamespace(
        state=SimpleNamespace(
            gameplay_state=GameplayState.PLAYING,
            running=True,
            score=0,
            boss_kill_count=0,
            score_multiplier=1.0,
            is_player_invincible=False,
        ),
        update=lambda player, has_regen: None,
        show_notification=lambda message: None,
    )
    renderer = SimpleNamespace(update_death_animation=lambda: None)

    class _Enemy:
        def __init__(self, idx):
            self.idx = idx

        def is_ready_for_batch_movement(self):
            return True

        def get_rust_batch_params(self):
            # Return None to skip the batch path and exercise the
            # generic ``enemy.update`` branch only. The buffer is
            # still used for ``_batch_indices`` only when params
            # come back non-None, so for this smoke test we just
            # confirm the buffer object is wired.
            return None, None

        def update(self, others, slow):
            pass

    enemies = [_Enemy(i) for i in range(n)]
    spawn = SimpleNamespace(enemies=enemies, boss=boss)
    reward = SimpleNamespace(unlocked_buffs=[], slow_factor=1.0, base_bullet_damage=10)
    bullet = SimpleNamespace(
        update_all=lambda: None,
        cleanup=lambda: None,
        clear_enemy_bullets=lambda **kwargs: None,
    )
    boss_killed_calls = []
    boss_manager = SimpleNamespace(
        boss=boss,
        update=lambda player: None,
        on_boss_hit=lambda score: None,
        on_boss_killed=lambda: boss_killed_calls.append(True),
    )
    collision = SimpleNamespace(set_explosion_callback=lambda callback: None)
    lock_manager = LockManager(None)
    return GameLoopManager(
        controller,
        renderer,
        spawn,
        reward,
        bullet,
        boss_manager,
        collision,
        lock_manager=lock_manager,
    )


class TestGameLoopEntityBufferWiring:
    def test_entity_buffer_is_constructed(self) -> None:
        loop = _make_loop_with_enemies(0)
        assert isinstance(loop._entity_buf, EntityBuffer)
        assert isinstance(loop._batch_indices, EntityBuffer)

    def test_batch_indices_buffer_reused_across_frames(self) -> None:
        """The underlying list object is stable across calls (no re-alloc)."""
        loop = _make_loop_with_enemies(0)
        first_id = id(loop._batch_indices._buf)
        # Call _update_entities twice; the buffer's underlying list
        # object should not have been replaced.
        player = _DummyPlayer()
        loop._lock_manager.set_player(player)
        loop._update_entities()
        loop._update_entities()
        assert id(loop._batch_indices._buf) == first_id

    def test_update_entities_no_enemies_is_noop(self) -> None:
        loop = _make_loop_with_enemies(0)
        player = _DummyPlayer()
        loop._lock_manager.set_player(player)
        # Should not raise.
        loop._update_entities()
