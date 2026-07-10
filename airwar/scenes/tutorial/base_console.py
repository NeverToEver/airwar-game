"""Base-talent-console helper functions for the tutorial homecoming stage.

Extracted from :mod:`airwar.scenes.tutorial_scene` so the scene file
stays focused on lifecycle + dispatch. Every function here is
exclusively used by the homecoming-base stage (id
``homecoming_base``) and is intentionally a free function that takes
the scene as its first argument (rather than a method on a class) --
the scene delegates to these helpers from its homecoming-base flow.
"""

from __future__ import annotations

from airwar.config.design_tokens import SceneColors  # noqa: F401  (kept for back-compat imports)
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.scenes.tutorial.models import (
    TutorialBaseGameController,
    TutorialBasePlayerStatus,
)
from airwar.ui.base_talent_console import BaseTalentConsoleAction


def setup_base_console_data(scene) -> None:
    """Build the per-tutorial-base player/controller/console data.

    Mirrors the legacy ``_setup_base_console_data`` initialisation: a
    fixed talent-route selection (offense=Laser, support=Mothership
    Recall) is applied to the reward system and the player status
    object.
    """
    scene._base_player_status = TutorialBasePlayerStatus()
    scene._base_game_controller = TutorialBaseGameController()
    scene._base_reward_system = RewardSystem("medium")
    earned_levels = {
        "Spread Shot": 1,
        "Laser": 1,
        "Phase Dash": 1,
        "Mothership Recall": 1,
        "Power Shot": 1,
        "Boost Recovery": 1,
    }
    scene._talent_balance_manager = TalentBalanceManager(
        earned_levels,
        {"offense": "Laser", "support": "Mothership Recall"},
    )
    scene._talent_balance_manager.apply_to_reward_system(
        scene._base_reward_system,
        scene._base_player_status,
    )


def repair_at_tutorial_base(scene) -> None:
    if not scene._base_game_controller or not scene._base_player_status:
        return
    cost = GAME_CONSTANTS.REQUISITION.REPAIR_COST
    if scene._base_game_controller.state.requisition_points < cost:
        return
    if scene._base_player_status.health >= scene._base_player_status.max_health:
        return
    scene._base_game_controller.state.requisition_points -= cost
    scene._base_player_status.health = scene._base_player_status.max_health


def recharge_at_tutorial_base(scene) -> None:
    if not scene._base_game_controller or not scene._base_player_status:
        return
    cost = GAME_CONSTANTS.REQUISITION.RECHARGE_COST
    if scene._base_game_controller.state.requisition_points < cost:
        return
    if scene._base_player_status.boost_current >= scene._base_player_status.max_health:
        return
    scene._base_game_controller.state.requisition_points -= cost
    scene._base_player_status.boost_current = scene._base_player_status.max_health


def resupply_at_tutorial_base(scene) -> None:
    if not scene._base_game_controller or not scene._base_player_status:
        return
    need_health = scene._base_player_status.health < scene._base_player_status.max_health
    need_boost = scene._base_player_status.boost_current < scene._base_player_status.boost_max
    if not need_health and not need_boost:
        return
    cost = 0
    if need_health:
        cost += GAME_CONSTANTS.REQUISITION.REPAIR_COST
    if need_boost:
        cost += GAME_CONSTANTS.REQUISITION.RECHARGE_COST
    if scene._base_game_controller.state.requisition_points < cost:
        return
    scene._base_game_controller.state.requisition_points -= cost
    if need_health:
        scene._base_player_status.health = scene._base_player_status.max_health
    if need_boost:
        scene._base_player_status.boost_current = scene._base_player_status.boost_max


def handle_base_console_action(scene, action) -> None:
    """Dispatch a :class:`BaseTalentConsoleAction` to the right helper.

    The "Continue" branch is stage-aware: it only flips the
    ``_base_sub_phase`` to ``depart`` while the homecoming stage is
    active and the player is in the base interior.
    """
    if action.kind == BaseTalentConsoleAction.CONTINUE:
        if scene._stage.id == "homecoming_base" and scene._base_sub_phase == "base":
            scene._base_sub_phase = "depart"
            scene._depart_timer = scene.DEPART_FRAMES
            scene._stage_progress = 0
            scene._fade_phase = "out"
            scene._fade_alpha = 0
        return

    if action.kind == BaseTalentConsoleAction.RESUPPLY:
        resupply_at_tutorial_base(scene)
        return

    if action.kind == BaseTalentConsoleAction.REPAIR:
        repair_at_tutorial_base(scene)
        return

    if action.kind == BaseTalentConsoleAction.RECHARGE:
        recharge_at_tutorial_base(scene)
        return

    if action.kind == BaseTalentConsoleAction.SELECT_MODULE:
        return

    if action.kind == BaseTalentConsoleAction.SELECT_ROUTE and action.route:
        scene._talent_balance_manager.next_option(action.route)
        if scene._base_reward_system and scene._base_player_status:
            scene._talent_balance_manager.apply_to_reward_system(
                scene._base_reward_system,
                scene._base_player_status,
            )


__all__ = [
    "handle_base_console_action",
    "recharge_at_tutorial_base",
    "repair_at_tutorial_base",
    "resupply_at_tutorial_base",
    "setup_base_console_data",
]
