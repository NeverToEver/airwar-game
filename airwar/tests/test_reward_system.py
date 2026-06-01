from unittest.mock import MagicMock, patch

import pytest

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


# --- Fixtures ---


@pytest.fixture
def rs():
    return RewardSystem("medium")


@pytest.fixture
def player():
    p = MagicMock()
    p.health = 80
    p.max_health = 100
    p.bullet_damage = 50
    p.fire_interval = 8
    p.fire_cooldown = 8
    p.pierce_count = 0
    p.boost_recovery_rate = 1.0
    p.mothership_cooldown_mult = 1.0
    p.is_phase_dash_enabled = False
    return p


# --- calculate_damage_taken ---


class TestCalculateDamageTaken:
    def test_no_armor_returns_raw(self, rs):
        assert rs.calculate_damage_taken(100) == 100

    def test_armor_reduces_damage(self, rs):
        rs.unlocked_buffs.append("Armor")
        assert rs.calculate_damage_taken(100) == 85

    def test_armor_rounds_down(self, rs):
        rs.unlocked_buffs.append("Armor")
        assert rs.calculate_damage_taken(33) == int(33 * 0.85)


# --- try_dodge ---


class TestTryDodge:
    def test_no_evasion_always_false(self, rs):
        for _ in range(50):
            assert rs.try_dodge() is False

    def test_evasion_returns_bool(self, rs):
        rs.unlocked_buffs.append("Evasion")
        results = {rs.try_dodge() for _ in range(200)}
        assert True in results
        assert False in results


# --- apply_lifesteal ---


class TestApplyLifesteal:
    def test_no_lifesteal_no_heal(self, rs, player):
        rs.apply_lifesteal(player, 100)
        assert player.health == 80

    def test_lifesteal_heals(self, rs, player):
        rs.unlocked_buffs.append("Lifesteal")
        rs.apply_lifesteal(player, 100)
        assert player.health == 90

    def test_lifesteal_caps_at_max(self, rs, player):
        player.health = 95
        rs.unlocked_buffs.append("Lifesteal")
        rs.apply_lifesteal(player, 100)
        assert player.health == 100

    def test_lifesteal_none_player(self, rs):
        rs.unlocked_buffs.append("Lifesteal")
        rs.apply_lifesteal(None, 100)


# --- apply_effective_levels ---


class TestApplyEffectiveLevels:
    def test_sets_buff_levels(self, rs):
        rs.apply_effective_levels({"Power Shot": 3, "Armor": 1})
        assert rs.buff_levels["Power Shot"] == 3
        assert rs.buff_levels["Armor"] == 1

    def test_unknown_buff_ignored(self, rs):
        rs.apply_effective_levels({"Fake Buff": 5})
        assert "Fake Buff" not in rs.buff_levels

    def test_negative_clamped_to_zero(self, rs):
        rs.apply_effective_levels({"Power Shot": -2})
        assert rs.buff_levels["Power Shot"] == 0

    def test_locked_buffs_propagated(self, rs):
        rs.apply_effective_levels({"Armor": 1}, locked_buffs={"Laser"})
        assert rs.locked_buffs == {"Laser"}

    def test_talent_loadout_propagated(self, rs):
        rs.apply_effective_levels({}, talent_loadout={"offense": "Spread Shot"})
        assert rs.talent_loadout == {"offense": "Spread Shot"}


# --- apply_reward ---


class TestApplyReward:
    def test_increments_level(self, rs, player):
        rs.apply_reward({"name": "Power Shot"}, player)
        assert rs.buff_levels["Power Shot"] == 1
        assert rs.earned_buff_levels["Power Shot"] == 1

    def test_adds_to_unlocked(self, rs, player):
        rs.apply_reward({"name": "Armor"}, player)
        assert "Armor" in rs.unlocked_buffs

    def test_extra_life_heals(self, rs, player):
        rs.apply_reward({"name": "Extra Life"}, player)
        assert player.max_health == 150

    def test_returns_notification(self, rs, player):
        result = rs.apply_reward({"name": "Power Shot"}, player)
        assert isinstance(result, str)
        assert len(result) > 0


# --- earned levels ---


