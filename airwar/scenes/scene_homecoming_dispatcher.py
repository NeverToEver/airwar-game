"""F07 god-class split: GameScene homecoming dispatcher.

This module extracts the 8 homecoming-related methods from
``GameScene`` (lines 629-708 in the pre-split file) into a
dedicated dispatcher class. The dispatcher owns the homecoming
coordinator and exposes the same public surface as the legacy
private methods.

Before: GameScene had 8 homecoming methods (80+ lines) that just
        forwarded to the coordinator.
After:  SceneHomecomingDispatcher owns the dispatching logic;
        GameScene has 1-line forwarders for backward compatibility.

47 模糊点 E.T3-T7 (Phase 6 §6.2): the four early-return paths in
``on_requested`` / ``on_complete`` / ``on_orbital_strike`` /
``on_departure_complete`` (and friends) all guard against a
``None`` coordinator. When the coordinator is set, every callback
proceeds normally and the protection lock is acquired through
``coordinator._set_protection`` — no early-return short-circuits
it. The ammo warning timing uses ``ammo_magazine.WARNING_CELL_THRESHOLD``
as the single source of truth (consumed by the magazine UI and
the tutorial renderer). On-requested step ordering matches the
coordinator's contract: hide UI → clear bullets → set protection
lock → start sequence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator


class SceneHomecomingDispatcher:
    """F07 god-class split: dispatches homecoming callbacks.

    Each method corresponds 1:1 with a HomecomingCoordinator method
    but the dispatcher (a) checks that the coordinator exists, and
    (b) binds the GameScene context (game_controller, player, etc.)
    so the coordinator does not have to know about the scene.

    Usage::

        scene._homecoming_dispatcher = SceneHomecomingDispatcher(
            coordinator=coordinator,
            scene=scene,  # for context binding
        )
    """

    def __init__(
        self,
        coordinator: HomecomingCoordinator | None,
        scene: object,
    ) -> None:
        self._coordinator = coordinator
        self._scene = scene

    def _is_active(self) -> bool:
        if self._coordinator is None:
            return False
        return self._coordinator.is_active()

    def _is_locked(self) -> bool:
        if self._coordinator is None:
            return False
        return self._coordinator.is_locked()

    def _is_base_pending(self) -> bool:
        if self._coordinator is None:
            return False
        return self._coordinator.is_base_pending()

    def update(self) -> None:
        """Per-frame homecoming update (coordinator tick)."""
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.update(
            s.game_controller,
            s.player,
            s._lock_manager,
            s._bullet_manager,
            s.spawn_controller,
            s._game_loop_manager,
            s.notification_manager,
        )

    def on_requested(self) -> None:
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.on_requested(
            s.game_controller,
            s.player,
            s._lock_manager,
            s._bullet_manager,
            s.notification_manager,
        )

    def on_complete(self) -> None:
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.on_complete(
            s.game_controller,
            s.player,
            s._lock_manager,
            s.notification_manager,
            s.reward_system,
        )
        # Propagate derived state to scene
        s._homecoming_base_pending = self._coordinator.is_base_pending()
        s._talent_balance_manager = self._coordinator.get_talent_balance_manager()

    def on_orbital_strike(self) -> None:
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.on_orbital_strike(
            s.spawn_controller,
            s._game_loop_manager,
            s.player,
            s.notification_manager,
        )

    def on_departure_complete(self) -> None:
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.on_departure_complete(
            s.game_controller,
            s.player,
            s._lock_manager,
            s.spawn_controller,
            s._game_loop_manager,
            s.notification_manager,
        )
        s._homecoming_base_pending = self._coordinator.is_base_pending()

    def leave_base(self) -> None:
        if self._coordinator is None:
            return
        s = self._scene
        self._coordinator.leave_base(
            s.game_controller,
            s.player,
            s._lock_manager,
            s.spawn_controller,
            s._game_loop_manager,
            s.notification_manager,
        )
        s._homecoming_base_pending = self._coordinator.is_base_pending()
        s._pause_requested = False

    def handle_console_click(self, pos: tuple[int, int]) -> bool:
        if self._coordinator is None:
            return False
        s = self._scene
        return self._coordinator.handle_console_click(
            pos,
            s.game_controller,
            s.player,
            s._lock_manager,
            s.spawn_controller,
            s._game_loop_manager,
            s.notification_manager,
            s.reward_system,
        )

    def coordinator(self) -> HomecomingCoordinator | None:
        """Return the underlying coordinator (read-only)."""
        return self._coordinator


__all__ = ["SceneHomecomingDispatcher"]
