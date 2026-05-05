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


class _SelectorWithShow:
    def __init__(self) -> None:
        self.visible = False
        self.options = []
        self.callback = None
        self.buff_levels = None
        self.unlocked_buffs = None

    def show(self, options, callback, buff_levels=None, unlocked_buffs=None) -> None:
        self.visible = True
        self.options = options
        self.callback = callback
        self.buff_levels = buff_levels
        self.unlocked_buffs = unlocked_buffs


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


def test_reward_selector_show_receives_current_buff_state() -> None:
    controller = GameController("medium", "pilot")
    controller.state.score = int(controller.get_next_threshold())
    controller.reward_system.buff_levels["Rapid Fire"] = 2
    controller.reward_system.unlocked_buffs.append("Rapid Fire")
    selector = _SelectorWithShow()
    manager = MilestoneManager(controller, controller.reward_system)
    manager.set_reward_selector(selector)

    assert manager.check_and_trigger(player=object()) is True

    assert selector.visible is True
    assert selector.buff_levels["Rapid Fire"] == 2
    assert selector.unlocked_buffs == ["Rapid Fire"]
