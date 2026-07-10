"""Construct the typed collaborators for one active game session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.config import BOOST_CONFIG, DIFFICULTY_SETTINGS
from airwar.entities import Player
from airwar.game.constants import PlayerConstants
from airwar.game.give_up import GiveUpDetector
from airwar.game.homecoming import HomecomingDetector, HomecomingSequence
from airwar.game.managers import (
    BossManager,
    BulletManager,
    GameLoopManager,
    InputCoordinator,
    MilestoneManager,
    UIManager,
)
from airwar.game.managers.collision_controller import CollisionController
from airwar.game.managers.game_controller import GameController
from airwar.game.managers.spawn_controller import SpawnController
from airwar.game.mother_ship import (
    EventBus,
    GameIntegrator,
    InputDetector,
    MotherShip,
    MotherShipStateMachine,
    ProgressBarUI,
)
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator
from airwar.input import PygameInputHandler
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.base_talent_console import BaseTalentConsole
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.give_up_ui import GiveUpUI
from airwar.ui.homecoming_ui import HomecomingUI
from airwar.ui.warning_banner import WarningBanner

from .game_scene_renderer import GameSceneRenderer
from .game_session import GameSession

if TYPE_CHECKING:
    from .game_scene import GameScene


class GameSceneFactory:
    """Build a ``GameSession`` without making ``GameScene`` its state store."""

    def build(
        self,
        scene: GameScene,
        screen_width: int,
        screen_height: int,
        kwargs: dict,
    ) -> GameSession:
        difficulty = kwargs.get("difficulty", "medium")
        username = kwargs.get("username", "Player")
        settings_ref = kwargs.get("settings_ref", {})
        settings = DIFFICULTY_SETTINGS[difficulty]

        game_controller = GameController(difficulty, username)
        game_controller.set_lock_manager(scene._lock_manager)
        scene._lock_manager.set_game_state(game_controller.state)

        game_renderer = GameRenderer()
        game_renderer.init_background(screen_width, screen_height)
        reward_system = game_controller.reward_system
        hud_renderer = HUDRenderer()
        notification_manager = game_controller.notification_manager

        spawn_controller = SpawnController(settings)
        spawn_controller.init_bullet_system()
        collision_controller = CollisionController()

        player = Player(
            screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET,
            screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET,
            PygameInputHandler(),
        )
        scene._lock_manager.set_player(player)
        player.set_aim_target(*scene._aim_assist.get_aim_position())
        player.rect.y = PlayerConstants.INITIAL_Y
        player.bullet_damage = settings["bullet_damage"]
        boost_cfg = BOOST_CONFIG[difficulty]
        player.boost_max = boost_cfg["max_boost"]
        player.boost_current = boost_cfg["max_boost"]
        player.boost_recovery_rate = boost_cfg["recovery_rate"]
        player.boost_speed_mult = boost_cfg["speed_mult"]
        player.boost_recovery_delay = boost_cfg["recovery_delay"]
        player.boost_recovery_ramp = boost_cfg["recovery_ramp"]
        player.apply_settings(settings_ref)
        reward_system.capture_player_baselines(player)

        reward_selector = scene.reward_selector
        setattr(
            reward_selector,
            "hide",
            lambda: setattr(reward_selector, "visible", False),
        )
        reward_selector.visible = False
        boost_gauge = BoostGauge()
        ammo_magazine = AmmoMagazine()
        warning_banner = WarningBanner()
        aim_crosshair = AimCrosshair()

        event_bus = EventBus()
        mother_ship_integrator = GameIntegrator(
            event_bus=event_bus,
            input_detector=InputDetector(event_bus),
            state_machine=MotherShipStateMachine(event_bus),
            progress_bar_ui=ProgressBarUI(screen_width, screen_height),
            mother_ship=MotherShip(screen_width, screen_height),
        )
        mother_ship_integrator.attach_game_scene(scene)

        give_up_detector = GiveUpDetector(scene._on_give_up_complete)
        give_up_ui = GiveUpUI(screen_width)

        homecoming_detector = HomecomingDetector(scene._on_homecoming_requested)
        homecoming_sequence = HomecomingSequence(scene._on_homecoming_complete)
        homecoming_ui = HomecomingUI(screen_width, screen_height)
        base_talent_console = BaseTalentConsole(screen_width, screen_height)
        homecoming_coordinator = HomecomingCoordinator(
            homecoming_detector,
            homecoming_sequence,
            homecoming_ui,
            base_talent_console,
        )
        homecoming_coordinator.set_save_fn(scene._save_base_loadout)

        bullet_manager = BulletManager(player, spawn_controller)
        boss_manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
        milestone_manager = MilestoneManager(game_controller, reward_system)
        milestone_manager.set_reward_selector(reward_selector)
        input_coordinator = InputCoordinator(
            player,
            game_controller,
            reward_selector,
            give_up_detector,
            give_up_ui,
        )
        ui_manager = UIManager(game_renderer, game_controller, reward_system)
        game_loop_manager = GameLoopManager(
            game_controller,
            game_renderer,
            spawn_controller,
            reward_system,
            bullet_manager,
            boss_manager,
            collision_controller,
            scene._lock_manager,
        )

        return GameSession(
            game_controller=game_controller,
            game_renderer=game_renderer,
            reward_system=reward_system,
            hud_renderer=hud_renderer,
            notification_manager=notification_manager,
            spawn_controller=spawn_controller,
            collision_controller=collision_controller,
            player=player,
            reward_selector=reward_selector,
            boost_gauge=boost_gauge,
            ammo_magazine=ammo_magazine,
            warning_banner=warning_banner,
            aim_crosshair=aim_crosshair,
            mother_ship_integrator=mother_ship_integrator,
            give_up_detector=give_up_detector,
            give_up_ui=give_up_ui,
            homecoming_coordinator=homecoming_coordinator,
            homecoming_detector=homecoming_detector,
            homecoming_sequence=homecoming_sequence,
            homecoming_ui=homecoming_ui,
            base_talent_console=base_talent_console,
            bullet_manager=bullet_manager,
            boss_manager=boss_manager,
            milestone_manager=milestone_manager,
            input_coordinator=input_coordinator,
            ui_manager=ui_manager,
            game_loop_manager=game_loop_manager,
            scene_renderer=GameSceneRenderer(scene),
        )


__all__ = ["GameSceneFactory"]
