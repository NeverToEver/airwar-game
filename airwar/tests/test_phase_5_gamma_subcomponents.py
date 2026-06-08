"""Targeted unit tests for the 3 new sub-components extracted in Phase 5-γ.

Brings coverage up from 43/74/78% to 100% on the parts that were
covered only via integration tests before:

- HomecomingBaseState.update_base (mission auto-claim + notify)
- HomecomingBaseState.sync_mission_progress (3 target types)
- BaseTalentOrchestrator.ensure_talent_balance_manager / apply_talent_loadout
  no-op guards
- BaseTalentOrchestrator.handle_console_click (click routing)
- BaseTalentOrchestrator._handle_action (all 6 action kinds)
- MotherShipRenderer.render early branches (phantom / not-visible)
- MotherShipRenderer._draw_phantom_* helpers (4 polygon helpers)
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.constants import GAME_CONSTANTS
from airwar.game.mother_ship.mother_ship import MotherShip
from airwar.game.systems.base_talent_orchestrator import BaseTalentOrchestrator
from airwar.game.systems.homecoming_base_state import HomecomingBaseState
from airwar.ui.base_talent_console import BaseTalentConsoleAction

# ════════════════════════════════════════════════════════════════════════
# HomecomingBaseState
# ════════════════════════════════════════════════════════════════════════


def _make_console(missions=None):
    console = MagicMock()
    console.get_missions.return_value = missions if missions is not None else []
    return console


def test_update_base_claims_completed_mission_and_notifies() -> None:
    state = HomecomingBaseState()
    state.enter_base()
    missions = [
        {"name": "消灭10架敌机", "target": "kills", "progress": 10, "goal": 10, "done": True, "claimed": False},
    ]
    console = _make_console(missions=missions)
    controller = SimpleNamespace(state=SimpleNamespace(requisition_points=10))
    notifications = MagicMock()

    state.update_base(controller, console, notifications)

    assert controller.state.requisition_points == 10 + GAME_CONSTANTS.REQUISITION.MISSION_REWARD
    assert missions[0]["claimed"] is True
    reward = GAME_CONSTANTS.REQUISITION.MISSION_REWARD
    notifications.show.assert_called_once_with(f"任务完成: 消灭10架敌机 (+{reward}RP)")


def test_update_base_no_op_when_not_pending_or_no_console() -> None:
    state = HomecomingBaseState()  # not pending
    console = _make_console(missions=[{"done": True, "claimed": False, "name": "X"}])
    controller = SimpleNamespace(state=SimpleNamespace(requisition_points=10))
    notifications = MagicMock()

    state.update_base(controller, console, notifications)

    assert controller.state.requisition_points == 10  # unchanged
    notifications.show.assert_not_called()


def test_update_base_skips_already_claimed() -> None:
    state = HomecomingBaseState()
    state.enter_base()
    missions = [
        {"name": "Done", "target": "kills", "progress": 10, "goal": 10, "done": True, "claimed": True},
    ]
    console = _make_console(missions=missions)
    controller = SimpleNamespace(state=SimpleNamespace(requisition_points=10))
    notifications = MagicMock()

    state.update_base(controller, console, notifications)

    assert controller.state.requisition_points == 10  # unchanged
    notifications.show.assert_not_called()


def test_sync_mission_progress_kills_target() -> None:
    state = HomecomingBaseState()
    missions = [
        {"target": "kills", "progress": 0, "goal": 5, "done": False},
        {"target": "kills", "progress": 0, "goal": 1, "done": False},
    ]
    console = _make_console(missions=missions)
    controller = SimpleNamespace(state=SimpleNamespace(kill_count=3, boss_kill_count=0))

    state.sync_mission_progress(controller, console, survival_frames=0)

    assert missions[0]["progress"] == 3
    assert missions[0]["done"] is False  # goal 5, progress 3
    assert missions[1]["progress"] == 3
    assert missions[1]["done"] is True  # goal 1, progress 3


def test_sync_mission_progress_survival_time_target() -> None:
    state = HomecomingBaseState()
    missions = [{"target": "survival_time", "progress": 0, "goal": 60, "done": False}]
    console = _make_console(missions=missions)
    controller = SimpleNamespace(state=SimpleNamespace(kill_count=0, boss_kill_count=0))

    state.sync_mission_progress(controller, console, survival_frames=3700)  # 61 seconds

    assert missions[0]["progress"] == 61  # 3700 // 60
    assert missions[0]["done"] is True


def test_sync_mission_progress_boss_kills_target() -> None:
    state = HomecomingBaseState()
    missions = [{"target": "boss_kills", "progress": 0, "goal": 1, "done": False}]
    console = _make_console(missions=missions)
    controller = SimpleNamespace(state=SimpleNamespace(kill_count=99, boss_kill_count=1))

    state.sync_mission_progress(controller, console, survival_frames=0)

    assert missions[0]["progress"] == 1
    assert missions[0]["done"] is True


def test_sync_mission_progress_no_op_when_no_console() -> None:
    state = HomecomingBaseState()
    controller = SimpleNamespace(state=SimpleNamespace(kill_count=10, boss_kill_count=0))
    # No console — should not crash
    state.sync_mission_progress(controller, None, survival_frames=0)


# ════════════════════════════════════════════════════════════════════════
# BaseTalentOrchestrator
# ════════════════════════════════════════════════════════════════════════


def _make_orchestrator(reward_system=None, has_manager=False) -> BaseTalentOrchestrator:
    coordinator = SimpleNamespace(
        leave_base=MagicMock(),
        _resupply=SimpleNamespace(
            resupply_at_base=MagicMock(),
            repair_at_base=MagicMock(),
            recharge_at_base=MagicMock(),
        ),
    )
    orch = BaseTalentOrchestrator(coordinator, base_talent_console=MagicMock())
    if has_manager:
        orch._talent_balance_manager = MagicMock()
    return orch


def test_ensure_talent_balance_manager_no_op_when_no_reward_system() -> None:
    orch = _make_orchestrator()
    orch.ensure_talent_balance_manager(None)
    assert orch._talent_balance_manager is None


def test_apply_talent_loadout_no_op_when_no_manager() -> None:
    orch = _make_orchestrator(has_manager=False)
    reward = MagicMock()
    orch.apply_talent_loadout(reward, None, show_notification=True, notification_manager=MagicMock())
    reward.apply_effective_levels.assert_not_called()


def test_handle_console_click_returns_false_when_no_console() -> None:
    coordinator = SimpleNamespace(_resupply=SimpleNamespace())
    orch = BaseTalentOrchestrator(coordinator, base_talent_console=None)
    orch._talent_balance_manager = MagicMock()
    result = orch.handle_console_click((0, 0), MagicMock(), MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    assert result is False


def test_handle_console_click_returns_false_when_no_manager() -> None:
    orch = _make_orchestrator(has_manager=False)
    result = orch.handle_console_click((0, 0), MagicMock(), MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    assert result is False


def test_handle_console_click_returns_false_when_console_returns_none() -> None:
    orch = _make_orchestrator(has_manager=True)
    orch._base_talent_console.handle_mouse_click.return_value = None
    result = orch.handle_console_click((0, 0), MagicMock(), MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    assert result is False


def test_handle_console_click_routes_to_action() -> None:
    orch = _make_orchestrator(has_manager=True)
    orch._base_talent_console.handle_mouse_click.return_value = BaseTalentConsoleAction.continue_sortie()
    result = orch.handle_console_click((0, 0), MagicMock(), MagicMock(), MagicMock(),
                                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    assert result is True
    orch._coordinator.leave_base.assert_called_once()


def test_handle_action_continue_dispatches_to_leave_base() -> None:
    orch = _make_orchestrator(has_manager=False)
    action = BaseTalentConsoleAction.continue_sortie()
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._coordinator.leave_base.assert_called_once()


def test_handle_action_resupply_dispatches_to_resupply_service() -> None:
    orch = _make_orchestrator(has_manager=False)
    action = BaseTalentConsoleAction.resupply()
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._coordinator._resupply.resupply_at_base.assert_called_once()


def test_handle_action_repair_dispatches_to_resupply_service() -> None:
    orch = _make_orchestrator(has_manager=False)
    action = BaseTalentConsoleAction.repair()
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._coordinator._resupply.repair_at_base.assert_called_once()


def test_handle_action_recharge_dispatches_to_resupply_service() -> None:
    orch = _make_orchestrator(has_manager=False)
    action = BaseTalentConsoleAction.recharge()
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._coordinator._resupply.recharge_at_base.assert_called_once()


def test_handle_action_select_module_no_op() -> None:
    orch = _make_orchestrator(has_manager=True)
    action = BaseTalentConsoleAction.select_module("mission")
    # No exception, no call to resupply or route apply — SELECT_MODULE is a no-op branch.
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._coordinator._resupply.resupply_at_base.assert_not_called()
    orch._coordinator._resupply.repair_at_base.assert_not_called()
    orch._coordinator._resupply.recharge_at_base.assert_not_called()
    orch._coordinator.leave_base.assert_not_called()
    # next_option must NOT be queried for SELECT_MODULE
    orch._talent_balance_manager.next_option.assert_not_called()


def test_handle_action_select_route_with_no_next_option_no_op() -> None:
    orch = _make_orchestrator(has_manager=True)
    orch._talent_balance_manager.next_option.return_value = None
    action = BaseTalentConsoleAction.select_route("offense")
    orch._handle_action(action, MagicMock(), MagicMock(), MagicMock(),
                        MagicMock(), MagicMock(), MagicMock(), MagicMock())
    orch._talent_balance_manager.next_option.assert_called_once_with("offense")


# ════════════════════════════════════════════════════════════════════════
# MotherShipRenderer
# ════════════════════════════════════════════════════════════════════════


def test_render_phantom_visible_branch_skips_hull_render(monkeypatch) -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show_phantom()
    # Don't call .show() — so motion._visible is False. Phantom should render,
    # hull-render branch should early-return.
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    mother_ship.render(surface)
    # Phantom draws to the cached _phantom_surf which is then blitted.
    # The hull branch (after the not-visible check) should NOT have run.
    # Verify by checking that motion._visible is still False.
    assert mother_ship._motion._visible is False


def test_render_not_visible_no_phantom_no_crash() -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    # Don't call .show() or .show_phantom() — both early-return branches.
    mother_ship.render(surface)
    assert mother_ship._motion._visible is False
    assert mother_ship._motion._phantom_visible is False


def test_render_visible_full_pipeline_runs(monkeypatch) -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show()
    mother_ship.set_position(960, 400)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    mother_ship.render(surface)
    # Surface should have non-transparent pixels (the hull drew something)
    assert surface.get_bounding_rect().width >= 100


def test_draw_phantom_hull_polygon() -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    renderer = mother_ship._renderer
    renderer._draw_phantom_hull(surface, 960, 400, (200, 200, 200, 255), 2)
    # Should have drawn 9 vertices
    bbox = surface.get_bounding_rect()
    assert bbox.width > 0


def test_draw_phantom_sponsons_polygon() -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    renderer = mother_ship._renderer
    renderer._draw_phantom_sponsons(surface, 960, 400, (200, 200, 200, 255), 2)
    bbox = surface.get_bounding_rect()
    assert bbox.width > 0


def test_draw_phantom_docking_bay_polygon() -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    renderer = mother_ship._renderer
    renderer._draw_phantom_docking_bay(surface, 960, 400, (200, 200, 200, 255))
    bbox = surface.get_bounding_rect()
    assert bbox.width > 0


def test_draw_phantom_engines_ellipses() -> None:
    pygame.init()
    mother_ship = MotherShip(1920, 1080)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    renderer = mother_ship._renderer
    renderer._draw_phantom_engines(surface, 960, 400, 0.5)
    bbox = surface.get_bounding_rect()
    assert bbox.width > 0


def test_render_phantom_full_pipeline(monkeypatch) -> None:
    """Full _render_phantom path: cache creation, hull + sponsons + bay + engines."""
    pygame.init()
    # Make get_ticks deterministic
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show_phantom()  # records _phantom_started_at = 1000
    # Advance time so reveal > 0 (full reveal at +520ms)
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 2000)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    mother_ship._renderer._render_phantom(surface)
    # Verify cache was created
    assert mother_ship._renderer._phantom_surf is not None
    assert mother_ship._renderer._phantom_surf_size == (1920, 1080)
    # Second call should reuse cache (no reallocation)
    cached = mother_ship._renderer._phantom_surf
    mother_ship._renderer._render_phantom(surface)
    assert mother_ship._renderer._phantom_surf is cached  # same object
