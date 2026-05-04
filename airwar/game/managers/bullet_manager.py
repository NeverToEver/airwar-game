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

from typing import Protocol

# Try to import Rust batch update function
try:
    from airwar.core_bindings import batch_update_bullets, RUST_AVAILABLE
except ImportError:
    batch_update_bullets = None
    RUST_AVAILABLE = False

from ...config import get_screen_height, get_screen_width


class PlayerProtocol(Protocol):
    """Player protocol - defines the bullet-related interface a player must provide."""

    def get_bullets(self) -> list: ...
    def remove_bullet(self, bullet) -> None: ...


class SpawnControllerProtocol(Protocol):
    """Spawn controller protocol - defines the bullet-related interface a spawner must provide."""

    @property
    def enemy_bullets(self) -> list: ...


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

    def __init__(
        self,
        player: PlayerProtocol,
        spawn_controller: SpawnControllerProtocol
    ) -> None:
        """Initialize the bullet manager.

        Args:
            player: Player object implementing PlayerProtocol.
            spawn_controller: Enemy spawn controller implementing SpawnControllerProtocol.
        """
        self._player = player
        self._spawn_controller = spawn_controller
        self._use_rust = RUST_AVAILABLE and batch_update_bullets is not None
        self._batch_bullet_data = []
        self._batch_bullet_map = {}

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

        Marks all enemy bullets as inactive and clears the list.
        Typically called after a boss is killed.
        """
        for bullet in self._spawn_controller.enemy_bullets[:]:
            if getattr(bullet, "clear_immune", False) and not include_clear_immune:
                continue
            bullet.active = False
        self._spawn_controller.enemy_bullets[:] = [
            bullet for bullet in self._spawn_controller.enemy_bullets
            if getattr(bullet, "clear_immune", False) and not include_clear_immune
        ]

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

    def _update_bullets_batch(self, bullets: list, cleanup: bool) -> None:
        """Batch update bullets using Rust for position updates.

        Handles position updates and screen boundary checks in Rust,
        then applies results back. For laser bullets, still calls
        bullet.update() for trail management.

        Args:
            bullets: List of bullet entities
            cleanup: Whether to remove inactive bullets
        """
        if not bullets:
            return

        # Build bullet data for Rust: (id, x, y, vx, vy, bullet_type, is_laser, screen_height)
        # Use object id as unique identifier
        # bullet_type: 0=normal, 1=single, 2=laser (not used in current Rust impl)
        bullet_data = self._batch_bullet_data
        bullet_map = self._batch_bullet_map
        bullet_data.clear()
        bullet_map.clear()
        for _i, bullet in enumerate(bullets):
            if not bullet.active:
                continue
            self._update_release_delay(bullet)
            if getattr(bullet, "held", False):
                continue
            bullet_id = id(bullet)
            vx = bullet.velocity.x
            vy = bullet.velocity.y
            is_laser = bullet.data.bullet_type == "laser" or bullet.data.is_laser
            bullet_data.append((
                bullet_id,
                bullet.rect.x,
                bullet.rect.y,
                vx,
                vy,
                0,  # bullet_type (reserved for future use)
                is_laser,
                float(get_screen_height())
            ))
            bullet_map[bullet_id] = bullet

        if not bullet_data:
            return

        # Call Rust batch update
        results = batch_update_bullets(bullet_data)

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
                bullet._trail.append((
                    bullet.rect.x,
                    bullet.rect.y,
                    bullet.rect.width,
                    bullet.rect.height,
                ))
                if len(bullet._trail) > 8:
                    bullet._trail.pop(0)

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
        """Remove inactive bullets from the enemy bullet list."""
        bullets = self._spawn_controller.enemy_bullets
        if not bullets:
            return
        # Fast path: skip allocation if all bullets are active (most frames)
        if not any(not b.active for b in bullets):
            return
        self._spawn_controller.enemy_bullets[:] = [b for b in bullets if b.active]
