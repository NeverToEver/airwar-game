from airwar.entities.player import Player
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.game.mother_ship.mother_ship_state import GameSaveData
from airwar.input.input_handler import MockInputHandler
from airwar.scenes.game_scene import GameScene
from airwar.ui.base_talent_console import BaseTalentConsole

import pygame


def _make_player() -> Player:
    player = Player(400, 760, MockInputHandler())
    player.boost_recovery_rate = 1.0
    return player


def test_talent_balance_converts_spread_points_into_laser_and_locks_spread() -> None:
    earned = {"Spread Shot": 1, "Laser": 0, "Phase Dash": 0, "Mothership Recall": 0}
    manager = TalentBalanceManager(earned)

    manager.select("offense", "Laser")
    effective = manager.effective_levels()

    assert effective["Laser"] == 1
    assert effective["Spread Shot"] == 0
    assert sum(effective.values()) == sum(earned.values())
    assert manager.locked_buffs() == {"Spread Shot"}


def test_talent_balance_converts_phase_dash_into_mothership_recall() -> None:
    earned = {"Spread Shot": 0, "Laser": 0, "Phase Dash": 1, "Mothership Recall": 1}
    manager = TalentBalanceManager(earned)

    manager.select("support", "Mothership Recall")
    effective = manager.effective_levels()

    assert effective["Mothership Recall"] == 2
    assert effective["Phase Dash"] == 0
    assert sum(effective.values()) == sum(earned.values())
    assert manager.locked_buffs() == {"Phase Dash"}


def test_talent_loadout_reapplies_player_abilities_without_stacking() -> None:
    player = _make_player()
    reward_system = RewardSystem("medium")
    reward_system.capture_player_baselines(player)
    earned = {
        "Spread Shot": 1,
        "Laser": 0,
        "Phase Dash": 1,
        "Mothership Recall": 0,
        "Boost Recovery": 1,
    }
    manager = TalentBalanceManager(earned, {"offense": "Laser", "support": "Mothership Recall"})

    manager.apply_to_reward_system(reward_system, player)
    manager.apply_to_reward_system(reward_system, player)

    weapon_status = player.get_weapon_status()
    assert weapon_status["laser"] is True
    assert weapon_status["spread"] is False
    assert player.phase_dash_enabled is False
    assert player.mothership_cooldown_mult == 0.5
    assert player.boost_recovery_rate == 1.5
    assert reward_system.locked_buffs == {"Spread Shot", "Phase Dash"}


def test_base_talent_console_renders_visible_route_controls() -> None:
    pygame.font.init()
    surface = pygame.Surface((1280, 720), pygame.SRCALPHA)
    console = BaseTalentConsole(1280, 720)
    reward_system = RewardSystem("medium")
    reward_system.locked_buffs = {"Spread Shot"}
    manager = TalentBalanceManager({"Spread Shot": 1, "Phase Dash": 1}, {"offense": "Laser"})

    console.render(surface, manager, reward_system)

    assert surface.get_bounding_rect().width > 0
    assert any(name.startswith("route:") for name in console._button_rects)


def test_restore_from_save_rehydrates_base_talent_loadout_locks() -> None:
    pygame.init()
    pygame.display.set_mode((800, 600))
    scene = GameScene()
    scene.enter(difficulty="medium", username="pilot")
    save_data = GameSaveData(
        username="pilot",
        player_health=80,
        player_max_health=100,
        buff_levels={"Laser": 1, "Mothership Recall": 1},
        earned_buff_levels={"Spread Shot": 1, "Phase Dash": 1},
        talent_loadout={"offense": "Laser", "support": "Mothership Recall"},
    )

    scene.restore_from_save(save_data)

    assert scene.reward_system.buff_levels["Laser"] == 1
    assert scene.reward_system.buff_levels["Spread Shot"] == 0
    assert scene.reward_system.buff_levels["Mothership Recall"] == 1
    assert scene.reward_system.buff_levels["Phase Dash"] == 0
    assert scene.reward_system.locked_buffs == {"Spread Shot", "Phase Dash"}
    assert scene.player.phase_dash_enabled is False
    assert scene.player.mothership_cooldown_mult == 0.5
