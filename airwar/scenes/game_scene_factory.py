"""GameScene factory - Phase42.2 god-class split.

Extracts the enter() subsystem construction logic into a dedicated
factory. The factory builds every subsystem the scene needs,
returning a typed dict the scene attaches to itself.

Construction order (1:1 with the original enter() body):
1. game_controller
2. game_renderer
3. hud_renderer
4. spawn_controller
5. collision_controller
6. player (with boost + reward baselines)
7. UI components
8. _setup_reward_selector
9. Subsystem groups (mothership, give-up, homecoming)
10. Managers (bullet, boss, milestone, input, ui, game_loop)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.config import BOOST_CONFIG, DIFFICULTY_SETTINGS
from airwar.entities import Player
from airwar.game.constants import PlayerConstants
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
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.input import PygameInputHandler
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.warning_banner import WarningBanner

if TYPE_CHECKING:
 from .game_scene import GameScene
from .game_scene_renderer import GameSceneRenderer


class GameSceneFactory:
 """Builds every subsystem wired into a GameScene during enter()."""

 def build(
  self,
  scene: GameScene,
  screen_width: int,
  screen_height: int,
  kwargs: dict,
 ) -> dict[str, object]:
  difficulty = kwargs.get("difficulty", "medium")
  username = kwargs.get("username", "Player")
  settings_ref = kwargs.get("settings_ref", {})
  settings = DIFFICULTY_SETTINGS[difficulty]

  # Core game systems
  scene.game_controller = GameController(difficulty, username)
  scene.game_controller.set_lock_manager(scene._lock_manager)
  scene._lock_manager.set_game_state(scene.game_controller.state)

  scene.game_renderer = GameRenderer()
  scene.game_renderer.init_background(screen_width, screen_height)

  scene.reward_system = scene.game_controller.reward_system
  scene.hud_renderer = HUDRenderer()
  scene.notification_manager = scene.game_controller.notification_manager

  scene.spawn_controller = SpawnController(settings)
  scene.spawn_controller.init_bullet_system()

  scene.collision_controller = CollisionController()

  input_handler = PygameInputHandler()
  scene.player = Player(
   screen_width //2 - PlayerConstants.INITIAL_X_OFFSET,
   screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET,
   input_handler,
  )
  scene._lock_manager.set_player(scene.player)
  scene._sync_player_aim_target()
  scene.player.rect.y = PlayerConstants.INITIAL_Y
  scene.player.bullet_damage = settings["bullet_damage"]
  boost_cfg = BOOST_CONFIG[difficulty]
  scene.player.boost_max = boost_cfg["max_boost"]
  scene.player.boost_current = boost_cfg["max_boost"]
  scene.player.boost_recovery_rate = boost_cfg["recovery_rate"]
  scene.player.boost_speed_mult = boost_cfg["speed_mult"]
  scene.player.boost_recovery_delay = boost_cfg["recovery_delay"]
  scene.player.boost_recovery_ramp = boost_cfg["recovery_ramp"]
  scene.player.apply_settings(settings_ref)
  scene.reward_system.capture_player_baselines(scene.player)

  # UI components
  scene._boost_gauge = BoostGauge()
  scene._ammo_magazine = AmmoMagazine()
  scene._warning_banner = WarningBanner()
  scene._aim_crosshair = AimCrosshair()
  scene._scene_renderer = GameSceneRenderer(scene)

  scene._setup_reward_selector()

  # Subsystem groups (delegate to scene so F07 dispatcher hook fires)
  scene._init_mother_ship_system(screen_width, screen_height)
  scene._init_give_up_system(screen_width, screen_height)
  scene._init_homecoming_system(screen_width, screen_height)

  # Managers
  scene._bullet_manager = BulletManager(scene.player, scene.spawn_controller)
  scene._boss_manager = BossManager(
   scene.spawn_controller,
   scene.game_controller,
   scene.reward_system,
   scene._bullet_manager,
  )
  scene._milestone_manager = MilestoneManager(scene.game_controller, scene.reward_system)
  scene._milestone_manager.set_reward_selector(scene.reward_selector)
  scene._input_coordinator = InputCoordinator(
   scene.player,
   scene.game_controller,
   scene.reward_selector,
   scene._give_up_detector,
   scene._give_up_ui,
  )
  scene._ui_manager = UIManager(
   scene.game_renderer,
   scene.game_controller,
   scene.reward_system,
  )
  scene._game_loop_manager = GameLoopManager(
   scene.game_controller,
   scene.game_renderer,
   scene.spawn_controller,
   scene.reward_system,
   scene._bullet_manager,
   scene._boss_manager,
   scene.collision_controller,
   scene._lock_manager,
  )

  return {
   "game_controller": scene.game_controller,
   "reward_system": scene.reward_system,
   "hud_renderer": scene.hud_renderer,
   "notification_manager": scene.notification_manager,
   "spawn_controller": scene.spawn_controller,
   "collision_controller": scene.collision_controller,
   "player": scene.player,
   "bullet_manager": scene._bullet_manager,
   "boss_manager": scene._boss_manager,
   "milestone_manager": scene._milestone_manager,
   "input_coordinator": scene._input_coordinator,
   "ui_manager": scene._ui_manager,
   "game_loop_manager": scene._game_loop_manager,
  }


__all__ = ["GameSceneFactory"]
