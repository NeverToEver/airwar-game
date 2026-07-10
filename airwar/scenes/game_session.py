"""Typed composition root for one active gameplay session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.player import Player
    from airwar.game.give_up.give_up_detector import GiveUpDetector
    from airwar.game.managers.boss_manager import BossManager
    from airwar.game.managers.bullet_manager import BulletManager
    from airwar.game.managers.collision_controller import CollisionController
    from airwar.game.managers.game_controller import GameController
    from airwar.game.managers.game_loop_manager import GameLoopManager
    from airwar.game.managers.input_coordinator import InputCoordinator
    from airwar.game.managers.milestone_manager import MilestoneManager
    from airwar.game.managers.spawn_controller import SpawnController
    from airwar.game.managers.ui_manager import UIManager
    from airwar.game.mother_ship.game_integrator import GameIntegrator
    from airwar.game.rendering.game_renderer import GameRenderer
    from airwar.game.rendering.hud_renderer import HUDRenderer
    from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator
    from airwar.game.systems.notification_manager import NotificationManager
    from airwar.game.systems.reward_system import RewardSystem
    from airwar.game.homecoming.homecoming_detector import HomecomingDetector
    from airwar.game.homecoming.homecoming_sequence import HomecomingSequence
    from airwar.scenes.game_scene_renderer import GameSceneRenderer
    from airwar.ui.aim_crosshair import AimCrosshair
    from airwar.ui.ammo_magazine import AmmoMagazine
    from airwar.ui.base_talent_console import BaseTalentConsole
    from airwar.ui.boost_gauge import BoostGauge
    from airwar.ui.give_up_ui import GiveUpUI
    from airwar.ui.homecoming_ui import HomecomingUI
    from airwar.ui.reward_selector import RewardSelector
    from airwar.ui.warning_banner import WarningBanner


@dataclass(slots=True)
class GameSession:
    """All collaborators initialized for a single entry into ``GameScene``.

    ``GameScene`` still exposes legacy attributes while callers are migrated,
    but construction and ownership now have one typed boundary.
    """

    game_controller: GameController
    game_renderer: GameRenderer
    reward_system: RewardSystem
    hud_renderer: HUDRenderer
    notification_manager: NotificationManager
    spawn_controller: SpawnController
    collision_controller: CollisionController
    player: Player
    reward_selector: RewardSelector
    boost_gauge: BoostGauge
    ammo_magazine: AmmoMagazine
    warning_banner: WarningBanner
    aim_crosshair: AimCrosshair
    mother_ship_integrator: GameIntegrator
    give_up_detector: GiveUpDetector
    give_up_ui: GiveUpUI
    homecoming_coordinator: HomecomingCoordinator
    homecoming_detector: HomecomingDetector
    homecoming_sequence: HomecomingSequence
    homecoming_ui: HomecomingUI
    base_talent_console: BaseTalentConsole
    bullet_manager: BulletManager
    boss_manager: BossManager
    milestone_manager: MilestoneManager
    input_coordinator: InputCoordinator
    ui_manager: UIManager
    game_loop_manager: GameLoopManager
    scene_renderer: GameSceneRenderer


__all__ = ["GameSession"]
