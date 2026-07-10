"""Base talent orchestrator — talent lifecycle + console click routing.

Extracted from :class:`HomecomingCoordinator` in Phase 5-γ.
Owns the :class:`TalentBalanceManager` instance and the action
dispatch table for the base talent console.
"""

from airwar.game.systems.talent_balance_manager import TalentBalanceManager


class BaseTalentOrchestrator:
    """Manages talent balance + routes base-console clicks to actions.

    Public surface (called by :class:`HomecomingCoordinator`):

    - :meth:`get_talent_balance_manager` — accessor (also exposed via
      ``coordinator.get_talent_balance_manager()``)
    - :meth:`ensure_talent_balance_manager` — lazy init from reward system
    - :meth:`apply_talent_loadout` — apply effective levels + save
    - :meth:`handle_console_click` — public entry for UI clicks
    - :meth:`_handle_action` — internal action dispatcher
    - :meth:`set_save_fn` — forwarded from :class:`HomecomingCoordinator`

    The orchestrator references :class:`HomecomingCoordinator` for
    sibling components (``_resupply`` for RESUPPLY/REPAIR/RECHARGE,
    ``leave_base`` for CONTINUE) and uses :attr:`_save_fn` for
    loadout persistence.
    """

    def __init__(self, coordinator, base_talent_console) -> None:
        self._coordinator = coordinator
        self._base_talent_console = base_talent_console
        self._talent_balance_manager = None
        self._save_fn = None

    # --- Accessors ---

    def get_talent_balance_manager(self):
        return self._talent_balance_manager

    def set_save_fn(self, fn) -> None:
        """Set the save callback (forwarded from coordinator)."""
        self._save_fn = fn

    def _invoke_save(self) -> bool:
        if not self._save_fn:
            return False
        return self._save_fn()

    # --- Talent lifecycle ---

    def ensure_talent_balance_manager(self, reward_system) -> None:
        """Build :class:`TalentBalanceManager` from reward system state."""
        if not reward_system:
            return
        reward_system.ensure_earned_levels()
        self._talent_balance_manager = TalentBalanceManager(
            reward_system.get_earned_buff_levels(),
            reward_system.talent_loadout,
        )
        self.apply_talent_loadout(reward_system, None, show_notification=False)

    def apply_talent_loadout(self, reward_system, player, show_notification=True, notification_manager=None) -> None:
        """Apply the effective levels to the reward system + save loadout."""
        if not self._talent_balance_manager or not reward_system:
            return
        reward_system.apply_effective_levels(
            self._talent_balance_manager.effective_levels(),
            locked_buffs=self._talent_balance_manager.locked_buffs(),
            talent_loadout=self._talent_balance_manager._loadout,
        )
        if player:
            reward_system.reapply_all_effects(player)
        self._invoke_save()
        if show_notification and notification_manager:
            notification_manager.show("基地天赋配置已同步")

    # --- Click routing ---

    def handle_console_click(
        self,
        pos,
        game_controller,
        player,
        lock_manager,
        spawn_controller,
        game_loop_manager,
        notification_manager,
        reward_system,
    ) -> bool:
        if not self._base_talent_console or not self._talent_balance_manager:
            return False
        action = self._base_talent_console.handle_mouse_click(pos)
        if action is None:
            return False
        self._handle_action(
            action,
            game_controller,
            player,
            lock_manager,
            spawn_controller,
            game_loop_manager,
            notification_manager,
            reward_system,
        )
        return True

    def _handle_action(
        self,
        action,
        game_controller,
        player,
        lock_manager,
        spawn_controller,
        game_loop_manager,
        notification_manager,
        reward_system,
    ) -> None:
        from airwar.ui.base_talent_console import BaseTalentConsoleAction

        if action.kind == BaseTalentConsoleAction.CONTINUE:
            self._coordinator.leave_base(
                game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager
            )
            return
        if action.kind == BaseTalentConsoleAction.RESUPPLY:
            self._coordinator._resupply.resupply_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.REPAIR:
            self._coordinator._resupply.repair_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.RECHARGE:
            self._coordinator._resupply.recharge_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.SELECT_MODULE:
            return
        if action.kind == BaseTalentConsoleAction.SELECT_ROUTE and action.route:
            if self._talent_balance_manager and self._talent_balance_manager.next_option(action.route) is not None:
                self.apply_talent_loadout(
                    reward_system, player, show_notification=True, notification_manager=notification_manager
                )


__all__ = ["BaseTalentOrchestrator"]
