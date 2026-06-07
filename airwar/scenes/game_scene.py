"""Main game scene - gameplay loop, entity coordination, and rendering.

Phase42.2 god-class split: GameScene is now a thin coordinator.
The53 IGameScene forwarders live on IGameSceneAdapter
(see game_scene_protocol_adapter.py). The heavy enter() subsystem
construction lives on GameSceneFactory
(see game_scene_factory.py). The scene keeps:
 - Lifecycle: enter, exit, handle_events, update, render
 - State queries: is_* predicates
 - IGameScene Protocol conformance (53 public methods)
 - Property accessors with setters
 - The __setattr__ hook that keeps the F07 dispatcher in sync
"""

import pygame

from airwar.config import get_screen_height, get_screen_width
from airwar.config.design_tokens import get_design_tokens
from airwar.entities import Player
from airwar.game.constants import GAME_CONSTANTS
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
from airwar.game.managers.game_controller import GameController, GameplayState
from airwar.game.managers.spawn_controller import SpawnController
from airwar.game.mother_ship import (
 EventBus,
 GameIntegrator,
 InputDetector,
 MotherShip,
 MotherShipState,
 MotherShipStateMachine,
 PersistenceManager,
 ProgressBarUI,
)
from airwar.game.mother_ship.interfaces import IGameScene
from airwar.game.rendering.boss_enrage_renderer import BossEnrageRenderer
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.game.rendering.haunting_renderer import HauntingRenderer
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.systems.aim_assist_system import AimAssistSystem
from airwar.game.systems.lock_manager import LockLayer, LockManager, LockRequest
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.save_restore_manager import SaveRestoreManager
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.base_talent_console import BaseTalentConsole
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.give_up_ui import GiveUpUI
from airwar.ui.homecoming_ui import HomecomingUI
from airwar.ui.pause_button import PauseButtonComponent
from airwar.ui.reward_selector import RewardSelector
from airwar.ui.warning_banner import WarningBanner
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches

from .game_scene_factory import GameSceneFactory
from .game_scene_protocol_adapter import IGameSceneAdapter
from .game_scene_renderer import GameSceneRenderer
from .scene import Scene


