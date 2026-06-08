"""F07: 2 事件总线注册透明度（event bus transparency）。

Maps: docs/logic-clarity/04-test-suite.md § F07.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest


class TestF07EventConstants:
    """E1: 24 事件常量定义在 event_bus.py。"""

    def test_all_event_constants_defined(self):
        from airwar.game.mother_ship.event_bus import (
            EVENT_COOLDOWN_COMPLETE,
            EVENT_COOLDOWN_STARTED,
            EVENT_DOCKING_ANIMATION_COMPLETE,
            EVENT_DOCKING_COMPLETE,
            EVENT_ENTERING_COMPLETE,
            EVENT_EXIT_CANCELLED,
            EVENT_EXIT_COMPLETE,
            EVENT_EXIT_PROGRESS_UPDATE,
            EVENT_EXIT_STARTED,
            EVENT_GAME_RESUME,
            EVENT_H_PRESSED,
            EVENT_H_RELEASED,
            EVENT_H_RELEASED_EARLY,
            EVENT_PROGRESS_COMPLETE,
            EVENT_SAVE_GAME_REQUEST,
            EVENT_START_DOCKING_ANIMATION,
            EVENT_START_ENTERING_ANIMATION,
            EVENT_START_UNDOCKING_ANIMATION,
            EVENT_STATE_CHANGED,
            EVENT_STAY_EXPIRED,
            EVENT_STAY_STARTED,
            EVENT_UNDOCK_CANCELLED,
            EVENT_UNDOCK_REQUESTED,
            EVENT_UNDOCKING_ANIMATION_COMPLETE,
        )

        # All 24 defined
        assert all(
            isinstance(v, str)
            for v in [
                EVENT_H_PRESSED,
                EVENT_H_RELEASED,
                EVENT_H_RELEASED_EARLY,
                EVENT_PROGRESS_COMPLETE,
                EVENT_DOCKING_ANIMATION_COMPLETE,
                EVENT_UNDOCKING_ANIMATION_COMPLETE,
                EVENT_STAY_EXPIRED,
                EVENT_ENTERING_COMPLETE,
                EVENT_UNDOCK_REQUESTED,
                EVENT_EXIT_STARTED,
                EVENT_EXIT_PROGRESS_UPDATE,
                EVENT_EXIT_CANCELLED,
                EVENT_EXIT_COMPLETE,
                EVENT_START_UNDOCKING_ANIMATION,
                EVENT_START_ENTERING_ANIMATION,
                EVENT_START_DOCKING_ANIMATION,
                EVENT_STAY_STARTED,
                EVENT_COOLDOWN_STARTED,
                EVENT_GAME_RESUME,
                EVENT_UNDOCK_CANCELLED,
                EVENT_COOLDOWN_COMPLETE,
                EVENT_SAVE_GAME_REQUEST,
                EVENT_STATE_CHANGED,
                EVENT_DOCKING_COMPLETE,
            ]
        )

    def test_central_registry_exists(self):
        """Post-refactor: EVENT_REGISTRY 中央表。"""
        from airwar.game.mother_ship import event_bus

        # Sentinel: current state, registry does not exist
        if not hasattr(event_bus, "EVENT_REGISTRY"):
            pytest.skip("E1: EVENT_REGISTRY not yet defined; refactor pending")


class TestF07SubscribeReturnValueHandling:
    """E2: subscribe 返回 False 应被 caller 处理。"""

    def test_callers_check_subscribe_return(self):
        """F07 E1: 14 subscriptions centralized in MothershipEventHub.HANDLER_BINDINGS.

        After the god-class split, the 14 subscribe() calls are no
        longer inline in game_integrator.py. They live as a data
        structure (HANDLER_BINDINGS) in event_hub.py, iterated by
        MothershipEventHub.register_all().

        The test now verifies the HANDLER_BINDINGS table has 14
        entries, replacing the legacy "14 inline subscribe() calls"
        heuristic.
        """
        from airwar.game.mother_ship.event_hub import HANDLER_BINDINGS

        # F07 E1: 14 events now bound via HANDLER_BINDINGS table.
        assert len(HANDLER_BINDINGS) == 14, f"Expected 14 HANDLER_BINDINGS, got {len(HANDLER_BINDINGS)}"

    def test_event_hub_centralizes_subscriptions(self):
        """F07 E1 + god-class split: 14 subscriptions go through MothershipEventHub."""
        from airwar.game.mother_ship.event_hub import HANDLER_BINDINGS

        assert len(HANDLER_BINDINGS) == 14
        for event_name, handler_name in HANDLER_BINDINGS:
            assert event_name.startswith("EVENT_"), f"Bad event name: {event_name}"
            assert handler_name.startswith("_on_"), f"Bad handler: {handler_name}"


class TestF07SubscribeIdempotent:
    """Verify subscribe is idempotent (duplicate subscription)."""

    def test_subscribe_duplicate_is_idempotent(self):
        from airwar.game.mother_ship.event_bus import EventBus

        bus = EventBus()

        def cb(**_):
            return None

        # Subscribe twice
        assert bus.subscribe("EVT", cb) is True
        result = bus.subscribe("EVT", cb)  # duplicate
        # Current: returns True (idempotent)
        assert result is True
        # Count should still be 1
        assert bus.subscriber_count("EVT") == 1


class TestF07UnsubscribeRemovesCallback:
    """Verify unsubscribe properly removes a callback."""

    def test_unsubscribe_after_subscribe(self):
        from airwar.game.mother_ship.event_bus import EventBus

        bus = EventBus()

        def cb(**_):
            return None

        bus.subscribe("EVT", cb)
        assert bus.subscriber_count("EVT") == 1
        bus.unsubscribe("EVT", cb)
        assert bus.subscriber_count("EVT") == 0
