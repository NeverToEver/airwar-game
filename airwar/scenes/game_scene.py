"""Main game scene -- gameplay loop, entity coordination, and rendering."""

import pygame

from airwar.config import BOOST_CONFIG, DIFFICULTY_SETTINGS, get_screen_height, get_screen_width
from airwar.config.design_tokens import get_design_tokens
from airwar.entities import Player
from airwar.game.constants import GAME_CONSTANTS, PlayerConstants, normalize_score
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
from airwar.input import PygameInputHandler
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

from .scene import Scene


class GameScene(Scene, MouseInteractiveMixin, IGameScene):
    """Main game scene controller coordinating game loop and subsystems.

    GameScene is the primary controller for the gameplay scene. It coordinates
    all subsystems including GameController, SpawnController, CollisionController,
    Player, and MotherShip systems.

    Implements IGameScene for clean integration with GameIntegrator.
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
    PERMANENT_INVINCIBILITY_FRAMES = 999999  # Sentinel: effectively infinite invincibility
    DOCKING_INVINCIBILITY_FRAMES = 1200  # 20 seconds at 60fps

    AUTO_SAVE_INTERVAL = 1800  # 30 seconds at 60fps

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
        self._haunting_renderer: HauntingRenderer | None = None
        self._save_restore_manager = SaveRestoreManager()
        self._lock_manager = LockManager(None)
        self.game_controller: GameController | None = None
        self.game_renderer: GameRenderer = None
        self.health_system = None  # delegated to GameController.health_system
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
        self._viewport = None
        self._phase_dash_invincibility_active = False
        self._survival_frames = 0

    def enter(self, **kwargs) -> None:
        """Initialize the game scene.

        Args:
            difficulty: Game difficulty ('easy', 'medium', 'hard').
            username: Player name.

        Initializes all game subsystems:
        - GameController: Game state and logic.
        - SpawnController: Enemy spawning system.
        - CollisionController: Collision detection.
        - Player: Player spaceship.
        - MotherShip system: Mothership interaction system.
        """
        self._pause_requested = False
        self._is_loading = True
        self._loading_progress = 0
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
        self._loading_progress = 20
        prewarm_glow_caches()
        prewarm_ship_sprite_caches()
        self._loading_progress = 100
        self._is_loading = False

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        self._init_pause_button_layout()
        self._aim_assist.set_raw_aim_position(self._get_logical_mouse_pos())

        difficulty = kwargs.get("difficulty", "medium")
        username = kwargs.get("username", "Player")
        settings_ref = kwargs.get("settings_ref", {})
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.game_controller = GameController(difficulty, username)
        self.game_controller.set_lock_manager(self._lock_manager)
        self._lock_manager.set_game_state(self.game_controller.state)
        self.game_renderer = GameRenderer()
        self.game_renderer.init_background(screen_width, screen_height)
        self.reward_system = self.game_controller.reward_system
        self.hud_renderer = HUDRenderer()
        self.notification_manager = self.game_controller.notification_manager

        self.spawn_controller = SpawnController(settings)
        self.spawn_controller.init_bullet_system()

        self.collision_controller = CollisionController()

        input_handler = PygameInputHandler()
        self.player = Player(
            screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET,
            screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET,
            input_handler,
        )
        self._lock_manager.set_player(self.player)
        self._sync_player_aim_target()
        self.player.rect.y = PlayerConstants.INITIAL_Y
        self.player.bullet_damage = settings["bullet_damage"]
        boost_cfg = BOOST_CONFIG[difficulty]
        self.player.boost_max = boost_cfg["max_boost"]
        self.player.boost_current = boost_cfg["max_boost"]
        self.player.boost_recovery_rate = boost_cfg["recovery_rate"]
        self.player.boost_speed_mult = boost_cfg["speed_mult"]
        self.player.boost_recovery_delay = boost_cfg["recovery_delay"]
        self.player.boost_recovery_ramp = boost_cfg["recovery_ramp"]
        self.player.apply_settings(settings_ref)
        self.reward_system.capture_player_baselines(self.player)
        self._boost_gauge = BoostGauge()
        self._ammo_magazine = AmmoMagazine()
        self._warning_banner = WarningBanner()
        self._aim_crosshair = AimCrosshair()

        self._setup_reward_selector()
        self._init_mother_ship_system(screen_width, screen_height)
        self._init_give_up_system(screen_width, screen_height)
        self._init_homecoming_system(screen_width, screen_height)
        self._bullet_manager = BulletManager(self.player, self.spawn_controller)
        self._boss_manager = BossManager(
            self.spawn_controller, self.game_controller, self.reward_system, self._bullet_manager
        )
        self._milestone_manager = MilestoneManager(self.game_controller, self.reward_system)
        self._milestone_manager.set_reward_selector(self.reward_selector)
        self._input_coordinator = InputCoordinator(
            self.player,
            self.game_controller,
            self.reward_selector,
            self._give_up_detector,
            self._give_up_ui,
        )
        self._ui_manager = UIManager(
            self.game_renderer,
            self.game_controller,
            self.reward_system,
        )
        self._game_loop_manager = GameLoopManager(
            self.game_controller,
            self.game_renderer,
            self.spawn_controller,
            self.reward_system,
            self._bullet_manager,
            self._boss_manager,
            self.collision_controller,
            self._lock_manager,
        )

        self._auto_save_timer = 0

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
        self._homecoming_coordinator = HomecomingCoordinator(detector, sequence, ui, console)
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
        """Process input events.

        Args:
            event: pygame event object.
        """
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
            if event.button == 1 and self._homecoming_base_pending and self._handle_base_console_click(event.pos):
                return
            if event.button == 1 and self.handle_mouse_click(event.pos):
                self._handle_button_click(self.get_hovered_button())

    def _handle_button_click(self, button_name: str) -> None:
        """Handle mouse button click events.

        Args:
            button_name: Name of the clicked button.
        """
        if button_name == "pause":
            self._pause_requested = True

    def _get_logical_mouse_pos(self) -> tuple[float, float]:
        pos = pygame.mouse.get_pos()
        if self._viewport:
            return self._viewport.screen_to_logical(*pos)
        return pos

    def consume_pause_request(self) -> bool:
        """Consume the pause request flag.

        Returns:
            True if there was a pause request (and resets the flag), False otherwise.
        """
        if self.is_homecoming_locked():
            self._pause_requested = False
            return False
        if self._pause_requested:
            self._pause_requested = False
            return True
        return False

    def update(self, *args, **kwargs) -> None:
        """Main game update loop.

        Update order:
        1. Entrance animation (if playing).
        2. Mothership system update.
        3. Docking state handling.
        4. Game logic update (if not paused).
        """
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

        # Always update warning banner scroll animation (even during entrance/dying)
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
            self.player.rect.x = dock_pos[0] - self.player.rect.width // 2
            self.player.rect.y = dock_pos[1] - self.player.rect.height // 2

        self._sync_player_phase_dash_invincibility()

        self._game_loop_manager.check_collisions(
            self.player,
            self.spawn_controller.enemy_bullets,
            self._on_player_damaged,
        )

        # Post-collision cleanup: ensure entities killed during collision are
        # removed before milestone check, avoiding residue during pause
        self.spawn_controller.cleanup()
        self._bullet_manager.cleanup()
        self.player.cleanup_inactive_bullets()

        self._milestone_manager.check_and_trigger(self.player)

        self._survival_frames += 1
        self._update_haunting_effect()
        self._auto_save_timer += 1
        if self._auto_save_timer >= self.AUTO_SAVE_INTERVAL:
            self._auto_save_timer = 0
            self._try_auto_save()

    def _update_haunting_effect(self) -> None:
        if not self._haunting_renderer or not self.spawn_controller:
            return
        enemy_pressure = len(self.spawn_controller.enemies)
        if self.spawn_controller.boss:
            enemy_pressure += 3
        if self.spawn_controller.enemy_bullets:
            enemy_pressure += min(8, len(self.spawn_controller.enemy_bullets) // 6)
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
            return  # Manual dock save handles this — don't overwrite mid-dock
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
        """Check ammo level and activate warning banner when critically low.

        When the mothership's ammo drops below the warning threshold during
        DOCKED state, activates the scrolling warning banner. The banner's
        on_complete callback triggers the undocking sequence.
        """
        if not self._mother_ship_integrator or not self._warning_banner:
            return

        status = self._mother_ship_integrator.get_status_data()
        if not status.get("ammo_warning", False):
            return

        if self._warning_banner.is_active:
            return

        def trigger_undock():
            self._mother_ship_integrator.request_undock()

        self._warning_banner.activate(on_complete=trigger_undock)

    BULLET_CLEAR_RADIUS = 250  # Only clear enemy bullets within this radius on player hit

    def _on_player_damaged(self, damage: int, player) -> None:
        """Handle player hit: apply damage, clear nearby enemy bullets, trigger invincibility."""
        self.game_controller.on_player_hit(damage, player)
        self._clear_nearby_enemy_bullets(player)

    def _clear_nearby_enemy_bullets(self, player) -> None:
        """Clear enemy bullets within BULLET_CLEAR_RADIUS of the player after being hit.

        Preserves distant bullets as ongoing pressure while giving the player
        a breather from immediate threats near the impact point.
        """
        if not self.spawn_controller:
            return
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

    def _update_homecoming(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.update(
                self.game_controller,
                self.player,
                self._lock_manager,
                self._bullet_manager,
                self.spawn_controller,
                self._game_loop_manager,
                self.notification_manager,
            )

    def _on_homecoming_requested(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.on_requested(
                self.game_controller,
                self.player,
                self._lock_manager,
                self._bullet_manager,
                self.notification_manager,
            )

    def _on_homecoming_complete(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.on_complete(
                self.game_controller,
                self.player,
                self._lock_manager,
                self.notification_manager,
                self.reward_system,
            )
            self._homecoming_base_pending = self._homecoming_coordinator.is_base_pending()
            self._talent_balance_manager = self._homecoming_coordinator.get_talent_balance_manager()

    def _handle_base_console_click(self, pos: tuple[int, int]) -> bool:
        if self._homecoming_coordinator:
            return self._homecoming_coordinator.handle_console_click(
                pos,
                self.game_controller,
                self.player,
                self._lock_manager,
                self.spawn_controller,
                self._game_loop_manager,
                self.notification_manager,
                self.reward_system,
            )
        return False

    def _leave_homecoming_base(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.leave_base(
                self.game_controller,
                self.player,
                self._lock_manager,
                self.spawn_controller,
                self._game_loop_manager,
                self.notification_manager,
            )
            self._homecoming_base_pending = self._homecoming_coordinator.is_base_pending()
            self._pause_requested = False

    def _on_homecoming_orbital_strike(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.on_orbital_strike(
                self.spawn_controller,
                self._game_loop_manager,
                self.player,
                self.notification_manager,
            )

    def _on_homecoming_departure_complete(self) -> None:
        if self._homecoming_coordinator:
            self._homecoming_coordinator.on_departure_complete(
                self.game_controller,
                self.player,
                self._lock_manager,
                self.spawn_controller,
                self._game_loop_manager,
                self.notification_manager,
            )
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
        if self._homecoming_coordinator:
            return self._homecoming_coordinator.is_active()
        return bool(self._homecoming_sequence and self._homecoming_sequence.is_active())

    def is_homecoming_active(self) -> bool:
        return self._is_homecoming_active()

    def is_homecoming_locked(self) -> bool:
        if self._homecoming_coordinator:
            return self._homecoming_coordinator.is_locked()
        return self._is_homecoming_active() or self._homecoming_base_pending

    def is_homecoming_complete(self) -> bool:
        if self._homecoming_coordinator:
            return self._homecoming_coordinator.is_base_pending()
        return bool(self._homecoming_base_pending)

    def render(self, surface: pygame.Surface) -> None:
        """Render the game scene.

        Args:
            surface: pygame rendering surface.
        """
        is_docked_render = self._mother_ship_integrator and self._mother_ship_integrator.is_docked()
        if self.game_renderer:
            self.game_renderer.entity_renderer.player_docked = is_docked_render
        if self._ui_manager:
            self._ui_manager.set_player_docked(is_docked_render)

        self._ui_manager.render_game(surface, self.player, self.spawn_controller.enemies, self.spawn_controller.boss)
        self._render_haunting_world(surface)

        self._ui_manager.render_bullets(surface, self.player, self.spawn_controller.enemy_bullets)
        self._render_haunting_post_bullets(surface)
        self._ui_manager.render_hud(surface, self.player)
        self._ui_manager.render_buff_stats_panel(surface, self.player)

        self._render_pause_button(surface)

        # Boost gauge -- bottom-left dashboard indicator
        if self._boost_gauge is not None:
            status = self.player.get_boost_status()
            self._boost_gauge.render(surface, status["current"], status["max"], status["active"], status)

        # Ammo magazine -- left-side vertical ammo rack
        if self._ammo_magazine and self._mother_ship_integrator:
            ms_data = self._mother_ship_integrator.get_status_data()
            self._ammo_magazine.render(
                surface,
                ammo_count=ms_data.get("ammo_count", 0.0),
                ammo_max=ms_data.get("ammo_max", 10.0),
                is_cooldown=ms_data.get("is_in_cooldown", False),
                is_docked=ms_data.get("is_docked", False),
                is_warning=ms_data.get("ammo_warning", False),
                is_present=ms_data.get("is_present", False),
                cooldown_remaining=ms_data.get("cooldown_remaining", 0.0),
                cooldown_reduction=ms_data.get("cooldown_reduction", 0.0),
            )

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

        boss = self.spawn_controller.boss if self.spawn_controller else None
        if not is_docked_render:
            self._boss_enrage_renderer.render(surface, boss)

        self._game_loop_manager.render_explosions(surface)
        self._input_coordinator.render_give_up(surface)
        if self._homecoming_ui and self._homecoming_detector and self._homecoming_detector.is_active():
            self._homecoming_ui.render_progress(surface)

        # Warning banner -- top-of-screen scrolling ammo depletion alert
        if self._warning_banner:
            self._warning_banner.render(surface)

        self._render_aim_crosshair(surface)

        if self._haunting_renderer and not self._should_suppress_haunting():
            self._haunting_renderer.render_hud_corruption(surface)

        if self._homecoming_ui and self._homecoming_sequence:
            self._homecoming_ui.render_sequence(surface, self._homecoming_sequence, self.player)

        if self._homecoming_base_pending and self._base_talent_console and self._talent_balance_manager:
            mothership_status = self._mother_ship_integrator.get_status_data() if self._mother_ship_integrator else None
            self._base_talent_console.render(
                surface,
                self._talent_balance_manager,
                self.reward_system,
                player=self.player,
                game_controller=self.game_controller,
                mothership_status=mothership_status,
                requisition_points=self.game_controller.state.requisition_points if self.game_controller else 0,
                missions=self._base_talent_console.get_missions() if self._base_talent_console else None,
            )
            # Keep mission progress in sync with actual game state
            if self._homecoming_coordinator:
                self._homecoming_coordinator.sync_mission_progress(self.game_controller, self._survival_frames)

        # Reward selector must render above game elements. Homecoming blocks
        # reward selection, but keep the normal layering contract intact.
        if self.reward_selector.visible:
            self.reward_selector.render(surface)

        # Render notifications above reward selector so critical messages are not obscured
        self._ui_manager.render_notification(surface)
        self._render_haunting_foreground(surface)

        if self._haunting_renderer and not self._should_suppress_haunting():
            self._haunting_renderer.render_transition_flicker(surface)

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
        """Render the pause button.

        Only renders when game is running normally (not paused, not reward selection).
        Button is located at top-left corner, uses two vertical bars icon for pause.
        Uses cached Surface to avoid per-frame memory reallocation.

        Args:
            surface: pygame rendering surface.
        """
        if not self.game_controller or self.game_controller.state.is_paused:
            return
        if self.reward_selector and self.reward_selector.visible:
            return
        is_hovered = self.is_button_hovered("pause")
        self._pause_button.render(surface, is_hovered, self._tokens.colors, self._tokens.spacing)

    @property
    def score(self) -> int:
        """Get the current score.

        Returns:
            Current game score.
        """
        return self.game_controller.state.score if self.game_controller else 0

    @score.setter
    def score(self, value: int) -> None:
        """Set the current score.

        Args:
            value: New score value.
        """
        if self.game_controller:
            self.game_controller.state.score = normalize_score(value)

    @property
    def cycle_count(self) -> int:
        """Get the current cycle count.

        Returns:
            Number of completed boss cycles.
        """
        return self.game_controller.state.cycle_count if self.game_controller else 0

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        """Set the cycle count.

        Args:
            value: New cycle count value.
        """
        if self.game_controller:
            self.game_controller.state.cycle_count = value

    def is_game_over(self) -> bool:
        """Check if the game is over.

        Returns:
            True if the game is over.
        """
        if not self.player:
            return True
        if not self.game_controller:
            return True
        return self.game_controller.is_game_over()

    def pause(self) -> None:
        """Pause the game.

        Does not pause if reward selector is visible.
        """
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
        """Get the game paused state.

        Returns:
            True if the game is paused.
        """
        return self.game_controller.state.is_paused if self.game_controller else False

    @property
    def unlocked_buffs(self) -> list:
        """Get the list of unlocked buffs.

        Returns:
            List of unlocked buff names.
        """
        return self.reward_system.unlocked_buffs if self.reward_system else []

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        """Set the list of unlocked buffs.

        Args:
            value: List of buff names.
        """
        if self.reward_system:
            self.reward_system.unlocked_buffs = value

    @property
    def difficulty(self) -> str:
        """Get the game difficulty.

        Returns:
            Game difficulty ('easy', 'medium', 'hard').
        """
        return self.game_controller.state.difficulty if self.game_controller else "medium"

    @difficulty.setter
    def difficulty(self, value: str) -> None:
        """Set the game difficulty.

        Args:
            value: Game difficulty ('easy', 'medium', 'hard').
        """
        if self.game_controller:
            self.game_controller.state.difficulty = value

    def restore_from_save(self, save_data) -> None:
        """Restore game state from save data.

        Args:
            save_data: Save data object containing:
                - score: Current score.
                - kill_count: Kill count.
                - cycle_count: Current cycle count.
                - player_health: Player health.
                - player_max_health: Player max health.
                - unlocked_buffs: List of unlocked buffs.
                - buff_levels: Dictionary of buff levels.
                - difficulty: Game difficulty.
                - username: Player name.
                - is_in_mothership: Whether in mothership state.
        """
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

    # IGameScene implementation for GameIntegrator layer compliance

    def set_player_position(self, x: float, y: float) -> None:
        """Set player rect center position."""
        if self.player:
            self.player.rect.x = x - self.player.rect.width // 2
            self.player.rect.y = y - self.player.rect.height // 2

    def set_player_position_topleft(self, x: float, y: float) -> None:
        """Set player rect top-left position."""
        if self.player:
            self.player.rect.x = x
            self.player.rect.y = y

    def trigger_explosion(self, x: float, y: float, radius: int) -> None:
        """Trigger explosion visual effect at given position."""
        if self._game_loop_manager:
            self._game_loop_manager._on_explosion(x, y, radius)

    def trigger_boss_death_explosion(self, boss) -> None:
        """Play a boss wreck explosion without keeping the boss entity alive."""
        if self._game_loop_manager and boss:
            self._game_loop_manager.trigger_boss_death_explosion(
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
            )

    def add_score(self, amount: int) -> None:
        """Add to score."""
        if self.game_controller:
            self.game_controller.state.score = normalize_score(self.game_controller.state.score + amount)

    def add_kill(self) -> None:
        """Increment kill count."""
        if self.game_controller:
            self.game_controller.state.kill_count += 1

    def add_boss_kill(self) -> None:
        """Increment boss kill count."""
        if self.game_controller:
            self.game_controller.state.boss_kill_count += 1

    def show_notification(self, message: str) -> None:
        """Show a notification message."""
        if self.notification_manager:
            self.notification_manager.show(message)

    def get_enemies(self) -> list:
        """Get current enemy list."""
        if self.spawn_controller:
            return list(self.spawn_controller.enemies)
        return []

    def get_boss(self):
        """Get current boss or None."""
        return self.spawn_controller.boss if self.spawn_controller else None

    def clear_boss(self) -> None:
        """Clear the current boss."""
        if self._boss_manager:
            self._boss_manager.clear_boss()
        elif self.spawn_controller:
            self.spawn_controller.boss = None

    def set_player_invincible(self, invincible: bool, timer: int, silent: bool = False) -> None:
        """Set player invincibility state.

        When silent=True, the player is invincible without the blink flash effect.
        """
        if not self.game_controller:
            return
        if self._lock_manager:
            self._sync_lock_manager_targets()
            if invincible:
                self._lock_manager.acquire(
                    LockLayer.MOTHERSHIP,
                    LockRequest(
                        invincible=True,
                        is_silent_invincible=silent,
                        invincibility_duration=timer,
                    ),
                )
            else:
                self._lock_manager.release(LockLayer.MOTHERSHIP)
            return
        self.game_controller.set_invincible(invincible, timer, silent)

    def get_score(self) -> int:
        """Get current score."""
        return self.score

    def get_cycle_count(self) -> int:
        """Get current cycle count."""
        return self.cycle_count

    def get_kill_count(self) -> int:
        """Get total kill count."""
        return self.game_controller.state.kill_count if self.game_controller else 0

    def get_boss_kill_count(self) -> int:
        """Get boss kill count."""
        return self.game_controller.state.boss_kill_count if self.game_controller else 0

    def get_unlocked_buffs(self) -> list:
        """Get list of unlocked buff names."""
        return self.unlocked_buffs

    def get_buff_levels(self) -> dict[str, int]:
        """Get buff levels dictionary."""
        if not self.reward_system:
            return {}
        return dict(self.reward_system.buff_levels)

    def get_earned_buff_levels(self) -> dict[str, int]:
        if not self.reward_system:
            return {}
        return self.reward_system.get_earned_buff_levels()

    def get_talent_loadout(self) -> dict[str, str]:
        if not self.reward_system:
            return {}
        return dict(self.reward_system.talent_loadout)

    def get_player_health(self) -> int:
        """Get player current health."""
        return self.player.health if self.player else 0

    def get_player_max_health(self) -> int:
        """Get player max health."""
        return self.player.max_health if self.player else 0

    def get_difficulty(self) -> str:
        """Get game difficulty setting."""
        return self.difficulty

    def get_username(self) -> str:
        """Get player username."""
        return self.game_controller.state.username if self.game_controller else "Player"

    def set_paused(self, paused: bool) -> None:
        """Set game paused state."""
        if self.game_controller:
            self.game_controller.set_paused(paused)

    def clear_ripple_effects(self) -> None:
        """Clear all ripple effects."""
        if self.game_controller:
            self.game_controller.state.ripple_effects.clear()
