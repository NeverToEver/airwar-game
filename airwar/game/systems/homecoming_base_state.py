"""Base state for homecoming — flag + mission progress sync.

Extracted from :class:`HomecomingCoordinator` in Phase 5-γ.
Owns the binary ``_base_pending`` flag and the two tickers that
project game state into the base-console mission model.
"""

from airwar.game.constants import GAME_CONSTANTS


class HomecomingBaseState:
    """Holds the ``_base_pending`` flag and the per-tick mission sync.

    Public surface (called by :class:`HomecomingCoordinator`):

    - :meth:`is_pending` / :meth:`set_pending` — flag query / mutation
    - :meth:`enter_base` / :meth:`exit_base` — explicit transitions
    - :meth:`update_base` — auto-claim completed mission rewards
    - :meth:`sync_mission_progress` — project game state into mission progress

    The flag is the *only* state owned here; everything else is
    queried from the base talent console and game state on each call.
    """

    def __init__(self) -> None:
        self._pending = False

    # --- Flag accessors ---

    def is_pending(self) -> bool:
        """Return True if the player is currently docked at the base."""
        return self._pending

    def set_pending(self, value: bool) -> None:
        """Set the pending flag (cast to bool for backward compat)."""
        self._pending = bool(value)

    def enter_base(self) -> None:
        """Mark the player as at-base (called when sequence completes)."""
        self._pending = True

    def exit_base(self) -> None:
        """Mark the player as no longer at-base (called on departure)."""
        self._pending = False

    # --- Per-tick sync ---

    def update_base(self, game_controller, base_talent_console, notification_manager) -> None:
        """Tick the base console and auto-claim completed mission rewards.

        Mutates ``game_controller.state.requisition_points`` and each
        mission's ``claimed`` flag. Surfaces a localized notification
        for each claimed reward.
        """
        if not self._pending or not base_talent_console:
            return
        base_talent_console.update()
        for mission in base_talent_console.get_missions():
            if mission.get("done", False) and not mission.get("claimed", False):
                game_controller.state.requisition_points += GAME_CONSTANTS.REQUISITION.MISSION_REWARD
                mission["claimed"] = True
                if notification_manager:
                    reward = GAME_CONSTANTS.REQUISITION.MISSION_REWARD
                    notification_manager.show(f"任务完成: {mission.get('name', '')} (+{reward}RP)")

    def sync_mission_progress(self, game_controller, base_talent_console, survival_frames) -> None:
        """Project game state into the base-console mission progress.

        Reads ``game_controller.state.kill_count`` /
        ``boss_kill_count`` and the survival-frame counter; writes
        ``progress`` and ``done`` fields on each mission.
        """
        if not base_talent_console or not game_controller:
            return
        for mission in base_talent_console.get_missions():
            target = mission.get("target", "")
            if target == "kills":
                mission["progress"] = game_controller.state.kill_count
            elif target == "survival_time":
                mission["progress"] = survival_frames // 60
            elif target == "boss_kills":
                mission["progress"] = game_controller.state.boss_kill_count
            mission["done"] = mission.get("progress", 0) >= mission.get("goal", 0)


__all__ = ["HomecomingBaseState"]
