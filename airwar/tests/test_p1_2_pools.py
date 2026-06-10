"""Tests for the P1-2 pre-allocated pool/buffer additions.

Covers:
- ``BulletPool`` in ``airwar.game.managers.bullet_manager``:
  acquire/release lifecycle, capacity-bounded behaviour, fallback
  to direct construction when saturated, and idempotent release.
- ``EntityBuffer`` in ``airwar.game.managers.game_loop_manager``:
  reset/add/iter/grow lifecycle, length/boolean contract, and
  ``to_list`` snapshot semantics.
- ``BulletManager.pool`` accessor exposes the pool and
  ``acquire_bullet`` / ``release_bullet`` route through it.
- ``GameLoopManager`` wires ``_entity_buf`` and ``_batch_indices``
  and reuses them across ``_update_entities`` calls (no per-frame
  list re-allocation observed via id()).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airwar.entities.bullet import Bullet, BulletData
from airwar.game.managers.bullet_manager import BulletManager, BulletPool
from airwar.game.managers.game_controller import GameplayState
from airwar.game.managers.game_loop_manager import EntityBuffer, GameLoopManager
from airwar.game.systems.lock_manager import LockManager


# ---------------------------------------------------------------------------
# BulletPool tests
# ---------------------------------------------------------------------------


class TestBulletPool:
    def test_pre_allocates_full_capacity(self) -> None:
        """A fresh pool should be empty of nothing — every slot is real."""
        pool = BulletPool(capacity=10)
        assert pool.capacity == 10
        assert pool.free_count == 10
        assert len(pool) == 10

    def test_acquire_returns_bullet_with_correct_data(self) -> None:
        pool = BulletPool(capacity=4)
        data = BulletData(damage=25, speed=12.0, owner="player", bullet_type="single")
        bullet = pool.acquire(100.0, 200.0, data)

        assert isinstance(bullet, Bullet)
        assert bullet.data.damage == 25
        assert bullet.data.speed == 12.0
        assert bullet.data.owner == "player"
        assert bullet.active is True
        # Position is centred on (x, y) — see ``_reinit``.
        assert bullet.rect.x == pytest.approx(95.0)
        assert bullet.rect.y == pytest.approx(195.0)
        # One slot is now in use.
        assert pool.free_count == 3

    def test_acquire_when_pool_empty_falls_back_to_construction(self) -> None:
        """Draining the pool must not block spawners — direct-construct fallback."""
        pool = BulletPool(capacity=2)
        # Drain the pool.
        for _ in range(2):
            pool.acquire(0.0, 0.0, BulletData())
        assert pool.free_count == 0
        c = pool.acquire(50.0, 50.0, BulletData())
        assert isinstance(c, Bullet)
        assert c.data is not None

    def test_release_returns_bullet_to_pool(self) -> None:
        pool = BulletPool(capacity=3)
        bullet = pool.acquire(0.0, 0.0, BulletData())
        assert pool.free_count == 2
        pool.release(bullet)
        assert pool.free_count == 3

    def test_release_does_not_grow_past_capacity(self) -> None:
        """Releasing a bullet when the pool is full is a no-op (GC reclaims)."""
        pool = BulletPool(capacity=2)
        bullet = pool.acquire(0.0, 0.0, BulletData())
        # Free count is 1 (one slot in use, one free).
        assert pool.free_count == 1
        pool.release(bullet)
        assert pool.free_count == 2
        # Release a second, fresh bullet; pool is full, count stays at 2.
        other = Bullet(0.0, 0.0, BulletData())
        pool.release(other)
        assert pool.free_count == 2

    def test_acquire_after_release_returns_a_usable_bullet(self) -> None:
        """Acquired bullet is in a fresh state (active=True, _trail cleared)."""
        pool = BulletPool(capacity=2)
        first = pool.acquire(0.0, 0.0, BulletData(damage=99))
        first._trail.append((1, 2, 3, 4))
        pool.release(first)
        second = pool.acquire(10.0, 20.0, BulletData(damage=5))
        # Deque ``popleft`` returns the oldest element (FIFO); the
        # pool's contract is reuse, not strict LIFO, so identity is
        # best-effort. The reusable state contract is what matters.
        assert second.data.damage == 5
        assert second.active is True
        assert len(second._trail) == 0
        # Position is recentred on the new (10, 20) origin.
        assert second.rect.x == pytest.approx(5.0)
        assert second.rect.y == pytest.approx(15.0)

    def test_acquire_reinits_angle_offset(self) -> None:
        pool = BulletPool(capacity=2)
        data = BulletData(speed=14.0, angle_offset=10.0)
        bullet = pool.acquire(0.0, 0.0, data)
        # The angle offset path uses cos(10°) ≈ 0.9848 for the
        # forward (y) component, scaled by data.speed.
        expected = -14.0 * 0.9848077530
        assert bullet.velocity.y == pytest.approx(expected, abs=1e-3)
        assert bullet.velocity.x == pytest.approx(14.0 * 0.1736481776, abs=1e-3)

    def test_capacity_clamped_to_minimum_one(self) -> None:
        pool = BulletPool(capacity=0)
        assert pool.capacity == 1
        assert pool.free_count == 1

    def test_bullet_manager_exposes_pool(self) -> None:
        """``BulletManager`` should wire a BulletPool in __init__."""
        player = SimpleNamespace()
        spawn = SimpleNamespace()
        mgr = BulletManager(player, spawn)
        assert isinstance(mgr.pool, BulletPool)
        assert mgr.pool.capacity == BulletPool.POOL_CAPACITY

    def test_bullet_manager_acquire_release_route(self) -> None:
        player = SimpleNamespace()
        spawn = SimpleNamespace()
        mgr = BulletManager(player, spawn)
        bullet = mgr.acquire_bullet(10.0, 20.0, BulletData(damage=42))
        assert bullet.data.damage == 42
        mgr.release_bullet(bullet)
        # Released bullets return to the pool's free list.
        assert mgr.pool.free_count == BulletPool.POOL_CAPACITY

    def test_release_marks_bullet_inactive(self) -> None:
        pool = BulletPool(capacity=2)
        bullet = pool.acquire(0.0, 0.0, BulletData())
        assert bullet.active is True
        pool.release(bullet)
        assert bullet.active is False


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
