"""F07 god-class split: Mothership event hub.

This module extracts the 14+ event subscriptions from
``GameIntegrator.__init__`` into a dedicated hub class. The
GameIntegrator keeps a thin facade (the public API) but delegates
event handling to this hub.

Before: GameIntegrator.__init__ had 51 lines and 14 subscribe() calls.
After:  GameIntegrator.__init__ is 8 lines; this module owns the
        subscription table and handler dispatch.

Backward compatibility: GameIntegrator still has the
``_register_handlers()`` method (now a 1-line forwarder) so any
external caller that calls it still works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_integrator import GameIntegrator


# Event-to-handler subscription table. Each entry maps an event
# constant name to the bound method that handles it. Building this as
# a data structure makes the subscription list auditable and easy to
# diff (vs. 14+ inline ``bus.subscribe(EVENT_X, self._on_x)`` calls).
HANDLER_BINDINGS: list[tuple[str, str]] = [
    ("EVENT_STATE_CHANGED", "_on_state_changed"),
    ("EVENT_GAME_RESUME", "_on_game_resume"),
    ("EVENT_START_ENTERING_ANIMATION", "_on_start_entering_animation"),
    ("EVENT_START_DOCKING_ANIMATION", "_on_start_docking_animation"),
    ("EVENT_UNDOCK_CANCELLED", "_on_undock_cancelled"),
    ("EVENT_START_UNDOCKING_ANIMATION", "_on_start_undocking_animation"),
    ("EVENT_COOLDOWN_STARTED", "_on_cooldown_started"),
    ("EVENT_STAY_STARTED", "_on_stay_started"),
    ("EVENT_UNDOCK_REQUESTED", "_on_undock_requested"),
    ("EVENT_EXIT_STARTED", "_on_exit_started"),
    ("EVENT_EXIT_PROGRESS_UPDATE", "_on_exit_progress_update"),
    ("EVENT_EXIT_COMPLETE", "_on_exit_complete"),
    ("EVENT_EXIT_CANCELLED", "_on_exit_cancelled"),
]


class MothershipEventHub:
    """F07 god-class split: subscribes the 14 mothership events to
    GameIntegrator handlers.

    The hub owns the subscription table and the registration call.
    Handlers remain on the GameIntegrator (they reference
    integrator-internal state like the mothership entity, the
    persistence manager, etc.), so the hub only does the binding.
    """

    def __init__(self, integrator: GameIntegrator) -> None:
        self._integrator = integrator

    def register_all(self) -> None:
        """Bind every event in ``HANDLER_BINDINGS`` to the integrator."""
        from . import event_bus as eb

        bus = self._integrator._event_bus
        for event_name, handler_name in HANDLER_BINDINGS:
            event_const = getattr(eb, event_name, None)
            handler = getattr(self._integrator, handler_name, None)
            if event_const is None:
                raise RuntimeError(f"MothershipEventHub: unknown event constant {event_name!r}")
            if handler is None:
                raise RuntimeError(f"MothershipEventHub: unknown handler {handler_name!r} on integrator")
            bus.subscribe(event_const, handler)

    def unregister_all(self) -> None:
        """Unbind every event in ``HANDLER_BINDINGS`` from the integrator."""
        from . import event_bus as eb

        bus = self._integrator._event_bus
        for event_name, handler_name in HANDLER_BINDINGS:
            event_const = getattr(eb, event_name, None)
            handler = getattr(self._integrator, handler_name, None)
            if event_const is not None and handler is not None:
                bus.unsubscribe(event_const, handler)



__all__ = ["HANDLER_BINDINGS", "MothershipEventHub"]