class TestEarnedLevels:
    def test_earned_copies_from_buff_levels(self, rs):
        rs.buff_levels["Armor"] = 3
        rs.ensure_earned_levels()
        assert rs.earned_buff_levels["Armor"] == 3

    def test_no_copy_if_earned_already_set(self, rs):
        rs.earned_buff_levels["Armor"] = 5
        rs.buff_levels["Armor"] = 3
        rs.ensure_earned_levels()
        assert rs.earned_buff_levels["Armor"] == 5

    def test_get_earned_returns_copy(self, rs):
        rs.buff_levels["Power Shot"] = 2
        result = rs.get_earned_buff_levels()
        assert result["Power Shot"] == 2
        result["Power Shot"] = 999
        assert rs.earned_buff_levels["Power Shot"] == 2


# --- generate_options ---


class TestGenerateOptions:
    def test_returns_three_options(self, rs):
        options = rs.generate_options(5, [])
        assert len(options) == 3

    def test_explosive_gated_before_3_boss_kills(self, rs):
        for _ in range(100):
            options = rs.generate_options(0, [])
            names = [o["name"] for o in options]
            assert "Explosive" not in names

    def test_locked_buffs_excluded(self, rs):
        rs.locked_buffs = {"Power Shot", "Armor", "Extra Life"}
        for _ in range(50):
            options = rs.generate_options(5, [])
            names = {o["name"] for o in options}
            assert "Power Shot" not in names


# --- get_buff_color ---


class TestGetBuffColor:
    def test_unknown_buff_returns_white(self, rs):
        assert rs.get_buff_color("Fake Buff") == (255, 255, 255)


# --- reset ---


class TestReset:
    def test_reset_clears_state(self, rs, player):
        rs.apply_reward({"name": "Power Shot"}, player)
        rs.reset()
        assert rs.buff_levels["Power Shot"] == 0
        assert rs.earned_buff_levels["Power Shot"] == 0
        assert rs.unlocked_buffs == []
        assert rs.slow_factor == 1.0


# --- set_difficulty ---


class TestSetDifficulty:
    def test_easy_bullet_damage(self, rs):
        rs.set_difficulty("easy")
        assert rs.base_bullet_damage == 100

    def test_hard_bullet_damage(self, rs):
        rs.set_difficulty("hard")
        assert rs.base_bullet_damage == 34


# --- reapply_all_effects ---


class TestReapplyAllEffects:
    def test_resets_base_stats(self, rs, player):
        rs.reapply_all_effects(player)
        assert player.bullet_damage == 50
        assert player.pierce_count == 0
        assert player.max_health == 100

    def test_extra_life_increases_max(self, rs, player):
        rs.buff_levels["Extra Life"] = 1
        rs.reapply_all_effects(player)
        assert player.max_health == 150

    def test_none_player_noop(self, rs):
        rs.reapply_all_effects(None)


# --- do_explosive_damage ---


class TestDoExplosiveDamage:
    def test_no_explosive_level_noop(self, rs):
        enemy = MagicMock()
        enemy.active = True
        enemy.rect.centerx = 100
        enemy.rect.centery = 100
        rs.do_explosive_damage([enemy], 100, 100, 50)
        enemy.take_damage.assert_not_called()

    def test_explosive_damages_nearby(self, rs):
        rs.buff_levels["Explosive"] = 1
        rs.unlocked_buffs.append("Explosive")
        enemy = MagicMock()
        enemy.active = True
        enemy.rect.centerx = 100
        enemy.rect.centery = 100
        rs.do_explosive_damage([enemy], 100, 100, 50)
        enemy.take_damage.assert_called_once_with(25)

    def test_explosive_ignores_far(self, rs):
        rs.buff_levels["Explosive"] = 1
        rs.unlocked_buffs.append("Explosive")
        enemy = MagicMock()
        enemy.active = True
        enemy.rect.centerx = 500
        enemy.rect.centery = 500
        rs.do_explosive_damage([enemy], 100, 100, 50)
        enemy.take_damage.assert_not_called()

    def test_explosive_ignores_inactive(self, rs):
        rs.buff_levels["Explosive"] = 1
        rs.unlocked_buffs.append("Explosive")
        enemy = MagicMock()
        enemy.active = False
        rs.do_explosive_damage([enemy], 100, 100, 50)
        enemy.take_damage.assert_not_called()

    def test_empty_list_noop(self, rs):
        rs.buff_levels["Explosive"] = 1
        rs.do_explosive_damage([], 100, 100, 50)
