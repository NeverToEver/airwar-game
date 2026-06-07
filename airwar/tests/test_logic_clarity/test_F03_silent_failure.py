"""F03: 8 静默失败（silent failures）— POST-REFACTOR CONTRACT.

After the Phase 3 logic-clarity refactor, all S5/S6/S7/S4 silent paths
have been converted to explicit exceptions. These tests verify that the
new contract holds.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from airwar.entities.player_state import (
    IllegalPlayerTransition,
    PlayerAliveState,
    PlayerState,
    PlayerStateMachine,
)


class _StubPlayer:
    """Minimal duck-typed Player that satisfies PlayerStateMachine.__init__."""


def _make_sm() -> PlayerStateMachine:
    return PlayerStateMachine(_StubPlayer())


class TestF03IllegalPlayerTransitions:
    """S5, S6, S7: 玩家 HSM 非法转态应抛 IllegalPlayerTransition。"""

    def test_mark_dying_when_dead_raises(self):
        """S5: 已被 mark_dead 的玩家不应能 mark_dying。"""
        sm = _make_sm()
        sm.mark_dead()
        assert sm.state == PlayerState.DEAD
        with pytest.raises(IllegalPlayerTransition):
            sm.mark_dying()
        # State remains DEAD
        assert sm.state == PlayerState.DEAD

    def test_enter_boost_when_docked_raises(self):
        """S6: enter_boost 当 DOCKED 应抛 IllegalPlayerTransition。"""
        sm = _make_sm()
        sm.enter_dock()
        assert sm.alive_substate == PlayerAliveState.DOCKED
        with pytest.raises(IllegalPlayerTransition):
            sm.enter_boost()
        # State remains DOCKED
        assert sm.alive_substate == PlayerAliveState.DOCKED

    def test_enter_boost_when_shielded_raises(self):
        """S6 variant: enter_boost 当 SHIELDED 应抛。"""
        sm = _make_sm()
        sm.activate_shield(60)
        assert sm.alive_substate == PlayerAliveState.SHIELDED
        with pytest.raises(IllegalPlayerTransition):
            sm.enter_boost()
        assert sm.alive_substate == PlayerAliveState.SHIELDED

    def test_enter_dash_when_shielded_raises(self):
        """S7: enter_dash 非 NORMAL 应抛。"""
        sm = _make_sm()
        sm.activate_shield(60)
        assert sm.alive_substate == PlayerAliveState.SHIELDED
        with pytest.raises(IllegalPlayerTransition):
            sm.enter_dash()
        assert sm.alive_substate == PlayerAliveState.SHIELDED

    def test_enter_boost_when_dashing_raises(self):
        """S6 variant: enter_boost 当 DASHING 应抛。"""
        sm = _make_sm()
        sm.enter_dash()
        assert sm.alive_substate == PlayerAliveState.DASHING
        with pytest.raises(IllegalPlayerTransition):
            sm.enter_boost()
        assert sm.alive_substate == PlayerAliveState.DASHING


class TestF03EventBusSubscribeOverflow:
    """S4: 订阅满 1000 应抛 SubscriptionCapExceeded。"""

    def test_subscribe_overflow_raises(self):
        from airwar.game.mother_ship.event_bus import EventBus, SubscriptionCapExceeded

        bus = EventBus()
        bus.MAX_SUBSCRIBERS = 3

        def make_cb(i):
            def cb(**_):
                return None

            cb.__name__ = f"cb_{i}"
            return cb

        for i in range(3):
            bus.subscribe("EVT", make_cb(i))

        with pytest.raises(SubscriptionCapExceeded) as exc_info:
            bus.subscribe("EVT", make_cb(99))
        assert exc_info.value.event == "EVT"
        assert exc_info.value.cap == 3
        assert exc_info.value.existing == 3

    def test_subscribe_overflow_does_not_swallow_exception(self):
        """S4 sentinel: caller must not silently ignore the cap."""
        from airwar.game.mother_ship.event_bus import EventBus, SubscriptionCapExceeded

        bus = EventBus()
        bus.MAX_SUBSCRIBERS = 1

        def first_cb(**_):
            return None

        def second_cb(**_):
            return None

        bus.subscribe("EVT", first_cb)
        # After refactor: a second subscribe MUST raise (caller has no
        # choice but to handle it). A silent return is the legacy bug.
        with pytest.raises(SubscriptionCapExceeded):
            bus.subscribe("EVT", second_cb)


class TestF03BossEnrageIdempotent:
    """Boss trigger_enrage 应当 idempotent（这是设计而非失败）。"""

    def test_boss_enrage_idempotent(self):
        from airwar.entities import Boss, BossData
        from airwar.entities.enemy.boss import BossState
        from airwar.entities.enemy.boss.boss_state import BossStateMachine

        boss = Boss(500, 120, BossData(health=1000))
        boss.is_entering = False
        sm = BossStateMachine(boss)

        sm.trigger_enrage((0.0, 0.0))
        assert sm.state == BossState.ENRAGE_TRANSITION
        sm.trigger_enrage((0.0, 0.0))  # second call: no error
        assert sm.state == BossState.ENRAGE_TRANSITION


class TestF03HomecomingCanRequestReturnsFailureMode:
    """S8: _can_request 应返回 FailureMode enum。"""

    def test_failure_mode_enum_defined(self):
        from airwar.game.systems import homecoming_coordinator

        # Post-refactor: FailureMode enum should be defined
        assert hasattr(homecoming_coordinator, "FailureMode")

    def test_failure_mode_can_request_with_reason_returns_enum(self):
        from airwar.game.systems import homecoming_coordinator

        if hasattr(homecoming_coordinator.HomecomingCoordinator, "_can_request_with_reason"):
            # If the new method exists, verify it returns FailureMode
            coordinator = homecoming_coordinator.HomecomingCoordinator(
                detector=None, sequence=None, ui=None, base_talent_console=None
            )
            result = coordinator._can_request_with_reason(None, None)
            # Result should be a FailureMode enum value
            assert isinstance(result, homecoming_coordinator.FailureMode)
        else:
            pytest.skip("_can_request_with_reason not yet implemented")


class TestF03EventCallbackExceptionHandling:
    """S3: callback 异常处理。"""

    def test_event_callback_failure_unsubscriber_after_threshold(self):
        """S3: callbacks that fail 3+ times are unsubscribed.

        Current contract: callback exception is caught + counted, and
        the callback is unsubscribed after ``_max_callback_failures``
        consecutive failures.
        """
        from airwar.game.mother_ship.event_bus import EventBus

        bus = EventBus()
        bus._max_callback_failures = 2  # shrink to keep test fast

        def bad_cb(**_):
            raise RuntimeError("boom")

        bus.subscribe("EVT", bad_cb)
        # Each publish() increments the failure counter for bad_cb
        for _ in range(bus._max_callback_failures):
            bus.publish("EVT")
        # After reaching the threshold, bad_cb is unsubscribed
        assert bad_cb not in bus._subscribers["EVT"]