class GameScene(Scene, MouseInteractiveMixin, IGameScene):
 """Main game scene controller.

 GameScene delegates:
  - The53 IGameScene forwarders to self._protocol (IGameSceneAdapter)
  - The enter() construction to self._factory.build (GameSceneFactory)
  - Per-frame rendering to self._scene_renderer (GameSceneRenderer)

 Update pipeline: see airwar.scenes.update_pipeline.PIPELINE_ORDER.
 """

 PAUSE_BUTTON_SIZE = PauseButtonComponent.PAUSE_BUTTON_SIZE
 PAUSE_BUTTON_MARGIN = PauseButtonComponent.PAUSE_BUTTON_MARGIN
 PAUSE_BAR_WIDTH = PauseButtonComponent.PAUSE_BAR_WIDTH
 PAUSE_BAR_HEIGHT = PauseButtonComponent.PAUSE_BAR_HEIGHT
 PAUSE_BAR_GAP = PauseButtonComponent.PAUSE_BAR_GAP
 AIM_ASSIST_BREAK_DISTANCE = AimAssistSystem.AIM_ASSIST_BREAK_DISTANCE
 AIM_ASSIST_SWITCH_DISTANCE = AimAssistSystem.AIM_ASSIST_SWITCH_DISTANCE
 AIM_ASSIST_RELEASE_DISTANCE = AimAssistSystem.AIM_ASSIST_RELEASE_DISTANCE
 AIM_ASSIST_DIRECTION_CONE_DOT = AimAssistSystem.AIM_ASSIST_DIRECTION_CONE_DOT
 AIM_INPUT_DELAY_BLEND = AimAssistSystem.AIM_INPUT_DELAY_BLEND
 AIM_INPUT_SNAP_DISTANCE = AimAssistSystem.AIM_INPUT_SNAP_DISTANCE
 PERMANENT_INVINCIBILITY_FRAMES = GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES
 DOCKING_INVINCIBILITY_FRAMES = GAME_CONSTANTS.PERSISTENCE.DOCKING_INVINCIBILITY_FRAMES

 AUTO_SAVE_INTERVAL = GAME_CONSTANTS.PERSISTENCE.AUTO_SAVE_INTERVAL
 BULLET_CLEAR_DEDUP_FRAMES = GAME_CONSTANTS.PERSISTENCE.BULLET_CLEAR_DEDUP_FRAMES

 def __init__(self):
  Scene.__init__(self)
  MouseInteractiveMixin.__init__(self)
  self._pause_requested = False
  self._is_loading = True
  self._loading_progress =0
  self._tokens = get_design_tokens()
  self._pause_button = PauseButtonComponent()
  self._aim_assist = AimAssistSystem()
  self._boss_enrage_renderer = BossEnrageRenderer()
  self._haunting_renderer: HauntingRenderer | None = None
  self._save_restore_manager = SaveRestoreManager()
  self._lock_manager = LockManager(None)
  self._protocol = IGameSceneAdapter(self)
  self._factory = GameSceneFactory()
  self.game_controller: GameController | None = None
  self.game_renderer: GameRenderer = None
  self.health_system = None
  self.reward_system: RewardSystem = None
  self.hud_renderer: HUDRenderer = None
  self.notification_manager: NotificationManager = None
  self.spawn_controller: SpawnController = None
  self.collision_controller: CollisionController = None
  self.player: Player = None
  self.reward_selector: RewardSelector = RewardSelector()
  self._mother_ship_integrator = None
  self._ammo_magazine: AmmoMagazine = None
  self._warning_banner: WarningBanner = None
  self._boost_gauge: BoostGauge = None
  self._aim_crosshair = AimCrosshair()
  self._give_up_detector = None
  self._give_up_ui = None
  self._homecoming_coordinator = None
  self._homecoming_dispatcher = None
  self._homecoming_detector = None
  self._homecoming_sequence = None
  self._homecoming_ui = None
  self._homecoming_base_pending = False
  self._base_talent_console = None
  self._talent_balance_manager = None
  self._bullet_manager: BulletManager = None
  self._boss_manager: BossManager = None
  self._milestone_manager: MilestoneManager = None
  self._input_coordinator: InputCoordinator = None
  self._ui_manager: UIManager = None
  self._game_loop_manager: GameLoopManager = None
  self._scene_renderer: GameSceneRenderer = None
  self._viewport = None
  self._phase_dash_invincibility_active = False
  self._survival_frames =0
  self._last_bullet_clear_frame = GAME_CONSTANTS.GAMEPLAY.bullet_clear_dedup_initial_frame()
 def enter(self, **kwargs) -> None:
  """Initialize the game scene via GameSceneFactory."""
  self._pause_requested = False
  self._is_loading = True
  self._loading_progress =0
  self.clear_hover()
  self.clear_buttons()
  self._pause_button.clear_cache()
  self._lock_manager.clear()
  self._phase_dash_invincibility_active = False
  if self._haunting_renderer:
   self._haunting_renderer.dispose()
  self._haunting_renderer = HauntingRenderer()
  self._viewport = kwargs.get("viewport")

  # Prewarm glow caches before gameplay starts
  self._loading_progress =20
  prewarm_glow_caches()
  prewarm_ship_sprite_caches()
  self._loading_progress =100
  self._is_loading = False

  screen_width = get_screen_width()
  screen_height = get_screen_height()
  self._init_pause_button_layout()
  self._aim_assist.set_raw_aim_position(self._get_logical_mouse_pos())

  self._factory.build(self, screen_width, screen_height, kwargs)
  self._auto_save_timer =0

 def _setup_reward_selector(self) -> None:
  self.reward_selector.hide = lambda: setattr(self.reward_selector, "visible", False)
  self.reward_selector.visible = False

 def _init_mother_ship_system(self, screen_width: int, screen_height: int) -> None:
  event_bus = EventBus()
  input_detector = InputDetector(event_bus)
  state_machine = MotherShipStateMachine(event_bus)
  persistence_manager = PersistenceManager(username=self.get_username())
  progress_bar_ui = ProgressBarUI(screen_width, screen_height)
  mother_ship = MotherShip(screen_width, screen_height)

  self._mother_ship_integrator = GameIntegrator(
   event_bus=event_bus,
   input_detector=input_detector,
   state_machine=state_machine,
   persistence_manager=persistence_manager,
   progress_bar_ui=progress_bar_ui,
   mother_ship=mother_ship,
  )
  self._mother_ship_integrator.attach_game_scene(self)

 def _init_give_up_system(self, screen_width: int, screen_height: int) -> None:
  self._give_up_detector = GiveUpDetector(self._on_give_up_complete)
  self._give_up_ui = GiveUpUI(screen_width, screen_height)

 def _init_homecoming_system(self, screen_width: int, screen_height: int) -> None:
  from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator

  detector = HomecomingDetector(self._on_homecoming_requested)
  sequence = HomecomingSequence(self._on_homecoming_complete)
  ui = HomecomingUI(screen_width, screen_height)
  console = BaseTalentConsole(screen_width, screen_height)
  coordinator = HomecomingCoordinator(detector, sequence, ui, console)
  # F07: SceneHomecomingDispatcher owns the8 callback methods.
  self._set_homecoming_coordinator(coordinator)
  self._homecoming_coordinator.set_save_fn(self._save_base_loadout)
  self._homecoming_detector = detector
  self._homecoming_sequence = sequence
  self._homecoming_ui = ui
  self._base_talent_console = console
  self._talent_balance_manager = None
  self._homecoming_base_pending = False

 def exit(self) -> None:
  if self._haunting_renderer:
   self._haunting_renderer.dispose()
   self._haunting_renderer = None

 def handle_events(self, event: pygame.event.Event) -> None:
  """Process input events."""
  self._input_coordinator.handle_events(event)

  if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
   if self.game_renderer.integrated_hud:
    self.game_renderer.integrated_hud.toggle()
  elif event.type == pygame.MOUSEMOTION:
   self._aim_assist.set_raw_aim_position(event.pos)
   self._sync_player_aim_target()
   if self._homecoming_base_pending and self._base_talent_console:
    self._base_talent_console.handle_mouse_motion(event.pos)
   self.handle_mouse_motion(event.pos)
  elif event.type == pygame.MOUSEBUTTONDOWN:
   self._aim_assist.set_raw_aim_position(event.pos)
   self._sync_player_aim_target()
   if event.button ==1 and self._homecoming_base_pending and self._handle_base_console_click(event.pos):
    return
   if event.button ==1 and self.handle_mouse_click(event.pos):
    self._handle_button_click(self.get_hovered_button())

 def _handle_button_click(self, button_name: str) -> None:
  """Handle mouse button click events."""
  if button_name == "pause":
   self._pause_requested = True

 def _get_logical_mouse_pos(self) -> tuple[float, float]:
  pos = pygame.mouse.get_pos()
  if self._viewport:
   return self._viewport.screen_to_logical(*pos)
  return pos

 def consume_pause_request(self) -> bool:
  """Consume the pause request flag."""
  if self.is_homecoming_locked():
   self._pause_requested = False
   return False
  if self._pause_requested:
   self._pause_requested = False
   return True
  return False

 def update(self, *args, **kwargs) -> None:
  """Update order: see airwar.scenes.update_pipeline.PIPELINE_ORDER."""
  self.reward_selector.update()
  if self._homecoming_coordinator:
   self._homecoming_coordinator.update_base(self.game_controller, self.notification_manager)
  self._aim_assist.update(self.spawn_controller, self._get_logical_mouse_pos())
  self._sync_player_aim_target()
  self._aim_crosshair.update()
  self._update_homecoming()

  if self.game_renderer and self.game_renderer.integrated_hud:
   unlocked_buffs = getattr(self.reward_system, "unlocked_buffs", [])
   self.game_renderer.integrated_hud.update_scroll(len(unlocked_buffs))
   if self.player:
    self.game_renderer.integrated_hud.update_health_tank(self.player.health, self.player.max_health)
   self.game_renderer.integrated_hud.update()

  if self._is_homecoming_active():
   return

  # Always update warning banner scroll animation
  if self._warning_banner:
   self._warning_banner.update()

  if self._game_loop_manager.is_entrance_playing():
   self._game_loop_manager.update_entrance(self.player)
   if self._mother_ship_integrator:
    self._mother_ship_integrator.update()
   return

  is_dying = self.game_controller.state.gameplay_state == GameplayState.DYING

  if is_dying:
   self._game_loop_manager.update_game(self.player)
   return

  if self.game_controller.state.is_paused or self.reward_selector.visible:
   return

  docked = False
  if self._mother_ship_integrator:
   self._mother_ship_integrator.update()
   docked = self._mother_ship_integrator.is_docked()

  self._update_mothership_ammo_warning()

  self._input_coordinator.update_give_up()
  self._game_loop_manager.update_game(self.player)

  # During docked state, lock player at docking position
  if docked:
   dock_pos = self._mother_ship_integrator.get_docking_position()
   self.player.rect.x = dock_pos[0] - self.player.rect.width //2
   self.player.rect.y = dock_pos[1] - self.player.rect.height //2

  self._sync_player_phase_dash_invincibility()

  self._game_loop_manager.check_collisions(
   self.player,
   self.spawn_controller.enemy_bullets,
   self._on_player_damaged,
  )

  # Post-collision cleanup
  self.spawn_controller.cleanup()
  self._bullet_manager.cleanup()
  self.player.cleanup_inactive_bullets()

  self._milestone_manager.check_and_trigger(self.player)

  self._survival_frames +=1
  self._update_haunting_effect()
  self._auto_save_timer +=1
  if self._auto_save_timer >= self.AUTO_SAVE_INTERVAL:
   self._auto_save_timer =0
   self._try_auto_save()

 def _update_haunting_effect(self) -> None:
  if not self._haunting_renderer or not self.spawn_controller:
   return
  enemy_pressure = len(self.spawn_controller.enemies)
  if self.spawn_controller.boss:
   enemy_pressure +=3
  if self.spawn_controller.enemy_bullets:
   enemy_pressure += min(8, len(self.spawn_controller.enemy_bullets) //6)
  self._haunting_renderer.update(enemy_pressure)

 def _should_suppress_haunting(self) -> bool:
  """Suppress haunting visuals when player is inside or near mothership."""
  if not self._mother_ship_integrator:
   return False
  state = self._mother_ship_integrator.get_current_state()
  return state in (
   MotherShipState.ENTERING,
   MotherShipState.DOCKING,
   MotherShipState.DOCKED,
   MotherShipState.UNDOCKING,
  )

 def _render_haunting_world(self, surface: pygame.Surface) -> None:
  """Render haunting world-style pass (before bullets)."""
  if not self._haunting_renderer or self._should_suppress_haunting():
   return
  self._haunting_renderer.render_world_styles(
   surface,
   self.player,
   self.spawn_controller.enemies,
   self.spawn_controller.boss,
  )

 def _render_haunting_post_bullets(self, surface: pygame.Surface) -> None:
  """Render haunting projectile styles, distortion, and atmosphere overlay."""
  if not self._haunting_renderer or self._should_suppress_haunting():
   return
  self._haunting_renderer.render_projectile_styles(
   surface,
   self.player.get_bullets(),
   self.spawn_controller.enemy_bullets,
  )
  self._haunting_renderer.distort_world(surface)
  self._haunting_renderer.render_atmosphere_overlay(surface)

 def _render_haunting_foreground(self, surface: pygame.Surface) -> None:
  """Render haunting UI corruption overlay above HUD elements."""
  if not self._haunting_renderer or self._should_suppress_haunting():
   return
  self._haunting_renderer.render_foreground_distortion(
   surface,
   self.game_controller.state if self.game_controller else None,
   self.player,
  )

 def _try_auto_save(self) -> None:
  """Periodic auto-save while game is running normally."""
  if not self._mother_ship_integrator:
   return
  if self._mother_ship_integrator.is_docked():
   return
  if not self.game_controller or not self.game_controller.is_playing():
   return
  save_data = self._mother_ship_integrator.create_save_data()
  if save_data:
   save_data.is_in_mothership = False
   PersistenceManager(username=save_data.username).save_game(save_data)

 def _sync_player_phase_dash_invincibility(self) -> None:
  if not self.game_controller or not self.player:
   return

  self._sync_lock_manager_targets()
  if self.player.is_phase_dash_invincible():
   self._phase_dash_invincibility_active = True
   self._lock_manager.acquire(
    LockLayer.PHASE_DASH,
    LockRequest(invincible=True, is_silent_invincible=True, invincibility_duration=2),
   )
   return

  if not self._phase_dash_invincibility_active:
   return

  self._phase_dash_invincibility_active = False
  self._lock_manager.release(LockLayer.PHASE_DASH)

 def _activate_invincibility(self) -> None:
  self._sync_lock_manager_targets()
  self._lock_manager.acquire(
   LockLayer.MOTHERSHIP,
   LockRequest(
    invincible=True,
    lock_controls=True,
    is_silent_invincible=True,
    invincibility_duration=self.PERMANENT_INVINCIBILITY_FRAMES,
   ),
  )

 def _deactivate_invincibility(self) -> None:
  self._sync_lock_manager_targets()
  self._lock_manager.release(LockLayer.MOTHERSHIP)

 def _update_mothership_ammo_warning(self) -> None:
  """Check ammo level and activate warning banner when critically low."""
  if not self._mother_ship_integrator or not self._warning_banner:
   return

  status = self._mother_ship_integrator.get_status_data()
  if not status.get("ammo_warning", False):
   return

  if self._warning_banner.is_active:
   return

  def trigger_undock():
   from airwar.game.mother_ship.event_bus import EVENT_UNDOCK_REQUESTED
   bus = self.event_bus
   assert bus is not None, (
    "F02 D5: warning_banner.on_complete requires the EventBus "
    "to be wired (publishes EVENT_UNDOCK_REQUESTED)."
   )
   bus.publish(EVENT_UNDOCK_REQUESTED)

  self._warning_banner.activate(on_complete=trigger_undock)

 BULLET_CLEAR_RADIUS = (
  GAME_CONSTANTS.PERSISTENCE.BULLET_CLEAR_RADIUS
 ) # px; clear enemy bullets within this radius on player hit

 def _on_player_damaged(self, damage: int, player) -> None:
  """Handle player hit: apply damage, clear nearby enemy bullets."""
  self.game_controller.on_player_hit(damage, player)
  self._clear_nearby_enemy_bullets(player)

 def _clear_nearby_enemy_bullets(self, player) -> None:
  """Clear enemy bullets within BULLET_CLEAR_RADIUS of the player after being hit."""
  if not self.spawn_controller:
   return
  if self._survival_frames - self._last_bullet_clear_frame < self.BULLET_CLEAR_DEDUP_FRAMES:
   return
  self._last_bullet_clear_frame = self._survival_frames
  px = player.rect.centerx
  py = player.rect.centery
  r2 = self.BULLET_CLEAR_RADIUS * self.BULLET_CLEAR_RADIUS
  for bullet in self.spawn_controller.enemy_bullets:
   if not bullet.active:
    continue
   dx = bullet.rect.centerx - px
   dy = bullet.rect.centery - py
   if dx * dx + dy * dy <= r2:
    bullet.active = False

 def _on_give_up_complete(self) -> None:
  self.game_controller.on_player_hit(GAME_CONSTANTS.DAMAGE.INSTANT_KILL, self.player)

 def _set_homecoming_coordinator(self, coordinator) -> None:
  """Set the homecoming coordinator and (re)create the dispatcher."""
  from .scene_homecoming_dispatcher import SceneHomecomingDispatcher

  # F07 F09: bypass __setattr__ hook by writing through base class.
  object.__setattr__(self, "_homecoming_coordinator", coordinator)
  object.__setattr__(
   self,
   "_homecoming_dispatcher",
   (
    SceneHomecomingDispatcher(coordinator=coordinator, scene=self)
    if coordinator is not None
    else None
   ),
  )

 def __setattr__(self, name: str, value: object) -> None:
  """F07 F09: keep dispatcher in sync with direct coordinator writes."""
  if name == "_homecoming_coordinator":
   self._set_homecoming_coordinator(value)
   return
  object.__setattr__(self, name, value)

 def _update_homecoming(self) -> None:
  """Backward-compat forwarder to SceneHomecomingDispatcher."""
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.update()

 def _on_homecoming_requested(self) -> None:
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.on_requested()

 def _on_homecoming_complete(self) -> None:
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.on_complete()

 def _handle_base_console_click(self, pos: tuple[int, int]) -> bool:
  if self._homecoming_dispatcher is None:
   return False
  return self._homecoming_dispatcher.handle_console_click(pos)

 def _leave_homecoming_base(self) -> None:
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.leave_base()

 def _on_homecoming_orbital_strike(self) -> None:
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.on_orbital_strike()

 def _on_homecoming_departure_complete(self) -> None:
  if self._homecoming_dispatcher is not None:
   self._homecoming_dispatcher.on_departure_complete()
   self._homecoming_base_pending = self._homecoming_coordinator.is_base_pending()

 def _save_base_loadout(self) -> bool:
  if not self._mother_ship_integrator:
   return False
  save_data = self._mother_ship_integrator.create_save_data()
  if not save_data:
   return False
  save_data.is_in_mothership = False
  return PersistenceManager(username=save_data.username).save_game(save_data)

 def _sync_lock_manager_targets(self) -> None:
  if self.game_controller:
   self._lock_manager.set_game_state(self.game_controller.state)
  if self.player:
   self._lock_manager.set_player(self.player)

 def acquire_lock(self, layer: LockLayer, request: LockRequest) -> None:
  """Acquire a lock layer via the centralized LockManager."""
  self._sync_lock_manager_targets()
  self._lock_manager.acquire(layer, request)

 def release_lock(self, layer: LockLayer) -> None:
  """Release a lock layer via the centralized LockManager."""
  self._sync_lock_manager_targets()
  self._lock_manager.release(layer)

 def _is_homecoming_active(self) -> bool:
  # F02 D6: HomecomingCoordinator is the single source of truth.
  if self._homecoming_coordinator is None:
   return False
  return self._homecoming_coordinator.is_active()

 def is_homecoming_active(self) -> bool:
  return self._is_homecoming_active()

 def is_homecoming_locked(self) -> bool:
  if self._homecoming_coordinator is None:
   return False
  return self._homecoming_coordinator.is_locked()

 def is_homecoming_complete(self) -> bool:
  if self._homecoming_coordinator is None:
   return False
  return self._homecoming_coordinator.is_base_pending()

 def render(self, surface: pygame.Surface) -> None:
  """Render via GameSceneRenderer."""
  self._scene_renderer.render(surface)

 def _sync_player_aim_target(self) -> None:
  if self.player:
   self.player.set_aim_target(*self._aim_assist.get_aim_position())

 def _render_aim_crosshair(self, surface: pygame.Surface) -> None:
  if not self.game_controller or not self.game_controller.is_playing():
   return
  if self.game_controller.state.is_paused:
   return
  if self.reward_selector and self.reward_selector.visible:
   return
  self._aim_crosshair.render(surface, self._aim_assist.get_aim_position())

 def _init_pause_button_layout(self) -> None:
  self._pause_button.init_layout(self.register_button)

 def _render_pause_button(self, surface: pygame.Surface) -> None:
  """Render the pause button."""
  if not self.game_controller or self.game_controller.state.is_paused:
   return
  if self.reward_selector and self.reward_selector.visible:
   return
  is_hovered = self.is_button_hovered("pause")
  self._pause_button.render(surface, is_hovered, self._tokens.colors, self._tokens.spacing)

 @property
 def score(self) -> int:
  """Get the current score."""
  return self.game_controller.state.score if self.game_controller else 0

 @score.setter
 def score(self, value: int) -> None:
  """Set the current score."""
  if self.game_controller:
   self.game_controller.set_score(value)

 @property
 def cycle_count(self) -> int:
  """Get the current cycle count."""
  return self.game_controller.state.cycle_count if self.game_controller else 0

 @cycle_count.setter
 def cycle_count(self, value: int) -> None:
  """Set the cycle count."""
  if self.game_controller:
   self.game_controller.set_cycle_count(value)

 def is_game_over(self) -> bool:
  """Check if the game is over."""
  if not self.player:
   return True
  if not self.game_controller:
   return True
  return self.game_controller.is_game_over()

 def pause(self) -> None:
  """Pause the game."""
  if self.is_homecoming_locked():
   return
  if self.game_controller and not self.reward_selector.visible:
   self.game_controller.set_paused(True)

 def resume(self) -> None:
  """Resume the game."""
  if self.is_homecoming_locked():
   return
  if self.game_controller:
   self.game_controller.set_paused(False)

 @property
 def paused(self) -> bool:
  """Get the game paused state."""
  return self.game_controller.state.is_paused if self.game_controller else False

 @property
 def unlocked_buffs(self) -> list:
  """Get the list of unlocked buffs."""
  return self.reward_system.unlocked_buffs if self.reward_system else []

 @unlocked_buffs.setter
 def unlocked_buffs(self, value: list) -> None:
  """Set the list of unlocked buffs."""
  if self.reward_system:
   self.reward_system.unlocked_buffs = value

 @property
 def difficulty(self) -> str:
  """Get the game difficulty."""
  return self.game_controller.state.difficulty if self.game_controller else "medium"

 @difficulty.setter
 def difficulty(self, value: str) -> None:
  """Set the game difficulty."""
  if self.game_controller:
   self.game_controller.set_difficulty(value)

 def restore_from_save(self, save_data) -> None:
  """Restore game state from save data."""
  self._save_restore_manager.restore(
   save_data,
   self.game_controller,
   self.player,
   self.reward_system,
   self.spawn_controller,
   self._mother_ship_integrator,
  )

 def create_save_data(self):
  """Create save data snapshot, or None if mothership not available."""
  if not self._mother_ship_integrator:
   return None
  return self._mother_ship_integrator.create_save_data()

 def is_mothership_docked(self) -> bool:
  if not self._mother_ship_integrator:
   return False
  return self._mother_ship_integrator.is_docked()

 @property
 def event_bus(self) -> EventBus | None:
  """Expose the in-game event bus for achievement integration."""
  if not self._mother_ship_integrator:
   return None
  return self._mother_ship_integrator.event_bus

 # IGameScene forwarders - all1-line delegations to self._protocol

 def set_player_position(self, x: float, y: float) -> None:
  return self._protocol.set_player_position(x, y)

 def set_player_position_topleft(self, x: float, y: float) -> None:
  return self._protocol.set_player_position_topleft(x, y)

 def trigger_explosion(self, x: float, y: float, radius: int) -> None:
  return self._protocol.trigger_explosion(x, y, radius)

 def trigger_boss_death_explosion(self, boss) -> None:
  return self._protocol.trigger_boss_death_explosion(boss)

 def add_score(self, amount: int) -> None:
  return self._protocol.add_score(amount)

 def add_kill(self) -> None:
  return self._protocol.add_kill()

 def add_boss_kill(self) -> None:
  return self._protocol.add_boss_kill()

 def show_notification(self, message: str) -> None:
  return self._protocol.show_notification(message)

 def get_enemies(self) -> list:
  return self._protocol.get_enemies()

 def get_boss(self):
  return self._protocol.get_boss()

 def clear_boss(self) -> None:
  return self._protocol.clear_boss()

 def set_player_invincible(self, invincible: bool, timer: int, silent: bool = False) -> None:
  return self._protocol.set_player_invincible(invincible, timer, silent)

 def get_score(self) -> int:
  return self._protocol.get_score()

 def get_cycle_count(self) -> int:
  return self._protocol.get_cycle_count()

 def get_kill_count(self) -> int:
  return self._protocol.get_kill_count()

 def get_boss_kill_count(self) -> int:
  return self._protocol.get_boss_kill_count()

 def get_unlocked_buffs(self) -> list:
  return self._protocol.get_unlocked_buffs()

 def get_buff_levels(self) -> dict[str, int]:
  return self._protocol.get_buff_levels()

 def get_earned_buff_levels(self) -> dict[str, int]:
  return self._protocol.get_earned_buff_levels()

 def get_talent_loadout(self) -> dict[str, str]:
  return self._protocol.get_talent_loadout()

 def get_player_health(self) -> int:
  return self._protocol.get_player_health()

 def get_player_max_health(self) -> int:
  return self._protocol.get_player_max_health()

 def get_difficulty(self) -> str:
  return self._protocol.get_difficulty()

 def get_username(self) -> str:
  return self._protocol.get_username()

 def set_paused(self, paused: bool) -> None:
  return self._protocol.set_paused(paused)

 def clear_ripple_effects(self) -> None:
  return self._protocol.clear_ripple_effects()
