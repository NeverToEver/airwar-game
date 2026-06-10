"""Tests for EventBus — subscriber cap and unsubscribe path."""

import logging

import pytest

from airwar.game.mother_ship.event_bus import EventBus

# EventBus is the cross-system pub/sub backbone — fast pure-unit, smoke it.
pytestmark = pytest.mark.smoke


def _make_callbacks(n):
    """Build ``n`` distinct no-op callbacks (avoid lambda-binding quirks)."""

    def make(i):
        def cb(**_):
            return None

        cb.__name__ = f"cb_{i}"
        return cb

    return [make(i) for i in range(n)]


# ---------------------------------------------------------------------------
# Cap enforcement
# ---------------------------------------------------------------------------


def test_subscribe_returns_true_under_cap():
    bus = EventBus()
    cb = _make_callbacks(1)[0]
    assert bus.subscribe("EVENT", cb) is True
    assert bus.subscriber_count("EVENT") == 1


def test_subscribe_raises_when_cap_reached():
    """F03 S4: subscribe() raises SubscriptionCapExceeded (was silent return False)."""
    from airwar.game.mother_ship.event_bus import SubscriptionCapExceeded

    bus = EventBus()
    # Shrink the cap to keep the test fast and avoid allocating 1001 callbacks.
    bus.MAX_SUBSCRIBERS = 3

    callbacks = _make_callbacks(3)
    for cb in callbacks:
        assert bus.subscribe("CROWDED", cb) is True

    offending = _make_callbacks(1)[0]
    with pytest.raises(SubscriptionCapExceeded) as exc_info:
        bus.subscribe("CROWDED", offending)
    assert exc_info.value.event == "CROWDED"
    assert exc_info.value.cap == 3
    assert exc_info.value.existing == 3

    assert bus.subscriber_count("CROWDED") == 3
    assert offending not in bus._subscribers["CROWDED"]


def test_refused_subscriber_does_not_receive_events():
    """F03 S4: rejected subscribers are not added to the callback list."""
    from airwar.game.mother_ship.event_bus import SubscriptionCapExceeded

    bus = EventBus()
    bus.MAX_SUBSCRIBERS = 1

    accepted_calls = []
    rejected_calls = []

    def accepted(**_):
        accepted_calls.append(1)

    def rejected(**_):
        rejected_calls.append(1)

    assert bus.subscribe("E", accepted) is True
    with pytest.raises(SubscriptionCapExceeded):
        bus.subscribe("E", rejected)

    bus.publish("E")
    assert accepted_calls == [1]
    assert rejected_calls == []


def test_cap_is_per_event_not_global():
    bus = EventBus()
    bus.MAX_SUBSCRIBERS = 2

    a, b, c = _make_callbacks(3)
    assert bus.subscribe("EVENT_A", a) is True
    assert bus.subscribe("EVENT_A", b) is True
    # Hitting the cap on EVENT_A must not affect EVENT_B.
    assert bus.subscribe("EVENT_B", c) is True
    assert bus.subscriber_count("EVENT_A") == 2
    assert bus.subscriber_count("EVENT_B") == 1


def test_idempotent_subscribe_returns_true_and_keeps_single_entry(caplog):
    bus = EventBus()
    cb = _make_callbacks(1)[0]
    with caplog.at_level(logging.WARNING, logger="airwar.game.mother_ship.event_bus"):
        assert bus.subscribe("EVENT", cb) is True
        assert bus.subscribe("EVENT", cb) is True
    assert bus.subscriber_count("EVENT") == 1
    # Idempotent re-subscribe must not emit the cap-refusal warning.
    assert not any("Refusing subscription" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Unsubscribe
# ---------------------------------------------------------------------------


def test_unsubscribe_removes_callback():
    bus = EventBus()
    cb = _make_callbacks(1)[0]
    bus.subscribe("EVENT", cb)
    assert bus.subscriber_count("EVENT") == 1

    bus.unsubscribe("EVENT", cb)
    assert bus.subscriber_count("EVENT") == 0


def test_unsubscribe_one_of_many_keeps_others():
    bus = EventBus()
    a, b, c = _make_callbacks(3)
    bus.subscribe("EVENT", a)
    bus.subscribe("EVENT", b)
    bus.subscribe("EVENT", c)

    bus.unsubscribe("EVENT", b)
    assert bus.subscriber_count("EVENT") == 2
    assert a in bus._subscribers["EVENT"]
    assert c in bus._subscribers["EVENT"]
    assert b not in bus._subscribers["EVENT"]


def test_unsubscribe_unknown_event_is_noop():
    bus = EventBus()
    cb = _make_callbacks(1)[0]
    # Should not raise even though the event was never subscribed to.
    bus.unsubscribe("NEVER_SUBSCRIBED", cb)
    assert bus.subscriber_count("NEVER_SUBSCRIBED") == 0


def test_unsubscribe_unknown_callback_is_noop():
    bus = EventBus()
    bus.subscribe("EVENT", _make_callbacks(1)[0])
    bus.unsubscribe("EVENT", _make_callbacks(1)[0])  # different function
    assert bus.subscriber_count("EVENT") == 1


def test_unsubscribe_frees_capacity_for_resubscribe():
    """F03 S4: after unsubscribe, the next subscribe is accepted (no longer raises)."""
    from airwar.game.mother_ship.event_bus import SubscriptionCapExceeded

    bus = EventBus()
    bus.MAX_SUBSCRIBERS = 1
    first, second = _make_callbacks(2)

    assert bus.subscribe("EVENT", first) is True
    with pytest.raises(SubscriptionCapExceeded):
        bus.subscribe("EVENT", second)

    bus.unsubscribe("EVENT", first)
    # Slot is now free; second should be accepted on retry.
    assert bus.subscribe("EVENT", second) is True
    assert bus.subscriber_count("EVENT") == 1


# ---------------------------------------------------------------------------
# Subscriber count tracking
# ---------------------------------------------------------------------------


def test_subscriber_count_unknown_event_is_zero():
    bus = EventBus()
    assert bus.subscriber_count("UNKNOWN") == 0


def test_subscriber_count_reflects_growth_and_shrinkage():
    bus = EventBus()
    assert bus.subscriber_count("EVENT") == 0

    a, b = _make_callbacks(2)
    bus.subscribe("EVENT", a)
    assert bus.subscriber_count("EVENT") == 1
    bus.subscribe("EVENT", b)
    assert bus.subscriber_count("EVENT") == 2

    bus.unsubscribe("EVENT", a)
    assert bus.subscriber_count("EVENT") == 1
    bus.unsubscribe("EVENT", b)
    assert bus.subscriber_count("EVENT") == 0


# ---------------------------------------------------------------------------
# Default MAX_SUBSCRIBERS constant
# ---------------------------------------------------------------------------


def test_default_max_subscribers_is_documented_cap():
    # Regression guard: the cap value is part of the contract — if a future
    # change lowers it, legitimate subscribers may suddenly be rejected.
    assert EventBus.MAX_SUBSCRIBERS == 1000
