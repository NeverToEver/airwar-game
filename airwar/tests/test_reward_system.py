from unittest.mock import patch

from airwar.game.systems.reward_system import RewardSystem


def test_generate_options_allows_one_shot_buffs_before_unlock():
    reward_system = RewardSystem("medium")

    with patch("airwar.game.systems.reward_system.random.choice") as choice:
        choice.side_effect = [
            "offense",
            {"name": "Spread Shot", "desc": "", "icon": ""},
            "offense",
            {"name": "Laser", "desc": "", "icon": ""},
            "offense",
            {"name": "Power Shot", "desc": "", "icon": ""},
        ]

        options = reward_system.generate_options(boss_kill_count=3, unlocked_buffs=[])

    assert [option["name"] for option in options] == ["Spread Shot", "Laser", "Power Shot"]


def test_generate_options_filters_taken_one_shot_buffs():
    reward_system = RewardSystem("medium")
    reward_system.buff_levels["Spread Shot"] = 1

    options = reward_system.generate_options(boss_kill_count=3, unlocked_buffs=["Laser"])
    names = {option["name"] for option in options}

    assert "Spread Shot" not in names
    assert "Laser" not in names


def test_generate_options_filters_taken_phase_dash():
    reward_system = RewardSystem("medium")
    reward_system.buff_levels["Phase Dash"] = 1

    options = reward_system.generate_options(boss_kill_count=3, unlocked_buffs=[])
    names = {option["name"] for option in options}

    assert "Phase Dash" not in names


def test_unknown_reward_does_not_mutate_known_buff_levels():
    reward_system = RewardSystem("medium")
    before = dict(reward_system.buff_levels)

    notification = reward_system.apply_reward({"name": "Unknown Buff"}, player=object())

    assert notification == "获得: Unknown Buff"
    assert reward_system.buff_levels == before
