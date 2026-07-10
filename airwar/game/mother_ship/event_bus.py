"""Event bus — publish/subscribe messaging for mothership events."""

import logging
from collections.abc import Callable

from airwar.config.constants_access import get_game_constants

from .interfaces import IEventBus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# F03 S4: Exceptions
# ---------------------------------------------------------------------------


class EventBusError(Exception):
    """Base class for EventBus errors."""


class SubscriptionCapExceeded(EventBusError):
    """Raised when a subscribe() call would push an event over MAX_SUBSCRIBERS.

    F03 S4: replaces the legacy silent ``return False`` contract. Callers
    MUST handle this (catch + unsubscribe the offender, or surface to UI).
    """

    def __init__(self, event: str, cap: int, existing: int) -> None:
        super().__init__(
            f"Subscription cap exceeded for event {event!r}: cap={cap}, existing={existing}. "
            f"Caller must unsubscribe() before retrying."
        )
        self.event = event
        self.cap = cap
        self.existing = existing


# ---------------------------------------------------------------------------
# F07 E1: Central event registry
# ---------------------------------------------------------------------------


# Each entry: payload_schema (kwargs the publisher should pass) +
#             subscribers_known (initial wiring metadata for diagnostics).
# New events MUST be added here so the event bus surface is documented
# in one place.
EVENT_REGISTRY: dict[str, dict] = {
    "EVENT_H_PRESSED": {"payload_schema": {"timestamp_ms": int}, "subscribers_known": []},
    "EVENT_H_RELEASED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_PROGRESS_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_DOCKING_ANIMATION_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_UNDOCKING_ANIMATION_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_STAY_EXPIRED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_ENTERING_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_UNDOCK_REQUESTED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_EXIT_STARTED": {"payload_schema": {"timestamp_ms": int}, "subscribers_known": []},
    "EVENT_EXIT_PROGRESS_UPDATE": {"payload_schema": {"progress": float}, "subscribers_known": []},
    "EVENT_EXIT_CANCELLED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_EXIT_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_START_UNDOCKING_ANIMATION": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_START_ENTERING_ANIMATION": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_START_DOCKING_ANIMATION": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_STAY_STARTED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_COOLDOWN_STARTED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_GAME_RESUME": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_UNDOCK_CANCELLED": {"payload_schema": {}, "subscribers_known": []},
    "EVENT_STATE_CHANGED": {"payload_schema": {"state": "MotherShipState"}, "subscribers_known": []},
    "EVENT_DOCKING_COMPLETE": {"payload_schema": {}, "subscribers_known": []},
}


# Event type constants
EVENT_STATE_CHANGED = "STATE_CHANGED"
EVENT_H_PRESSED = "H_PRESSED"
EVENT_H_RELEASED = "H_RELEASED"
EVENT_PROGRESS_COMPLETE = "PROGRESS_COMPLETE"
EVENT_DOCKING_ANIMATION_COMPLETE = "DOCKING_ANIMATION_COMPLETE"
EVENT_UNDOCKING_ANIMATION_COMPLETE = "UNDOCKING_ANIMATION_COMPLETE"
EVENT_STAY_EXPIRED = "STAY_EXPIRED"
EVENT_ENTERING_COMPLETE = "ENTERING_COMPLETE"
EVENT_UNDOCK_REQUESTED = "UNDOCK_REQUESTED"
EVENT_EXIT_COMPLETE = "EXIT_COMPLETE"
EVENT_EXIT_PROGRESS_UPDATE = "EXIT_PROGRESS_UPDATE"
EVENT_EXIT_CANCELLED = "EXIT_CANCELLED"
EVENT_START_UNDOCKING_ANIMATION = "START_UNDOCKING_ANIMATION"
EVENT_START_ENTERING_ANIMATION = "START_ENTERING_ANIMATION"
EVENT_START_DOCKING_ANIMATION = "START_DOCKING_ANIMATION"
EVENT_STAY_STARTED = "STAY_STARTED"
EVENT_COOLDOWN_STARTED = "COOLDOWN_STARTED"
EVENT_GAME_RESUME = "GAME_RESUME"
EVENT_UNDOCK_CANCELLED = "UNDOCK_CANCELLED"
EVENT_EXIT_STARTED = "EXIT_STARTED"
EVENT_DOCKING_COMPLETE = "DOCKING_COMPLETE"


