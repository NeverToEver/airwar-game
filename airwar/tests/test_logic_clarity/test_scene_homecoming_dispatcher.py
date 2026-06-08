"""F07: SceneHomecomingDispatcher tests.

Covers the 0% coverage of the homecoming dispatcher that was
extracted from GameScene in Round 4 of the Phase 3 refactor.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestSceneHomecomingDispatcherDispatch:
    """F07: dispatcher forwards to HomecomingCoordinator with scene context."""

    def test_dispatcher_dispatches_update(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            _bullet_manager="bm",
            spawn_controller="sc",
            _game_loop_manager="glm",
            notification_manager="nm",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.update()
        coordinator.update.assert_called_once_with(
            "gc",
            "p",
            "lm",
            "bm",
            "sc",
            "glm",
            "nm",
        )

    def test_dispatcher_dispatches_on_requested(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            _bullet_manager="bm",
            notification_manager="nm",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.on_requested()
        coordinator.on_requested.assert_called_once_with("gc", "p", "lm", "bm", "nm")

    def test_dispatcher_dispatches_on_complete_propagates_state(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        coordinator.is_base_pending.return_value = True
        coordinator.get_talent_balance_manager.return_value = "tbm"
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            notification_manager="nm",
            reward_system="rs",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.on_complete()
        coordinator.on_complete.assert_called_once_with("gc", "p", "lm", "nm", "rs")
        assert scene._homecoming_base_pending is True
        assert scene._talent_balance_manager == "tbm"

    def test_dispatcher_dispatches_on_orbital_strike(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        scene = SimpleNamespace(
            spawn_controller="sc",
            _game_loop_manager="glm",
            player="p",
            notification_manager="nm",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.on_orbital_strike()
        coordinator.on_orbital_strike.assert_called_once_with("sc", "glm", "p", "nm")

    def test_dispatcher_dispatches_on_departure_complete_propagates_state(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        coordinator.is_base_pending.return_value = True
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            spawn_controller="sc",
            _game_loop_manager="glm",
            notification_manager="nm",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.on_departure_complete()
        coordinator.on_departure_complete.assert_called_once_with(
            "gc",
            "p",
            "lm",
            "sc",
            "glm",
            "nm",
        )
        assert scene._homecoming_base_pending is True

    def test_dispatcher_dispatches_leave_base_clears_pause(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        coordinator.is_base_pending.return_value = False
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            spawn_controller="sc",
            _game_loop_manager="glm",
            notification_manager="nm",
            _pause_requested=True,
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        dispatcher.leave_base()
        coordinator.leave_base.assert_called_once_with("gc", "p", "lm", "sc", "glm", "nm")
        assert scene._pause_requested is False

    def test_dispatcher_dispatches_handle_console_click(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        coordinator.handle_console_click.return_value = True
        scene = SimpleNamespace(
            game_controller="gc",
            player="p",
            _lock_manager="lm",
            spawn_controller="sc",
            _game_loop_manager="glm",
            notification_manager="nm",
            reward_system="rs",
        )

        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        result = dispatcher.handle_console_click((100, 200))
        assert result is True
        coordinator.handle_console_click.assert_called_once_with(
            (100, 200),
            "gc",
            "p",
            "lm",
            "sc",
            "glm",
            "nm",
            "rs",
        )


class TestSceneHomecomingDispatcherGuardClauses:
    """F07: dispatcher is a no-op when coordinator is None."""

    def test_no_op_when_coordinator_is_none(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        scene = SimpleNamespace()
        dispatcher = SceneHomecomingDispatcher(coordinator=None, scene=scene)

        # All dispatch methods should silently no-op
        assert dispatcher.update() is None
        assert dispatcher.on_requested() is None
        assert dispatcher.on_complete() is None
        assert dispatcher.on_orbital_strike() is None
        assert dispatcher.on_departure_complete() is None
        assert dispatcher.leave_base() is None
        # handle_console_click returns False when no coordinator
        assert dispatcher.handle_console_click((0, 0)) is False
        # State predicates also return False
        assert dispatcher._is_active() is False
        assert dispatcher._is_locked() is False
        assert dispatcher._is_base_pending() is False
        # coordinator() returns None
        assert dispatcher.coordinator() is None

    def test_state_predicates_when_coordinator_present(self):
        from airwar.scenes.scene_homecoming_dispatcher import (
            SceneHomecomingDispatcher,
        )

        coordinator = MagicMock()
        coordinator.is_active.return_value = True
        coordinator.is_locked.return_value = False
        coordinator.is_base_pending.return_value = True

        scene = SimpleNamespace()
        dispatcher = SceneHomecomingDispatcher(coordinator=coordinator, scene=scene)
        assert dispatcher._is_active() is True
        assert dispatcher._is_locked() is False
        assert dispatcher._is_base_pending() is True
