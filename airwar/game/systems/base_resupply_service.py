"""Base resupply service — repair / recharge / combined refill transactions.

Extracted from :class:`HomecomingCoordinator` in Phase 5-γ.
Pure transactional logic: spends requisition points, fills health
and/or boost, persists the loadout via the forwarded save callback.
"""

from airwar.game.constants import GAME_CONSTANTS


class BaseResupplyService:
    """Handles the three base-station resupply transactions.

    Public surface (called by :class:`HomecomingCoordinator` and by
    :class:`BaseTalentOrchestrator._handle_action`):

    - :meth:`repair_at_base` — refill ``player.health`` for ``REPAIR_COST`` RP
    - :meth:`recharge_at_base` — refill ``player.boost_current`` for ``RECHARGE_COST`` RP
    - :meth:`resupply_at_base` — combined health + boost refill
    - :meth:`set_save_fn` — forwarded from :class:`HomecomingCoordinator`

    All three methods no-op if the relevant stat is already full or
    the player cannot afford the cost. Each successful transaction
    invokes the save callback so the loadout persists.
    """

    def __init__(self, coordinator) -> None:
        self._coordinator = coordinator
        self._save_fn = None

    def set_save_fn(self, fn) -> None:
        """Set the save callback (forwarded from coordinator)."""
        self._save_fn = fn

    def _invoke_save(self) -> bool:
        if not self._save_fn:
            return False
        return self._save_fn()

    def repair_at_base(self, game_controller, player, notification_manager) -> None:
        cost = GAME_CONSTANTS.REQUISITION.REPAIR_COST
        if not player or not game_controller:
            return
        if game_controller.state.requisition_points < cost:
            return
        if player.health >= player.max_health:
            return
        game_controller.state.requisition_points -= cost
        player.health = player.max_health
        self._invoke_save()
        if notification_manager:
            notification_manager.show(f"机体维修完成 (-{cost}RP)")

    def recharge_at_base(self, game_controller, player, notification_manager) -> None:
        cost = GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        if not player or not game_controller:
            return
        if game_controller.state.requisition_points < cost:
            return
        if player.boost_current >= player.boost_max:
            return
        game_controller.state.requisition_points -= cost
        player.boost_current = player.boost_max
        self._invoke_save()
        if notification_manager:
            notification_manager.show(f"加速燃料补给完成 (-{cost}RP)")

    def resupply_at_base(self, game_controller, player, notification_manager) -> None:
        if not player or not game_controller:
            return
        need_health = player.health < player.max_health
        need_boost = hasattr(player, "boost_current") and player.boost_current < player.boost_max
        if not need_health and not need_boost:
            if notification_manager:
                notification_manager.show("机体和燃料已全满，无需补给")
            return
        actual_cost = 0
        if need_health:
            actual_cost += GAME_CONSTANTS.REQUISITION.REPAIR_COST
        if need_boost:
            actual_cost += GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        if game_controller.state.requisition_points < actual_cost:
            if notification_manager:
                notification_manager.show(f"征用点数不足: 需要{actual_cost}RP")
            return
        game_controller.state.requisition_points -= actual_cost
        if need_health:
            player.health = player.max_health
        if need_boost:
            player.boost_current = player.boost_max
        self._invoke_save()
        if notification_manager:
            notification_manager.show(f"基地全面补给完成 (-{actual_cost}RP)")


__all__ = ["BaseResupplyService"]
