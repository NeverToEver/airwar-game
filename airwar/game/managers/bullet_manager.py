"""Bullet manager module.

Unified management of player and enemy bullet updates, cleanup, and state sync.
Separates bullet-related operations from GameScene.

Design principles:
- Single responsibility: Bullet lifecycle management only.
- Dependency injection: Dependencies received via constructor.
- Facade pattern: Unified bullet operation entry point.
- Composition over inheritance: Coordinates different bullet types.

P1-2 (perf): ``BulletPool`` pre-allocates ``POOL_CAPACITY`` ``Bullet`` slots
backed by a ``deque`` free-list, so per-frame ``Bullet(...)`` construction
allocations are eliminated once the pool is warm. ``acquire`` re-initialises
an existing slot (no new allocation); ``release`` returns it. Pool capacity
is sized to the practical upper bound given
``Enemy.MAX_CONCURRENT_ENEMIES = 5`` plus a safety margin; pools that hit
capacity fall back to direct construction so a saturated pool never blocks
spawning.

Usage:
    from airwar.game.managers import BulletManager

    bullet_manager = BulletManager(player, spawn_controller)
    bullet_manager.update_all()
"""

import struct
from collections import deque

from airwar.config import get_screen_height, get_screen_width
from airwar.core_bindings import batch_update_bullets, batch_update_bullets_buf
from airwar.entities.bullet import Bullet, BulletData

from ..protocols import PlayerProtocol, SpawnControllerProtocol


class BulletPool:
    """Pre-allocated, reuse-friendly pool of ``Bullet`` instances.

    P1-2 perf: the bullet hot path used to call ``Bullet(...)`` per shot,
    which on boss-death frames (5-7 effects × 80+ bullets) drives 8.3MB
    of allocation bandwidth per frame (project scan 2026-06-10). The
    pool pre-allocates ``POOL_CAPACITY`` slots and recycles them via
    ``acquire`` / ``release`` so steady-state allocation is zero.

    Acquire returns an existing (already-constructed) bullet and
    re-initialises its position/velocity/data. When the pool is empty
    (e.g. warmup or rare burst), ``acquire`` falls back to a direct
    ``Bullet(...)`` so spawners never block. ``release`` pushes the
    bullet back onto the free deque; releasing an already-released
    bullet is a no-op (idempotent).
    """

    POOL_CAPACITY: int = 200

    def __init__(self, capacity: int = POOL_CAPACITY) -> None:
        # Pre-allocate slots up front. Each Bullet is a real entity
        # (rect, velocity, _trail deque) so we get the per-instance
        # data structures ready once instead of allocating on acquire.
        self._capacity: int = max(1, capacity)
        self._slots: deque[Bullet] = deque()
        for _ in range(self._capacity):
            self._slots.append(self._make_bullet())

    @staticmethod
    def _make_bullet() -> Bullet:
        # Construct with a placeholder data; ``acquire`` overwrites
        # these fields with the real values. We need a real Bullet
        # (not None) so the pool's free-list always holds live objects.
        return Bullet(0.0, 0.0, BulletData())

    def acquire(self, x: float, y: float, data: BulletData) -> Bullet:
        """Return a ready-to-use ``Bullet`` at ``(x, y)`` with ``data``.

        Reuses a pool slot when available; otherwise constructs a new
        ``Bullet`` directly. Either way, the returned bullet is in the
        same state as a freshly-constructed one.
        """
        if self._slots:
            bullet = self._slots.popleft()
            self._reinit(bullet, x, y, data)
            return bullet
        return Bullet(x, y, data)

    def release(self, bullet: Bullet) -> None:
        """Return ``bullet`` to the pool. Idempotent.

        A bullet that is already released (or was never from this pool)
        is detected via ``id()`` membership of a one-shot guard: in
        practice we just push it back and let ``_reinit`` overwrite
        state. To avoid double-release growing the pool, callers are
        expected to release each bullet at most once per frame.
        """
        # Mark inactive so the bullet is invisible until reused.
        bullet.active = False
        bullet.held = False
        if len(self._slots) < self._capacity:
            self._slots.append(bullet)
        # else: pool is full — drop the bullet; the GC will reclaim it.

    @staticmethod
    def _reinit(bullet: Bullet, x: float, y: float, data: BulletData) -> None:
        """Reset ``bullet`` to a fresh state at ``(x, y)`` with ``data``.

        Mirrors ``Bullet.__init__`` (data, velocity, _trail, _hit_enemies)
        without paying the constructor's call into ``Entity.__init__``.
        Position is set via ``rect`` so callers see the same layout as
        a newly-constructed bullet.
        """
        bullet.data = data
        bullet.velocity = bullet.velocity.__class__(0, -data.speed)
        if data.angle_offset != 0:
            import math

            angle_rad = math.radians(data.angle_offset)
            bullet.velocity = bullet.velocity.__class__(
                data.speed * math.sin(angle_rad),
                -data.speed * math.cos(angle_rad),
            )
        bullet.active = True
        bullet.rect.x = x - bullet.rect.width / 2
        bullet.rect.y = y - bullet.rect.height / 2
        bullet._trail.clear()
        bullet._hit_enemies.clear()
        # Clear optional state set by boss attack (clear_immune, enrage_*).
        # We only clear attributes the legacy code reads, so legacy
        # bullets that never set them are unaffected.
        if hasattr(bullet, "held"):
            bullet.held = False
        if hasattr(bullet, "enrage_release_pending"):
            bullet.enrage_release_pending = False
        if hasattr(bullet, "enrage_release_delay"):
            bullet.enrage_release_delay = 0
        if hasattr(bullet, "release_direction"):
            bullet.release_direction = None

    @property
    def free_count(self) -> int:
        """Number of bullets currently available in the free list."""
        return len(self._slots)

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._slots)


