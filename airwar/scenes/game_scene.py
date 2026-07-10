"""Main game scene - gameplay loop, entity coordination, and rendering.

Phase 5-ε: GameScene is now a thin coordinator (≤450 lines).
The 26 IGameScene forwarders live on IGameSceneAdapter
(see game_scene_protocol_adapter.py). The heavy enter() subsystem
construction lives on GameSceneFactory
(see game_scene_factory.py). The 15-step update body lives on
GameSceneUpdater; the handle_events body lives on
GameSceneEventDispatcher; the per-frame render lives on
GameSceneRenderer. The scene keeps:
 - Lifecycle: enter, exit, handle_events, update, render
 - State queries: is_* predicates
 - IGameScene Protocol conformance (26 forwarder methods)
 - Property accessors with setters
 - The __setattr__ hook that keeps the F07 dispatcher in sync
"""

import pygame

from airwar.config import get_screen_height, get_screen_width
from airwar.config.design_tokens import get_design_tokens
from airwar.entities import Player
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.frame_context import FrameContext
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
from airwar.game.mother_ship import MotherShipState
from airwar.game.mother_ship.interfaces import IGameScene
from airwar.game.rendering.boss_enrage_renderer import BossEnrageRenderer
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.game.rendering.haunting_renderer import HauntingRenderer
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.rendering.juice_renderer import JuiceController
from airwar.game.systems.aim_assist_system import AimAssistSystem
from airwar.game.systems.game_save_service import GameSaveService
from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator
from airwar.game.systems.lock_manager import LockLayer, LockManager, LockRequest
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.save_restore_manager import SaveRestoreManager
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.pause_button import PauseButtonComponent
from airwar.ui.reward_selector import RewardSelector
from airwar.ui.warning_banner import WarningBanner
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches
from typing import Any, cast

from .game_scene_factory import GameSceneFactory
from .game_scene_protocol_adapter import IGameSceneAdapter
from .game_scene_protocols import GameSceneProtocol
from .game_scene_renderer import GameSceneRenderer
from .game_scene_event_dispatcher import GameSceneEventDispatcher
from .game_session import GameSession
from .game_scene_updater import GameSceneUpdater
from .scene import Scene


