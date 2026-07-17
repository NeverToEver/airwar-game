"""Bullet manager module.

Unified management of player and enemy bullet updates, cleanup, and state sync.
Separates bullet-related operations from GameScene.

Design principles:
- Single responsibility: Bullet lifecycle management only.
- Dependency injection: Dependencies received via constructor.
- Facade pattern: Unified bullet operation entry point.
- Composition over inheritance: Coordinates different bullet types.

Usage:
    from airwar.game.managers import BulletManager

    bullet_manager = BulletManager(player, spawn_controller)
    bullet_manager.update_all()
"""

import struct
from typing import Any

from airwar.config import get_screen_height, get_screen_width
from airwar.core_bindings import batch_update_bullets_buf

from ..protocols import PlayerProtocol, SpawnControllerProtocol


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
        self._batch_bullet_data: list[Any] = []
        self._batch_bullet_map: dict[int, Any] = {}

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
        self._update_bullets_batch(self._player.get_bullets(), cleanup)
        if cleanup:
            self._player.cleanup_inactive_bullets()

    def _update_enemy_bullets(self, cleanup: bool) -> None:
        """Update enemy bullets.

        Args:
            cleanup: Whether to remove inactive bullets after update.
        """
        self._update_bullets_batch(self._spawn_controller.enemy_bullets, cleanup)
        if cleanup:
            self._cleanup_enemy_bullets()

    # Binary buffer format: Q(id) + f(x) + f(y) + f(vx) + f(vy) + B(is_laser) + xxx(pad) + f(screen_h) = 32 bytes
    _BULLET_BUF_FMT = "<QffffBxxxf"
    _BULLET_BUF_SIZE = struct.calcsize(_BULLET_BUF_FMT)

    def _update_bullets_batch(self, bullets: list, cleanup: bool) -> None:
        """Batch update bullets via core_bindings (Rust extension or Python fallback).

        Handles position updates in the batch backend, then applies results
        back. Off-screen culling uses ``OFFSCREEN_MARGIN`` on all four sides
        (see the boundary check below); the backend's own vertical check is
        only an early-out hint. For laser bullets, the trail is maintained
        in Python after applying the new position.

        Uses binary buffer FFI for reduced overhead.

        Args:
            bullets: List of bullet entities
            cleanup: Whether to remove inactive bullets
        """
        if not bullets:
            return

        bullet_map = self._batch_bullet_map
        bullet_map.clear()
        screen_w = float(get_screen_width())
        screen_h = float(get_screen_height())

        # Pack bullets into binary buffer; cache data/laser flag/margin to avoid
        # repeated getattr in the apply-results loop.
        for bullet in bullets:
            if not bullet.active:
                continue
            self._update_release_delay(bullet)
            if getattr(bullet, "held", False):
                continue
            data = getattr(bullet, "data", None)
            if data is None:
                continue
            is_laser = getattr(data, "bullet_type", "") == "laser" or getattr(data, "is_laser", False)
            margin = float(getattr(bullet, "OFFSCREEN_MARGIN", 80))
            bullet_map[id(bullet)] = (bullet, data, is_laser, margin)

        if not bullet_map:
            return

        count = len(bullet_map)
        buf = bytearray(count * self._BULLET_BUF_SIZE)
        fmt = self._BULLET_BUF_FMT
        size = self._BULLET_BUF_SIZE
        for i, (bullet, _data, is_laser, _margin) in enumerate(bullet_map.values()):
            struct.pack_into(
                fmt,
                buf,
                i * size,
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
            entry = bullet_map.get(bullet_id)
            if entry is None:
                continue
            bullet, data, is_laser, margin = entry

            # Update position
            bullet.rect.x = new_x
            bullet.rect.y = new_y

            # Handle laser trail (still needs Python for pygame operations)
            if is_laser:
                bullet._trail.append(
                    (
                        bullet.rect.x,
                        bullet.rect.y,
                        bullet.rect.width,
                        bullet.rect.height,
                    )
                )

            # Update active state
            r = bullet.rect
            if not is_active or (
                r.right < -margin
                or r.left > screen_w + margin
                or r.bottom < -margin
                or r.top > screen_h + margin
            ):
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
        if direction is None:
            # Keep the bullet held until a valid release direction is available.
            return
        # ``enrage_release_speed`` defaults to 0.0 when a spawn path never set
        # it; fall back to the bullet's base speed so it never hovers forever.
        bullet.velocity = direction * (bullet.enrage_release_speed or bullet.data.speed)
        bullet.held = False
        bullet.enrage_release_pending = False

    def _cleanup_enemy_bullets(self) -> None:
        """Remove inactive bullets from the enemy bullet list."""
        bullets = self._spawn_controller.enemy_bullets
        if not bullets:
            return
        # Fast path: skip allocation if all bullets are active (most frames)
        if not any(not b.active for b in bullets):
            return
        self._spawn_controller.enemy_bullets[:] = [b for b in bullets if b.active]
