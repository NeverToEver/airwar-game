from types import SimpleNamespace

from airwar.game.constants import GAME_CONSTANTS
from airwar.game.managers.game_controller import GameController
from airwar.game.managers.milestone_manager import MilestoneManager


def _make_selector():
    return SimpleNamespace(
        visible=False,
        options=[],
        selected_index=0,
        on_select=None,
    )


def test_reward_thresholds_follow_design_curve_and_keep_growing() -> None:
    for difficulty in ("easy", "medium", "hard"):
        thresholds = [
            GAME_CONSTANTS.get_next_threshold(index, difficulty)
            for index in range(128)
        ]

        assert all(
            later > earlier
            for earlier, later in zip(thresholds, thresholds[1:], strict=False)
        )


def test_game_controller_uses_design_threshold_curve() -> None:
    controller = GameController("medium", "pilot")

    for index in (0, 1, 7, 8, 16, 64):
        assert controller.get_current_threshold(index) == GAME_CONSTANTS.get_next_threshold(index, "medium")


def test_saved_score_below_refactored_threshold_does_not_loop_reward_selection() -> None:
    controller = GameController("medium", "pilot")
    controller.state.score = 100300
    controller.milestone_index = 238
    controller.cycle_count = 238
    selector = _make_selector()
    manager = MilestoneManager(controller, controller.reward_system)
    manager.set_reward_selector(selector)

    assert controller.get_next_threshold() > controller.get_previous_threshold()
    assert controller.get_next_threshold() > controller.state.score

    assert manager.check_and_trigger(player=object()) is False
    assert selector.visible is False
    assert controller.state.paused is False


def test_score_at_active_threshold_triggers_reward_selection() -> None:
    controller = GameController("medium", "pilot")
    controller.state.score = int(controller.get_next_threshold())
    selector = _make_selector()
    manager = MilestoneManager(controller, controller.reward_system)
    manager.set_reward_selector(selector)

    assert manager.check_and_trigger(player=object()) is True
    assert selector.visible is True
    assert controller.state.paused is True
