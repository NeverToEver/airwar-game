"""Phase 4 god-class split: collision event publication + player-hit handler.

Extracted from ``CollisionController``. Owns:

* The ``CollisionEvent`` dataclass used for the public ``events`` snapshot.
* A factory for the ``player_hit`` callback closure that fans damage and
  the optional ``clear_bullets`` hook out to the supplied callables.

The dispatcher is intentionally lightweight — it does not own the
``_events`` list itself; that lives on the parent ``CollisionController``
so backward-compat callers (and tests that read ``controller.events``) keep
working unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from airwar.entities.player import Player


@dataclass
class CollisionEvent:
    """Collision event dataclass — callback registration for collision handling.

    Public API kept identical to the legacy ``CollisionController.CollisionEvent``
    so any consumer reading ``controller.events`` after ``check_all_collisions``
    sees no change.
    """

    type: str
    source: Any = None
    target: Any = None
    damage: int = 0
    score: int = 0


class CollisionEventDispatcher:
    """Owns the ``player_hit`` callback assembly + ``CollisionEvent`` type.

    The parent ``CollisionController`` keeps the events list and appends to it
    directly (so existing tests that read ``controller.events`` and
    ``controller._events.clear()`` work unchanged). The dispatcher's only
    responsibility is creating the per-frame player-hit handler that fans
    damage + clear-bullets hooks out to the supplied callables.
    """

    @staticmethod
    def make_player_hit_handler(
        player: Player,
        on_player_hit: Callable[[int, Player], None] | None = None,
        on_clear_bullets: Callable | None = None,
    ) -> Callable[[int, Player], None]:
        """Build the per-frame ``player_hit`` callback closure.

        Args:
            player: The player entity hit (used as default target).
            on_player_hit: Optional damage callback (damage, target).
            on_clear_bullets: Optional hook called when a player hit lands.

        Returns:
            Callable[[int, Player], None]: handler that invokes both hooks.
        """

        def handle_player_hit(damage: int, target=None) -> None:
            hit_target = target or player
            if on_player_hit:
                on_player_hit(damage, hit_target)
            if on_clear_bullets:
                on_clear_bullets()

        return handle_player_hit
