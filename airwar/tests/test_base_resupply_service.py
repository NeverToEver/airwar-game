"""Unit tests for :class:`BaseResupplyService` (Phase 5-γ, commit 3/4).

Covers the three transactions: repair (fill health), recharge (fill
boost), and combined resupply. Each test verifies the cost math,
the no-op guards (full / insufficient RP), and the save-callback
invocation. Service is constructed with ``coordinator=None`` since
``_invoke_save`` reads from ``self._save_fn`` (set via
``set_save_fn``), not from the coordinator.
"""

from types import SimpleNamespace

from airwar.game.systems.base_resupply_service import BaseResupplyService


def _make_player(health: int = 35, max_health: int = 140, boost_current: int = 40, boost_max: int = 220):
    return SimpleNamespace(
        health=health,
        max_health=max_health,
        boost_current=boost_current,
        boost_max=boost_max,
    )


def _make_controller(rp: int = 50):
    return SimpleNamespace(state=SimpleNamespace(requisition_points=rp))


def _make_service(saved_log: list | None = None) -> BaseResupplyService:
    svc = BaseResupplyService(coordinator=None)
    if saved_log is not None:
        svc.set_save_fn(lambda: saved_log.append(True) or True)
    return svc


def test_repair_at_base_fills_health_and_spends_rp() -> None:
    saved: list = []
    svc = _make_service(saved_log=saved)
    player = _make_player(health=35, max_health=140)
    controller = _make_controller(rp=50)
    notifications: list = []

    svc.repair_at_base(controller, player, SimpleNamespace(show=notifications.append))

    assert player.health == 140
    assert controller.state.requisition_points == 48  # 50 - 2(REPAIR_COST)
    assert saved == [True]
    assert notifications == ["机体维修完成 (-2RP)"]


def test_recharge_at_base_fills_boost_and_spends_rp() -> None:
    saved: list = []
    svc = _make_service(saved_log=saved)
    player = _make_player(boost_current=40, boost_max=220)
    controller = _make_controller(rp=50)
    notifications: list = []

    svc.recharge_at_base(controller, player, SimpleNamespace(show=notifications.append))

    assert player.boost_current == 220
    assert controller.state.requisition_points == 48  # 50 - 2(RECHARGE_COST)
    assert saved == [True]
    assert notifications == ["加速燃料补给完成 (-2RP)"]


def test_resupply_at_base_refills_both_at_combined_cost() -> None:
    saved: list = []
    svc = _make_service(saved_log=saved)
    player = _make_player(health=35, max_health=140, boost_current=40, boost_max=220)
    controller = _make_controller(rp=4)
    notifications: list = []

    svc.resupply_at_base(controller, player, SimpleNamespace(show=notifications.append))

    assert player.health == 140
    assert player.boost_current == 220
    assert controller.state.requisition_points == 0  # 4 - 4(combined)
    assert saved == [True]
    assert notifications == ["基地全面补给完成 (-4RP)"]


def test_resupply_at_base_no_ops_when_already_full() -> None:
    saved: list = []
    svc = _make_service(saved_log=saved)
    player = _make_player(health=140, max_health=140, boost_current=220, boost_max=220)
    controller = _make_controller(rp=50)
    notifications: list = []

    svc.resupply_at_base(controller, player, SimpleNamespace(show=notifications.append))

    assert controller.state.requisition_points == 50  # unchanged
    assert saved == []  # no save on no-op
    assert notifications == ["机体和燃料已全满，无需补给"]