class EventBus(IEventBus):
    """Event bus — publish/subscribe messaging for mothership events.

    Decouples mothership components by providing typed event channels
    for docking progress, state changes, and save completion.

    Per-event subscriber lists are bounded by ``MAX_SUBSCRIBERS`` to prevent
    unbounded memory growth in long sessions. When the cap is reached, new
    subscriptions are refused and a warning is logged; callers must invoke
    ``unsubscribe()`` before resubscribing.
    """

    # Backward-compatible aliases for values in GAME_CONSTANTS.EVENTS.
    MAX_SUBSCRIBERS: int = get_game_constants().EVENTS.MAX_SUBSCRIBERS

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._failure_counts: dict[tuple[str, int], int] = {}
        self._max_callback_failures: int | None = get_game_constants().EVENTS.MAX_CALLBACK_FAILURES

    def subscribe(self, event: str, callback: Callable) -> bool:
        """Subscribe ``callback`` to ``event``.

        Returns ``True`` on success, ``False`` if the per-event subscriber
        cap has been reached (the subscription is NOT added in that case
        and a warning is logged).
        """
        if event not in self._subscribers:
            self._subscribers[event] = []
        if callback in self._subscribers[event]:
            # Idempotent re-subscription: keep the existing slot, treat as
            # success so callers do not need to special-case duplicates.
            self._failure_counts.pop(self._failure_key(event, callback), None)
            return True
        if len(self._subscribers[event]) >= self.MAX_SUBSCRIBERS:
            # Refuse rather than evict: evicting an arbitrary subscriber
            # would silently drop a callback the original owner still
            # relies on, and there is no fair-eviction policy that does
            # not require cooperation from the subscriber. A loud refusal
            # forces the offending caller to be fixed.
            logger.warning(
                "Refusing subscription to %r: per-event cap of %d reached "
                "(existing subscribers: %d). Caller must unsubscribe before retrying.",
                event,
                self.MAX_SUBSCRIBERS,
                len(self._subscribers[event]),
            )
            # F03 S4: raise instead of returning False (silent refusal).
            raise SubscriptionCapExceeded(
                event=event,
                cap=self.MAX_SUBSCRIBERS,
                existing=len(self._subscribers[event]),
            )
        self._subscribers[event].append(callback)
        self._failure_counts.pop(self._failure_key(event, callback), None)
        return True

    def unsubscribe(self, event: str, callback: Callable) -> None:
        if event in self._subscribers:
            self._subscribers[event] = [cb for cb in self._subscribers[event] if cb != callback]
        self._failure_counts.pop(self._failure_key(event, callback), None)


    def publish(self, event: str, **kwargs) -> None:
        if event in self._subscribers:
            for callback in self._subscribers[event][:]:
                try:
                    callback(**kwargs)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception:
                    self._handle_callback_failure(event, callback)
                else:
                    self._failure_counts.pop(self._failure_key(event, callback), None)

    @staticmethod
    def _failure_key(event: str, callback: Callable) -> tuple[str, int]:
        return (event, id(callback))

    def _handle_callback_failure(self, event: str, callback: Callable) -> None:
        key = self._failure_key(event, callback)
        failures = self._failure_counts.get(key, 0) + 1
        self._failure_counts[key] = failures

        logger.error(
            "Event callback error [%s] from %r (%d/%s)",
            event,
            callback,
            failures,
            self._max_callback_failures or "unlimited",
            exc_info=True,
        )

        if self._max_callback_failures is not None and failures >= self._max_callback_failures:
            self.unsubscribe(event, callback)
            logger.error(
                "Unsubscribed failing event callback [%s] from %r after %d failures",
                event,
                callback,
                failures,
            )