class GameScene(Scene, MouseInteractiveMixin, IGameScene):
    """Main game scene controller.

    GameScene delegates:
     - The 26 IGameScene forwarders to self._protocol (IGameSceneAdapter)
     - The enter() construction to self._factory.build (GameSceneFactory)
     - The 15-step update() body to self._updater (GameSceneUpdater)
     - The handle_events() body to self._dispatcher (GameSceneEventDispatcher)
     - Per-frame rendering to self._scene_renderer (GameSceneRenderer)

    Update pipeline: see airwar.scenes.update_pipeline.PIPELINE_ORDER.
    """

    PAUSE_BUTTON_SIZE = PauseButtonComponent.PAUSE_BUTTON_SIZE
    uses_fixed_simulation = True
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

    AUTO_SAVE_INTERVAL_SECONDS = GAME_CONSTANTS.PERSISTENCE.AUTO_SAVE_INTERVAL_SECONDS
    BULLET_CLEAR_DEDUP_FRAMES = GAME_CONSTANTS.PERSISTENCE.BULLET_CLEAR_DEDUP_FRAMES

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._pause_requested = False
        self._is_loading = True
        self._loading_progress = 0
        self._tokens = get_design_tokens()
        self._pause_button = PauseButtonComponent()
        self._aim_assist = AimAssistSystem()
        self._boss_enrage_renderer = BossEnrageRenderer()
        self._juice_controller = JuiceController()
        self._haunting_renderer: HauntingRenderer | None = None
        self._save_restore_manager = SaveRestoreManager()
        self._lock_manager = LockManager(None)
        self._protocol = IGameSceneAdapter(cast(GameSceneProtocol, self))
        self._factory = GameSceneFactory()
        self._session: GameSession | None = None
        self.game_controller: GameController | None = None
        self.game_renderer: GameRenderer = None  # type: ignore[assignment]
        self.health_system: Any = None
        self.reward_system: RewardSystem = None  # type: ignore[assignment]
        self.hud_renderer: HUDRenderer = None  # type: ignore[assignment]
        self.notification_manager: NotificationManager = None  # type: ignore[assignment]
        self.spawn_controller: SpawnController = None  # type: ignore[assignment]
        self.collision_controller: CollisionController = None  # type: ignore[assignment]
        self.player: Player = None  # type: ignore[assignment]
        self.reward_selector: RewardSelector = RewardSelector()
        self._mother_ship_integrator = None
        self._ammo_magazine: AmmoMagazine = None  # type: ignore[assignment]
        self._warning_banner: WarningBanner = None  # type: ignore[assignment]
        self._boost_gauge: BoostGauge = None  # type: ignore[assignment]
        self._aim_crosshair = AimCrosshair()
        self._give_up_detector = None
        self._give_up_ui = None
        self._homecoming_coordinator: HomecomingCoordinator | None = None
        self._homecoming_dispatcher = None
        self._homecoming_detector = None
        self._homecoming_sequence = None
        self._homecoming_ui = None
        self._homecoming_base_pending = False
        self._base_talent_console = None
        self._talent_balance_manager = None
        self._bullet_manager: BulletManager = None  # type: ignore[assignment]
        self._boss_manager: BossManager = None  # type: ignore[assignment]
        self._milestone_manager: MilestoneManager = None  # type: ignore[assignment]
        self._input_coordinator: InputCoordinator = None  # type: ignore[assignment]
        self._ui_manager: UIManager = None  # type: ignore[assignment]
        self._game_loop_manager: GameLoopManager = None  # type: ignore[assignment]
        self._scene_renderer: GameSceneRenderer = None  # type: ignore[assignment]
        self._save_service: GameSaveService | None = None
        self._viewport = None
        # Per-frame state migrated to GameSceneUpdater (Phase 5-ε):
        # _phase_dash_invincibility_active / _survival_frames /
        # _last_bullet_clear_frame / _auto_save_elapsed. Read via the
        # @property shims below; write via the updater's reset_state().
        self._updater = GameSceneUpdater(cast(GameSceneProtocol, self))
        # Per-event dispatch body extracted to GameSceneEventDispatcher
        # (Phase 5-ε). The dispatcher is stateless across frames.
        self._dispatcher = GameSceneEventDispatcher(cast(GameSceneProtocol, self))

    def enter(self, **kwargs) -> None:
        """Initialize the game scene via GameSceneFactory."""
        self._pause_requested = False
        self._is_loading = True
        self._loading_progress = 0
        self.clear_hover()
        self.clear_buttons()
        self._pause_button.clear_cache()
        self._lock_manager.clear()
        # _phase_dash_invincibility_active reset by self._updater.reset_state() below.
        if self._haunting_renderer:
            self._haunting_renderer.dispose()
        self._haunting_renderer = HauntingRenderer()
        self._viewport = kwargs.get("viewport")
        self._save_service = kwargs.get("save_service")

        # Prewarm glow caches before gameplay starts
        self._loading_progress = 20
        prewarm_glow_caches()
        prewarm_ship_sprite_caches()
        self._loading_progress = 100
        self._is_loading = False

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        self._init_pause_button_layout()
        self._aim_assist.set_raw_aim_position(self._get_logical_mouse_pos())

        self._attach_session(self._factory.build(self, screen_width, screen_height, kwargs))
        self._updater.reset_state()

    def _attach_session(self, session: GameSession) -> None:
        """Install legacy facade attributes from the typed session boundary."""
        self._session = session
        self.game_controller = session.game_controller
        self.game_renderer = session.game_renderer
        self.reward_system = session.reward_system
        self.hud_renderer = session.hud_renderer
        self.notification_manager = session.notification_manager
        self.spawn_controller = session.spawn_controller
        self.collision_controller = session.collision_controller
        self.player = session.player
        self.reward_selector = session.reward_selector
        self._boost_gauge = session.boost_gauge
        self._ammo_magazine = session.ammo_magazine
        self._warning_banner = session.warning_banner
        self._aim_crosshair = session.aim_crosshair
        self._mother_ship_integrator = session.mother_ship_integrator
        self._give_up_detector = session.give_up_detector
        self._give_up_ui = session.give_up_ui
        self._set_homecoming_coordinator(session.homecoming_coordinator)
        self._homecoming_detector = session.homecoming_detector
        self._homecoming_sequence = session.homecoming_sequence
        self._homecoming_ui = session.homecoming_ui
        self._base_talent_console = session.base_talent_console
        self._talent_balance_manager = None
        self._homecoming_base_pending = False
        self._bullet_manager = session.bullet_manager
        self._boss_manager = session.boss_manager
        self._milestone_manager = session.milestone_manager
        self._input_coordinator = session.input_coordinator
        self._ui_manager = session.ui_manager
        self._game_loop_manager = session.game_loop_manager
        self._scene_renderer = session.scene_renderer

    def exit(self) -> None:
        if self._haunting_renderer:
            self._haunting_renderer.dispose()
            self._haunting_renderer = None
        if self._scene_renderer:
            self._scene_renderer.dispose()
        _clear_module_caches()

    def handle_events(self, event: pygame.event.Event) -> None:
        """Process input events.

        Delegates to :class:`GameSceneEventDispatcher` (Phase 5-ε). The
        dispatcher is stateless; the scene owns the persistent state
        (pause request, hover, button registry, etc.).
        """
        self._dispatcher.dispatch(event)

    def _handle_button_click(self, button_name: str | None) -> None:
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

    def update(self, frame: FrameContext | None = None, *args, **kwargs) -> None:
        """Per-frame update.

        Update order: delegates to :class:`GameSceneUpdater` which owns
        the 15-step pipeline body (see
        ``airwar.scenes.update_pipeline.PIPELINE_ORDER``):

        1. reward_selector
        2. aim_assist
        3. homecoming
        4. warning_banner
        5. entrance_animation
        6. dying_animation
        7. pause_check
        8. mothership_integrator
        9. give_up_detector
        10. core_logic
        11. phase_dash_sync
        12. collision
        13. post_collision_cleanup
        14. milestone_check
        15. auto_save
        """
        self._updater.run(frame)

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

    # ---- GameSceneUpdater callbacks ----
    def _sync_player_phase_dash_invincibility(self) -> None:
        self._updater._sync_player_phase_dash_invincibility()

    def _on_give_up_complete(self) -> None:
        self._updater._on_give_up_complete()

    def _set_homecoming_coordinator(self, coordinator) -> None:
        """Set the homecoming coordinator and (re)create the dispatcher."""
        from .scene_homecoming_dispatcher import SceneHomecomingDispatcher

        # F07 F09: bypass __setattr__ hook by writing through base class.
        object.__setattr__(self, "_homecoming_coordinator", coordinator)
        object.__setattr__(
            self,
            "_homecoming_dispatcher",
            (
                SceneHomecomingDispatcher(
                    coordinator=coordinator,
                    scene=cast(GameSceneProtocol, self),
                )
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

    def _update_homecoming(self, delta_seconds: float) -> None:
        """Backward-compat forwarder to SceneHomecomingDispatcher."""
        if self._homecoming_dispatcher is not None:
            self._homecoming_dispatcher.update(delta_seconds)

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
        if self._homecoming_coordinator is not None:
            self._homecoming_base_pending = self._homecoming_coordinator.is_base_pending()

    def _save_base_loadout(self) -> bool:
        if not self._mother_ship_integrator:
            return False
        return self.save_snapshot(force_outside_mothership=True)

    def save_snapshot(self, *, force_outside_mothership: bool = False) -> bool:
        if self._save_service is None:
            return False
        save_data = self.create_save_data()
        if save_data is None:
            return False
        return self._save_service.save(save_data, force_outside_mothership=force_outside_mothership)

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

    # Read-only views over the updater's state used by scene rendering.
    @property
    def _phase_dash_invincibility_active(self) -> bool:
        return self._updater._phase_dash_invincibility_active

    @property
    def _survival_frames(self) -> int:
        return self._updater._survival_frames

    @property
    def _last_bullet_clear_frame(self) -> int:
        return self._updater._last_bullet_clear_frame

    @property
    def _auto_save_elapsed(self) -> float:
        return self._updater._auto_save_elapsed

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
    def event_bus(self):
        """Forward the mothership event bus to the GameScene facade.

        The GameSceneUpdater's warning-banner callback publishes
        ``EVENT_UNDOCK_REQUESTED`` through this bus. The bus is owned by
        ``_mother_ship_integrator``; this property exists so callers do not
        need to reach through the integrator directly.
        """
        if self._mother_ship_integrator is None:
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


def _clear_module_caches() -> None:
    """Clear module-level caches to free memory on scene switch.

    These caches persist across game sessions and accumulate Surface
    objects. Clearing them on scene exit prevents memory growth during
    long play sessions.
    """
    # chamfered_panel caches
    try:
        from airwar.ui import chamfered_panel
        chamfered_panel._panel_surface_cache.clear()
        chamfered_panel._bg_cache.clear()
        chamfered_panel._border_cache.clear()
        chamfered_panel._glow_cache.clear()
    except (ImportError, AttributeError):
        pass

    # menu_background caches
    try:
        from airwar.ui.menu_background import MenuBackground
        MenuBackground._gradient_cache.clear()
        MenuBackground._scan_glow_cache.clear()
    except (ImportError, AttributeError):
        pass

    # explosion effect caches
    try:
        from airwar.game.explosion_animation.explosion_effect import (
            _glow_texture_cache, _spark_core_cache, _flash_cache,
        )
        _glow_texture_cache.clear()
        _spark_core_cache.clear()
        _flash_cache.clear()
    except (ImportError, AttributeError):
        pass
