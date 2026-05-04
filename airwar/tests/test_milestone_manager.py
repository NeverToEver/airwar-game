from types import SimpleNamespace

from airwar.game.managers.game_controller import GameController
from airwar.game.managers.milestone_manager import MilestoneManager


def _make_selector():
    return SimpleNamespace(
        visible=False,
        options=[],
        selected_index=0,
        on_select=None,
    )


def test_saved_score_above_capped_threshold_does_not_loop_reward_selection() -> None:
    controller = GameController("medium", "pilot")
    controller.state.score = 100300
    controller.milestone_index = 238
    controller.cycle_count = 238
    selector = _make_selector()
    manager = MilestoneManager(controller, controller.reward_system)
    manager.set_reward_selector(selector)

    assert controller.get_next_threshold() == controller.get_previous_threshold()

    assert manager.check_and_trigger(player=object()) is False
    assert selector.visible is False
    assert controller.state.paused is False