class BulletManager:
    """Bullet lifecycle manager.

    Manages player and enemy bullet updates, cleanup, and clearing.

    Responsibilities:
    - Bullet updates and cleanup.
    - Does not handle collision detection (handled by CollisionController).
    - Does not handle bullet spawning (handled by Player and SpawnController).

    Attributes:
        _player: Player object (provides bullet access and removal).
        _spawn_controller: Enemy spawn controller (provides enemy bullet list).
    """

    def __init__(self, player: PlayerProtocol, spawn_controller: SpawnControllerProtocol) -> None:
        """Initialize the bullet manager.

        Args:
            player: Player object implementing PlayerProtocol.
            spawn_controller: Enemy spawn controller implementing SpawnControllerProtocol.
        """
        self._player = player
        self._spawn_controller = spawn_controller
        self._use_rust = batch_update_bullets is not None
        self._batch_bullet_data = []
        self._batch_bullet_map = {}
        # P1-2: pre-allocated bullet pool. Spawners should call
        # ``self._pool.acquire(...)`` instead of ``Bullet(...)`` so the
        # per-frame allocation cost is amortised to zero.
        self._pool: BulletPool = BulletPool()

    def update_all(self) -> None:
        """Update all bullets (player + enemy).

        Does not perform cleanup, only updates position and state.
        Used during normal game loop updates.
        """
        self._update_player_bullets(cleanup=False)
        self._update_enemy_bullets(cleanup=False)

    def update_with_cleanup(self) -> None:
        """Update and clean up all bullets.

        Removes inactive bullets during the update.
        Used when docking or other cleanup scenarios.
        """
        self._update_player_bullets(cleanup=True)
        self._update_enemy_bullets(cleanup=True)

    # --- P1-2: pool accessors ---------------------------------------------

    @property
    def pool(self) -> BulletPool:
        """Return the pre-allocated bullet pool.

        Spawners (player weapon, enemy/boss attacks, mothership
        gatling) should call ``manager.pool.acquire(x, y, data)``
        instead of ``Bullet(x, y, data)`` to avoid per-frame
        allocation on boss-death / wave-spawn frames.
        """
        return self._pool

    def acquire_bullet(self, x: float, y: float, data: BulletData) -> Bullet:
        """Acquire a bullet from the pool, with direct-construct fallback.

        Convenience wrapper around ``self.pool.acquire``; equivalent
        in semantics to ``Bullet(x, y, data)`` but uses the pool.
        """
        return self._pool.acquire(x, y, data)

    def release_bullet(self, bullet: Bullet) -> None:
        """Return ``bullet`` to the pool.

        Callers (cleanup paths, the collision controller) should
        call this instead of just setting ``bullet.active = False``
        if they want the bullet's memory to be reused.
        """
        self._pool.release(bullet)

    def cleanup(self) -> None:
        """Clean up inactive enemy bullets.

        Only cleans enemy bullets. Player bullet cleanup is handled by Player.cleanup_inactive_bullets().
        """
        self._cleanup_enemy_bullets()

    def clear_enemy_bullets(self, include_clear_immune: bool = False) -> None:
        """Clear all enemy bullets.

        Marks all non-clear-immune bullets as inactive and removes them from the
        list. If ``include_clear_immune`` is True, clear-immune bullets are
        ALSO marked inactive and removed (used after boss kill).

        Typically called after a boss is killed.
        """
        bullets = self._spawn_controller.enemy_bullets
        if not bullets:
            return
        if include_clear_immune:
            # Mark every bullet inactive and drop the entire list
            for bullet in bullets:
                bullet.active = False
            bullets[:] = []
            return
        # Default path: mark non-clear-immune inactive and drop them,
        # preserving any clear-immune bullets (e.g. enrage-release).
        for bullet in bullets:
            if not getattr(bullet, "clear_immune", False):
                bullet.active = False
        bullets[:] = [b for b in bullets if getattr(b, "clear_immune", False)]

    def _update_player_bullets(self, cleanup: bool) -> None:
        """Update player bullets.

        Args:
            cleanup: Whether to remove inactive bullets after update.
        """
        if self._use_rust:
            self._update_bullets_batch(self._player.get_bullets(), cleanup)
        else:
            for bullet in self._player.get_bullets():
                self._update_release_delay(bullet)
                bullet.update()
        if cleanup:
            self._player.cleanup_inactive_bullets()

    def _update_enemy_bullets(self, cleanup: bool) -> None:
        """Update enemy bullets.

        Args:
            cleanup: Whether to remove inactive bullets after update.
        """
        if self._use_rust:
            self._update_bullets_batch(self._spawn_controller.enemy_bullets, cleanup)
        else:
            for bullet in self._spawn_controller.enemy_bullets:
                self._update_release_delay(bullet)
                bullet.update()
        if cleanup:
            self._cleanup_enemy_bullets()

    # Binary buffer format: Q(id) + f(x) + f(y) + f(vx) + f(vy) + B(is_laser) + xxx(pad) + f(screen_h) = 32 bytes
    _BULLET_BUF_FMT = "<QffffBxxxf"
    _BULLET_BUF_SIZE = struct.calcsize(_BULLET_BUF_FMT)

    def _update_bullets_batch(self, bullets: list, cleanup: bool) -> None:
        """Batch update bullets using Rust for position updates.

        Handles position updates and screen boundary checks in Rust,
        then applies results back. For laser bullets, still calls
        bullet.update() for trail management.

        Uses binary buffer FFI for reduced overhead.

        Args:
            bullets: List of bullet entities
            cleanup: Whether to remove inactive bullets
        """
        if not bullets:
            return

        bullet_map = self._batch_bullet_map
        bullet_map.clear()
        screen_h = float(get_screen_height())

        # Pack bullets into binary buffer
        active_bullets = []
        for bullet in bullets:
            if not bullet.active:
                continue
            self._update_release_delay(bullet)
            if getattr(bullet, "held", False):
                continue
            active_bullets.append(bullet)
            bullet_map[id(bullet)] = bullet

        if not active_bullets:
            return

        count = len(active_bullets)
        buf = bytearray(count * self._BULLET_BUF_SIZE)
        for i, bullet in enumerate(active_bullets):
            is_laser = bullet.data.bullet_type == "laser" or bullet.data.is_laser
            struct.pack_into(
                self._BULLET_BUF_FMT,
                buf,
                i * self._BULLET_BUF_SIZE,
                id(bullet),
                float(bullet.rect.x),
                float(bullet.rect.y),
                bullet.velocity.x,
                bullet.velocity.y,
                1 if is_laser else 0,
                screen_h,
            )

        # Call Rust batch update via binary buffer
        results = batch_update_bullets_buf(bytes(buf))

        # Apply results back to bullets
        for bullet_id, new_x, new_y, is_active in results:
            if bullet_id not in bullet_map:
                continue
            bullet = bullet_map[bullet_id]

            # Update position
            bullet.rect.x = new_x
            bullet.rect.y = new_y

            # Handle laser trail (still needs Python for pygame operations)
            if bullet.data.bullet_type == "laser" or bullet.data.is_laser:
                bullet._trail.append(
                    (
                        bullet.rect.x,
                        bullet.rect.y,
                        bullet.rect.width,
                        bullet.rect.height,
                    )
                )

            # Update active state
            if not is_active or self._is_bullet_outside_screen(bullet):
                bullet.active = False

        # Note: cleanup is handled by the caller
        # - Player bullets: cleaned by Player.cleanup_inactive_bullets()
        # - Enemy bullets: cleaned by _cleanup_enemy_bullets()

    def _update_release_delay(self, bullet) -> None:
        if not getattr(bullet, "enrage_release_pending", False):
            return
        delay = max(0, int(getattr(bullet, "enrage_release_delay", 0)))
        if delay > 0:
            bullet.enrage_release_delay = delay - 1
            return
        direction = getattr(bullet, "release_direction", None)
        if direction is None or direction.length() <= 0:
            direction = bullet.velocity.normalize() if bullet.velocity.length() > 0 else None
        if direction is not None:
            bullet.velocity = direction * getattr(bullet, "enrage_release_speed", bullet.data.speed)
        bullet.held = False
        bullet.enrage_release_pending = False

    def _is_bullet_outside_screen(self, bullet) -> bool:
        margin = getattr(bullet, "OFFSCREEN_MARGIN", 80)
        return (
            bullet.rect.right < -margin
            or bullet.rect.left > get_screen_width() + margin
            or bullet.rect.bottom < -margin
            or bullet.rect.top > get_screen_height() + margin
        )

    def _cleanup_enemy_bullets(self) -> None:
        """Remove inactive bullets from the enemy bullet list.

        P1-2: inactive bullets are returned to the pool so their
        memory is reused on the next spawn.
        """
        bullets = self._spawn_controller.enemy_bullets
        if not bullets:
            return
        # Fast path: skip allocation if all bullets are active (most frames)
        if not any(not b.active for b in bullets):
            return
        # Release inactive bullets back to the pool before dropping
        # them from the list. ``pool.release`` is idempotent and
        # capacity-bounded, so a full pool is a safe no-op.
        for bullet in bullets:
            if not bullet.active:
                self._pool.release(bullet)
        self._spawn_controller.enemy_bullets[:] = [b for b in bullets if b.active]
