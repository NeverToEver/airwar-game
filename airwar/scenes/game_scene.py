"""Main game scene -- gameplay loop, entity coordination, and rendering."""
import math

import pygame
from airwar.utils.fonts import get_cjk_font
from typing import Dict
from .scene import Scene
from airwar.entities import Player
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.managers.game_controller import GameController, GameplayState
from airwar.game.managers.spawn_controller import SpawnController
from airwar.game.managers.collision_controller import CollisionController
from airwar.game.managers.game_controller import normalize_score
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.ui.reward_selector import RewardSelector
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.warning_banner import WarningBanner
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.base_talent_console import BaseTalentConsole, BaseTalentConsoleAction
from airwar.ui.homecoming_ui import HomecomingUI
from airwar.game.mother_ship import (
    EventBus,
    InputDetector,
    MotherShipStateMachine,
    PersistenceManager,
    ProgressBarUI,
    MotherShip,
    GameIntegrator,
)
from airwar.game.mother_ship.interfaces import IGameScene
from airwar.game.constants import PlayerConstants, GAME_CONSTANTS
from airwar.ui.give_up_ui import GiveUpUI
from airwar.game.give_up import GiveUpDetector
from airwar.game.homecoming import HomecomingDetector, HomecomingSequence
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.game.managers import (
    BulletManager,
    BossManager,
    MilestoneManager,
    InputCoordinator,
    UIManager,
    GameLoopManager,
)
from airwar.config import DIFFICULTY_SETTINGS, BOOST_CONFIG, VALID_DIFFICULTIES, get_screen_width, get_screen_height
from airwar.input import PygameInputHandler
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.config.design_tokens import get_design_tokens
from airwar.utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches


class GameScene(Scene, MouseInteractiveMixin, IGameScene):
    """Main game scene controller coordinating game loop and subsystems.

    GameScene is the primary controller for the gameplay scene. It coordinates
    all subsystems including GameController, SpawnController, CollisionController,
    Player, and MotherShip systems.

    Implements IGameScene for clean integration with GameIntegrator.
    """

    PAUSE_BUTTON_SIZE = 30
    PAUSE_BUTTON_MARGIN = 10
    PAUSE_BAR_WIDTH = 4
    PAUSE_BAR_HEIGHT = 14
    PAUSE_BAR_GAP = 4
    AIM_ASSIST_BREAK_DISTANCE = 38.0
    AIM_ASSIST_SWITCH_DISTANCE = 90.0
    AIM_ASSIST_RELEASE_DISTANCE = 230.0
    AIM_ASSIST_DIRECTION_CONE_DOT = 0.42
    AIM_INPUT_DELAY_BLEND = 0.28
    AIM_INPUT_SNAP_DISTANCE = 10.0
    HOMECOMING_LOCK_INVINCIBILITY_TIMER = 999999

    AUTO_SAVE_INTERVAL = 1800  # 30 seconds at 60fps

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._pause_requested = False
        self._is_loading = True
        self._loading_progress = 0
        self._tokens = get_design_tokens()
        self._pause_btn_layout = None
        self._pause_btn_cache = {}
        self.game_controller: GameController = None
        self.game_renderer: GameRenderer = None
        self.health_system: HealthSystem = None
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
        self._aim_position = (0.0, 0.0)
        self._raw_aim_position = (0.0, 0.0)
        self._previous_raw_aim_position = (0.0, 0.0)
        self._smoothed_raw_aim_position = (0.0, 0.0)
        self._aim_input_initialized = False
        self._aim_assist_target = None
        self._give_up_detector = None
        self._give_up_ui = None
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
        self._phase_dash_invincibility_active = False
        self._phase_dash_previous_invincible = False
        self._phase_dash_previous_silent = False
        self._enrage_overlay_cache = None
        self._enrage_overlay_cache_key = None

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
        self._pause_btn_cache.clear()

        # Prewarm glow caches before gameplay starts
        self._loading_progress = 20
        prewarm_glow_caches()
        prewarm_ship_sprite_caches()
        self._loading_progress = 100
        self._is_loading = False

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        self._init_pause_button_layout()
        self._set_raw_aim_position(pygame.mouse.get_pos())

        difficulty = kwargs.get('difficulty', 'medium')
        username = kwargs.get('username', 'Player')
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.game_controller = GameController(difficulty, username)
        self.game_renderer = GameRenderer()
        self.game_renderer.init_background(screen_width, screen_height)
        self.health_system = HealthSystem(difficulty)
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
            input_handler
        )
        self._sync_player_aim_target()
        self.player.rect.y = PlayerConstants.INITIAL_Y
        self.player.bullet_damage = settings['bullet_damage']
        boost_cfg = BOOST_CONFIG[difficulty]
        self.player.boost_max = boost_cfg['max_boost']
        self.player.boost_current = boost_cfg['max_boost']
        self.player.boost_recovery_rate = boost_cfg['recovery_rate']
        self.player.boost_speed_mult = boost_cfg['speed_mult']
        self.player.boost_recovery_delay = boost_cfg['recovery_delay']
        self.player.boost_recovery_ramp = boost_cfg['recovery_ramp']
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
            self.spawn_controller,
            self.game_controller,
            self.reward_system,
            self._bullet_manager
        )
        self._milestone_manager = MilestoneManager(
            self.game_controller,
            self.reward_system
        )
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
        )

        self._auto_save_timer = 0

    def _setup_reward_selector(self) -> None:
        self.reward_selector.hide = lambda: setattr(self.reward_selector, 'visible', False)
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
        self._homecoming_detector = HomecomingDetector(self._on_homecoming_requested)
        self._homecoming_sequence = HomecomingSequence(self._on_homecoming_complete)
        self._homecoming_ui = HomecomingUI(screen_width, screen_height)
        self._base_talent_console = BaseTalentConsole(screen_width, screen_height)
        self._talent_balance_manager = None
        self._homecoming_base_pending = False

    def exit(self) -> None:
        pass

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
            self._set_raw_aim_position(event.pos)
            if self._homecoming_base_pending and self._base_talent_console:
                self._base_talent_console.handle_mouse_motion(event.pos)
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._set_raw_aim_position(event.pos)
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
        if self._homecoming_base_pending and self._base_talent_console:
            self._base_talent_console.update()
        self._set_raw_aim_position(pygame.mouse.get_pos())
        self._update_aim_assist()
        self._aim_crosshair.update()
        self._update_homecoming()

        if self.game_renderer and self.game_renderer.integrated_hud:
            unlocked_buffs = getattr(self.reward_system, 'unlocked_buffs', [])
            self.game_renderer.integrated_hud.update_scroll(len(unlocked_buffs))
            if self.player:
                self.game_renderer.integrated_hud.update_health_tank(
                    self.player.health, self.player.max_health)
            self.game_renderer.integrated_hud.update()

        if self._is_homecoming_active():
            return

        if self._game_loop_manager.is_entrance_playing():
            self._game_loop_manager.update_entrance(self.player)
            if self._mother_ship_integrator:
                self._mother_ship_integrator.update()
            return

        is_dying = self.game_controller.state.gameplay_state == GameplayState.DYING

        if is_dying:
            self._game_loop_manager.update_game(self.player)
            if self._mother_ship_integrator:
                self._mother_ship_integrator.update()
            return

        # Always update warning banner scroll animation (even during pause)
        if self._warning_banner:
            self._warning_banner.update()

        if self.game_controller.state.paused or self.reward_selector.visible:
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

        self._auto_save_timer += 1
        if self._auto_save_timer >= self.AUTO_SAVE_INTERVAL:
            self._auto_save_timer = 0
            self._try_auto_save()

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

        state = self.game_controller.state
        if self.player.is_phase_dash_invincible():
            if not self._phase_dash_invincibility_active:
                self._phase_dash_previous_invincible = state.player_invincible
                self._phase_dash_previous_silent = state.silent_invincible
            self._phase_dash_invincibility_active = True
            state.player_invincible = True
            state.invincibility_timer = max(state.invincibility_timer, 2)
            state.silent_invincible = True
            return

        if not self._phase_dash_invincibility_active:
            return

        self._phase_dash_invincibility_active = False
        if state.invincibility_timer <= 2 and not self._phase_dash_previous_invincible:
            state.player_invincible = False
            state.invincibility_timer = 0
            state.silent_invincible = False
        else:
            state.silent_invincible = self._phase_dash_previous_silent

    def _update_mothership_ammo_warning(self) -> None:
        """Check ammo level and activate warning banner when critically low.

        When the mothership's ammo drops below the warning threshold during
        DOCKED state, activates the scrolling warning banner. The banner's
        on_complete callback triggers the undocking sequence.
        """
        if not self._mother_ship_integrator or not self._warning_banner:
            return

        status = self._mother_ship_integrator.get_status_data()
        if not status.get('ammo_warning', False):
            return

        if self._warning_banner.is_active:
            return

        def trigger_undock():
            self._mother_ship_integrator.request_undock()

        self._warning_banner.activate(on_complete=trigger_undock)

    def _on_player_damaged(self, damage: int, player) -> None:
        """Handle player hit: apply damage, clear all enemy bullets, trigger invincibility."""
        self.game_controller.on_player_hit(damage, player)
        self._bullet_manager.clear_enemy_bullets()

    def _on_give_up_complete(self) -> None:
        self.game_controller.on_player_hit(GAME_CONSTANTS.DAMAGE.INSTANT_KILL, self.player)

    def _update_homecoming(self) -> None:
        if not self._homecoming_detector or not self._homecoming_sequence:
            return

        if self._homecoming_sequence.is_active():
            self._homecoming_sequence.update(self.player)
            if self.player:
                self.player.controls_locked = True
            return

        can_use = self._can_request_homecoming()
        self._homecoming_detector.update(GAME_CONSTANTS.TIMING.FIXED_DELTA_TIME, enabled=can_use)

        if self._homecoming_ui:
            if self._homecoming_detector.is_active():
                self._homecoming_ui.show()
                self._homecoming_ui.update_progress(self._homecoming_detector.get_progress())
            else:
                self._homecoming_ui.hide()

    def _can_request_homecoming(self) -> bool:
        if not self.game_controller or not self.player:
            return False
        if not self._homecoming_sequence or self._homecoming_base_pending:
            return False
        if not self.game_controller.is_playing():
            return False
        if self.game_controller.state.paused or self.reward_selector.visible:
            return False
        if self._game_loop_manager and self._game_loop_manager.is_entrance_playing():
            return False
        if self._mother_ship_integrator and self._mother_ship_integrator.is_docked():
            return False
        return not (self._homecoming_sequence and self._homecoming_sequence.is_active())

    def _on_homecoming_requested(self) -> None:
        if not self._can_request_homecoming():
            return

        if self._homecoming_ui:
            self._homecoming_ui.hide()

        if self._bullet_manager:
            self._bullet_manager.clear_enemy_bullets(include_clear_immune=True)
        if self.player:
            for bullet in self.player.get_bullets():
                bullet.active = False
            self.player.cleanup_inactive_bullets()

        self._set_homecoming_protection(locked=True)

        started = self._homecoming_sequence.start(self.player, get_screen_width(), get_screen_height())
        if started and self.notification_manager:
            self.notification_manager.show("返航航线已锁定")

    def _on_homecoming_complete(self) -> None:
        self._homecoming_base_pending = True
        self._ensure_talent_balance_manager()
        self._set_homecoming_protection(locked=True)
        if self.notification_manager:
            self.notification_manager.show("已进入基地整备")

    def _ensure_talent_balance_manager(self) -> None:
        if not self.reward_system:
            return
        self.reward_system.ensure_earned_levels()
        self._talent_balance_manager = TalentBalanceManager(
            self.reward_system.get_earned_buff_levels(),
            self.reward_system.talent_loadout,
        )
        self._apply_base_talent_loadout(show_notification=False)

    def _apply_base_talent_loadout(self, show_notification: bool = True) -> None:
        if not self._talent_balance_manager or not self.reward_system or not self.player:
            return
        self._talent_balance_manager.apply_to_reward_system(self.reward_system, self.player)
        self._save_base_loadout()
        if show_notification and self.notification_manager:
            self.notification_manager.show("基地天赋配置已同步")

    def _handle_base_console_click(self, pos: tuple[int, int]) -> bool:
        if not self._base_talent_console or not self._talent_balance_manager:
            return False
        action = self._base_talent_console.handle_mouse_click(pos)
        if action is None:
            return False
        self._handle_base_console_action(action)
        return True

    def _handle_base_console_action(self, action: BaseTalentConsoleAction) -> None:
        if action.kind == BaseTalentConsoleAction.CONTINUE:
            self._leave_homecoming_base()
            return
        if action.kind == BaseTalentConsoleAction.SELECT_ROUTE and action.route:
            if self._talent_balance_manager.next_option(action.route) is not None:
                self._apply_base_talent_loadout()

    def _leave_homecoming_base(self) -> None:
        self._save_base_loadout()
        self._homecoming_base_pending = False
        self._pause_requested = False
        if self._homecoming_sequence:
            self._homecoming_sequence.reset()
        if self._homecoming_detector:
            self._homecoming_detector.reset()
        if self._homecoming_ui:
            self._homecoming_ui.hide()
        self._set_homecoming_protection(locked=False)
        if self.notification_manager:
            self.notification_manager.show("已离开基地")

    def _save_base_loadout(self) -> bool:
        if not self._mother_ship_integrator:
            return False
        save_data = self._mother_ship_integrator.create_save_data()
        if not save_data:
            return False
        save_data.is_in_mothership = False
        return PersistenceManager(username=save_data.username).save_game(save_data)

    def _set_homecoming_protection(self, locked: bool) -> None:
        if self.player:
            self.player.controls_locked = locked
        if self.game_controller:
            self.game_controller.state.paused = locked
            self.game_controller.state.player_invincible = True
            self.game_controller.state.invincibility_timer = (
                self.HOMECOMING_LOCK_INVINCIBILITY_TIMER
                if locked
                else GAME_CONSTANTS.PLAYER.INVINCIBILITY_DURATION
            )
            self.game_controller.state.silent_invincible = locked

    def _is_homecoming_active(self) -> bool:
        return bool(self._homecoming_sequence and self._homecoming_sequence.is_active())

    def is_homecoming_active(self) -> bool:
        return self._is_homecoming_active()

    def is_homecoming_locked(self) -> bool:
        return self._is_homecoming_active() or self._homecoming_base_pending

    def is_homecoming_complete(self) -> bool:
        return bool(self._homecoming_base_pending)

    def render(self, surface: pygame.Surface) -> None:
        """Render the game scene.

        Args:
            surface: pygame rendering surface.
        """
        # Show loading screen while warming caches
        if self._is_loading:
            self._render_loading_screen(surface)
            return

        self._ui_manager.render_game(
            surface,
            self.player,
            self.spawn_controller.enemies,
            self.spawn_controller.boss
        )

        self._ui_manager.render_bullets(
            surface,
            self.player,
            self.spawn_controller.enemy_bullets
        )
        self._ui_manager.render_hud(surface, self.player)
        self._ui_manager.render_buff_stats_panel(surface, self.player)

        self._render_pause_button(surface)

        # Boost gauge -- bottom-left dashboard indicator
        if self._boost_gauge is not None:
            status = self.player.get_boost_status()
            self._boost_gauge.render(surface, status['current'],
                                     status['max'], status['active'], status)

        # Ammo magazine -- left-side vertical ammo rack
        if self._ammo_magazine and self._mother_ship_integrator:
            ms_data = self._mother_ship_integrator.get_status_data()
            self._ammo_magazine.render(
                surface,
                ammo_count=ms_data.get('ammo_count', 0.0),
                ammo_max=ms_data.get('ammo_max', 10.0),
                is_cooldown=ms_data.get('is_in_cooldown', False),
                is_docked=ms_data.get('is_docked', False),
                is_warning=ms_data.get('ammo_warning', False),
                is_present=ms_data.get('is_present', False),
                cooldown_remaining=ms_data.get('cooldown_remaining', 0.0),
                cooldown_reduction=ms_data.get('cooldown_reduction', 0.0),
            )

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

        self._render_boss_enrage_overlay(surface)

        self._game_loop_manager.render_explosions(surface)
        self._input_coordinator.render_give_up(surface)
        if self._homecoming_ui and self._homecoming_detector and self._homecoming_detector.is_active():
            self._homecoming_ui.render_progress(surface)

        # Warning banner -- top-of-screen scrolling ammo depletion alert
        if self._warning_banner:
            self._warning_banner.render(surface)

        self._render_aim_crosshair(surface)

        if self._homecoming_ui and self._homecoming_sequence:
            self._homecoming_ui.render_sequence(surface, self._homecoming_sequence, self.player)

        if self._homecoming_base_pending and self._base_talent_console and self._talent_balance_manager:
            self._base_talent_console.render(surface, self._talent_balance_manager, self.reward_system)

        # Reward selector must render above game elements. Homecoming blocks
        # reward selection, but keep the normal layering contract intact.
        if self.reward_selector.visible:
            self.reward_selector.render(surface)

        # Render notifications above reward selector so critical messages are not obscured
        self._ui_manager.render_notification(surface)

    def _render_boss_enrage_overlay(self, surface: pygame.Surface) -> None:
        boss = self.spawn_controller.boss if self.spawn_controller else None
        if not boss or not boss.is_enrage_active():
            return

        intensity = boss.enrage_visual_intensity()
        sw, sh = surface.get_size()
        scale = 1.0 + 0.018 * intensity
        scaled = pygame.transform.scale(surface, (int(sw * scale), int(sh * scale)))
        wobble_x = int(math.sin(pygame.time.get_ticks() * 0.012) * 7 * intensity)
        wobble_y = int(math.cos(pygame.time.get_ticks() * 0.010) * 4 * intensity)
        surface.blit(scaled, scaled.get_rect(center=(sw // 2 + wobble_x, sh // 2 + wobble_y)))

        cache_key = (sw, sh)
        if self._enrage_overlay_cache_key != cache_key:
            self._enrage_overlay_cache = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self._enrage_overlay_cache_key = cache_key
        overlay = self._enrage_overlay_cache
        overlay.fill((112, 38, 30, int(42 * intensity)))
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _set_raw_aim_position(self, position: tuple[int, int]) -> None:
        x = max(0, min(float(position[0]), float(get_screen_width())))
        y = max(0, min(float(position[1]), float(get_screen_height())))
        if not self._aim_input_initialized:
            self._aim_input_initialized = True
            self._previous_raw_aim_position = (x, y)
            self._raw_aim_position = (x, y)
            self._smoothed_raw_aim_position = (x, y)
            self._aim_position = (x, y)
            self._sync_player_aim_target()
            return
        self._previous_raw_aim_position = self._raw_aim_position
        self._raw_aim_position = (x, y)
        self._aim_position = self._smoothed_raw_aim_position
        self._sync_player_aim_target()

    def _update_aim_assist(self) -> None:
        self._update_smoothed_raw_aim_position()
        target = self._resolve_aim_assist_target()
        if target is None:
            self._aim_position = self._smoothed_raw_aim_position
            self._sync_player_aim_target()
            return

        target_rect = self._target_rect(target)
        self._aim_position = target_rect.center
        self._sync_player_aim_target()

    def _resolve_aim_assist_target(self):
        raw_x, raw_y = self._smoothed_raw_aim_position
        candidates = self._aim_assist_candidates()
        if not candidates:
            self._aim_assist_target = None
            return None

        movement = self._raw_aim_movement()
        movement_len_sq = movement[0] * movement[0] + movement[1] * movement[1]

        if movement_len_sq >= self.AIM_ASSIST_SWITCH_DISTANCE * self.AIM_ASSIST_SWITCH_DISTANCE:
            directional_target = self._target_in_movement_direction(candidates, movement)
            if directional_target is not None:
                self._aim_assist_target = directional_target
                return directional_target
            if movement_len_sq >= self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE:
                self._aim_assist_target = None
                return None
            if self._aim_assist_target and getattr(self._aim_assist_target, 'active', False):
                return self._aim_assist_target

        if self._aim_assist_target and self._is_aim_assist_locked(self._aim_assist_target, raw_x, raw_y):
            return self._aim_assist_target

        for target in candidates:
            if self._is_raw_aim_inside_target(target, raw_x, raw_y):
                self._aim_assist_target = target
                return target

        target = self._nearest_aim_assist_target(candidates, raw_x, raw_y)
        self._aim_assist_target = target
        return target

    def _update_smoothed_raw_aim_position(self) -> None:
        sx, sy = self._smoothed_raw_aim_position
        rx, ry = self._raw_aim_position
        dx = rx - sx
        dy = ry - sy
        if dx * dx + dy * dy <= self.AIM_INPUT_SNAP_DISTANCE * self.AIM_INPUT_SNAP_DISTANCE:
            self._smoothed_raw_aim_position = self._raw_aim_position
            return
        self._smoothed_raw_aim_position = (
            sx + dx * self.AIM_INPUT_DELAY_BLEND,
            sy + dy * self.AIM_INPUT_DELAY_BLEND,
        )

    def _aim_assist_candidates(self) -> list:
        if not self.spawn_controller:
            return []
        targets = [enemy for enemy in self.spawn_controller.enemies if getattr(enemy, 'active', False)]
        boss = self.spawn_controller.boss
        if boss and getattr(boss, 'active', False):
            targets.append(boss)
        return targets

    def _is_raw_aim_inside_target(self, target, raw_x: float, raw_y: float) -> bool:
        return self._target_rect(target).collidepoint(raw_x, raw_y)

    def _is_aim_assist_locked(self, target, raw_x: float, raw_y: float) -> bool:
        if not getattr(target, 'active', False):
            return False
        rect = self._target_rect(target)
        if rect.collidepoint(raw_x, raw_y):
            return True
        dx = raw_x - rect.centerx
        dy = raw_y - rect.centery
        return (dx * dx + dy * dy) <= self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE

    def _raw_aim_movement(self) -> tuple[float, float]:
        return (
            self._raw_aim_position[0] - self._previous_raw_aim_position[0],
            self._raw_aim_position[1] - self._previous_raw_aim_position[1],
        )

    def _nearest_aim_assist_target(self, candidates: list, raw_x: float, raw_y: float):
        return min(
            candidates,
            key=lambda target: self._distance_sq_to_target(target, raw_x, raw_y),
            default=None,
        )

    def _target_in_movement_direction(self, candidates: list, movement: tuple[float, float]):
        if self._aim_assist_target:
            origin = self._target_rect(self._aim_assist_target).center
        else:
            origin = self._raw_aim_position

        mx, my = movement
        movement_len = math.hypot(mx, my)
        if movement_len <= 0:
            return None
        move_x = mx / movement_len
        move_y = my / movement_len

        best_target = None
        best_score = 0.0
        for target in candidates:
            if target is self._aim_assist_target:
                continue
            rect = self._target_rect(target)
            tx = rect.centerx - origin[0]
            ty = rect.centery - origin[1]
            distance = math.hypot(tx, ty)
            if distance <= 0:
                continue
            dot = (tx / distance) * move_x + (ty / distance) * move_y
            if dot > best_score and dot >= self.AIM_ASSIST_DIRECTION_CONE_DOT:
                best_score = dot
                best_target = target
        return best_target

    def _distance_sq_to_target(self, target, raw_x: float, raw_y: float) -> float:
        rect = self._target_rect(target)
        dx = raw_x - rect.centerx
        dy = raw_y - rect.centery
        return dx * dx + dy * dy

    def _target_rect(self, target) -> pygame.Rect:
        rect = target.get_hitbox() if hasattr(target, 'get_hitbox') else target.rect
        if isinstance(rect, pygame.Rect):
            return rect
        if hasattr(target, 'get_hitbox'):
            rect = target.get_hitbox()
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)

    def _sync_player_aim_target(self) -> None:
        if self.player:
            self.player.set_aim_target(*self._aim_position)

    def _render_aim_crosshair(self, surface: pygame.Surface) -> None:
        if not self.game_controller or not self.game_controller.is_playing():
            return
        if self.game_controller.state.paused:
            return
        if self.reward_selector and self.reward_selector.visible:
            return
        self._aim_crosshair.render(surface, self._aim_position)

    def _init_pause_button_layout(self) -> None:
        """Pre-calculate pause button geometry and register button regions.

        Only called in enter() and resize to avoid per-frame recalculation.
        Also pre-renders both states (normal/hovered) Surface and caches them.
        """
        colors = self._tokens.colors
        spacing = self._tokens.spacing
        size = self.PAUSE_BUTTON_SIZE
        margin = self.PAUSE_BUTTON_MARGIN
        bar_w = self.PAUSE_BAR_WIDTH
        bar_h = self.PAUSE_BAR_HEIGHT
        bar_gap = self.PAUSE_BAR_GAP

        button_x = margin
        button_y = margin
        center_x = button_x + size // 2
        center_y = button_y + size // 2

        self._pause_btn_layout = {
            'rect': pygame.Rect(button_x, button_y, size, size),
            'left_bar': (center_x - bar_gap // 2 - bar_w, center_y - bar_h // 2, bar_w, bar_h),
            'right_bar': (center_x + bar_gap // 2, center_y - bar_h // 2, bar_w, bar_h),
            'pos': (button_x, button_y),
        }
        self.register_button("pause", self._pause_btn_layout['rect'])

        # Pre-render both normal and hovered state surfaces
        self._pause_btn_cache.clear()
        for state_key, bg_alpha, border_alpha in [
            ("normal", 180, 120),
            ("hovered", 220, 200),
        ]:
            bg_color = (*colors.BACKGROUND_PANEL, bg_alpha)
            bg_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(
                bg_surface, bg_color,
                bg_surface.get_rect(),
                border_radius=spacing.BORDER_RADIUS_SM
            )

            border_color = (*colors.PANEL_BORDER, border_alpha)
            border_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surface, border_color,
                border_surface.get_rect(),
                width=1,
                border_radius=spacing.BORDER_RADIUS_SM
            )

            self._pause_btn_cache[state_key] = (bg_surface, border_surface)

    def _render_pause_button(self, surface: pygame.Surface) -> None:
        """Render the pause button.

        Only renders when game is running normally (not paused, not reward selection).
        Button is located at top-left corner, uses two vertical bars icon for pause.
        Uses cached Surface to avoid per-frame memory reallocation.

        Args:
            surface: pygame rendering surface.
        """
        if not self.game_controller or self.game_controller.state.paused:
            return
        if self.reward_selector and self.reward_selector.visible:
            return
        if not self._pause_btn_layout:
            return

        is_hovered = self.is_button_hovered("pause")
        state_key = "hovered" if is_hovered else "normal"
        bg_surface, border_surface = self._pause_btn_cache[state_key]

        layout = self._pause_btn_layout
        pos = layout['pos']
        surface.blit(bg_surface, pos)
        surface.blit(border_surface, pos)

        bar_color = self._tokens.colors.HUD_AMBER if is_hovered else self._tokens.colors.TEXT_MUTED
        pygame.draw.rect(surface, bar_color, layout['left_bar'], border_radius=1)
        pygame.draw.rect(surface, bar_color, layout['right_bar'], border_radius=1)

    def _render_loading_screen(self, surface: pygame.Surface) -> None:
        """Render loading screen while prewarming caches.

        Args:
            surface: pygame rendering surface.
        """
        colors = self._tokens.colors
        screen_width = surface.get_width()
        screen_height = surface.get_height()

        # Dark overlay
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        # Loading text
        font_large = get_cjk_font(72)
        font_small = get_cjk_font(36)

        title = font_large.render("加载中...", True, colors.TEXT_PRIMARY)
        title_rect = title.get_rect(center=(screen_width // 2, screen_height // 2 - 40))

        progress_text = font_small.render(f"{self._loading_progress}%", True, colors.HUD_AMBER)
        progress_rect = progress_text.get_rect(center=(screen_width // 2, screen_height // 2 + 20))

        hint = font_small.render("请稍候，正在优化游戏体验", True, colors.TEXT_MUTED)
        hint_rect = hint.get_rect(center=(screen_width // 2, screen_height // 2 + 70))

        surface.blit(title, title_rect)
        surface.blit(progress_text, progress_rect)
        surface.blit(hint, hint_rect)

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
        return self.game_controller.cycle_count if self.game_controller else 0

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        """Set the cycle count.

        Args:
            value: New cycle count value.
        """
        if self.game_controller:
            self.game_controller.cycle_count = value

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
            self.game_controller.state.paused = True

    def resume(self) -> None:
        """Resume the game."""
        if self.is_homecoming_locked():
            return
        if self.game_controller:
            self.game_controller.state.paused = False

    @property
    def paused(self) -> bool:
        """Get the game paused state.

        Returns:
            True if the game is paused.
        """
        return self.game_controller.state.paused if self.game_controller else False

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
        return self.game_controller.state.difficulty if self.game_controller else 'medium'

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
        if not save_data or not self.game_controller or not self.player:
            return

        self.game_controller.state.score = normalize_score(save_data.score)
        self.game_controller.state.kill_count = max(0, save_data.kill_count)
        self.game_controller.state.boss_kill_count = max(0, save_data.boss_kill_count)
        self.game_controller.milestone_index = save_data.cycle_count
        self.game_controller.cycle_count = save_data.cycle_count

        self.reward_system.unlocked_buffs = save_data.unlocked_buffs
        self._restore_buff_levels(save_data.buff_levels)
        self._restore_earned_buff_levels(getattr(save_data, "earned_buff_levels", {}))
        if getattr(save_data, "talent_loadout", None):
            self.reward_system.talent_loadout = dict(save_data.talent_loadout)
        self.reward_system.capture_player_baselines(self.player)
        self._restore_talent_loadout_effects()
        self.player.health = min(max(1, save_data.player_health), self.player.max_health)

        self.game_controller.state.difficulty = save_data.difficulty if save_data.difficulty in VALID_DIFFICULTIES else 'medium'
        self.game_controller.state.username = save_data.username
        self.game_controller.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(self.game_controller.state.difficulty)

        # Restore difficulty scaling so enemy stats scale correctly after load
        if self.game_controller.difficulty_manager:
            self.game_controller.difficulty_manager.set_boss_kill_count(save_data.boss_kill_count)

        if save_data.is_in_mothership:
            self._restore_to_mothership_state()
        else:
            sw = get_screen_width()
            sh = get_screen_height()
            self.player.rect.x = max(0, min(save_data.player_x, sw - self.player.rect.width))
            self.player.rect.y = max(0, min(save_data.player_y, sh - self.player.rect.height))

        self.game_controller.state.entrance_animation = False
        self.game_controller.state.entrance_timer = 0

    def _restore_buff_levels(self, buff_levels: dict) -> None:
        """Restore buff levels from save data.

        Handles both legacy short-name keys (piercing_level, etc.)
        and current proper buff names (Piercing, etc.).
        """
        if not buff_levels:
            return
        legacy_map = {
            'piercing_level': 'Piercing', 'spread_level': 'Spread Shot',
            'explosive_level': 'Explosive', 'armor_level': 'Armor',
            'evasion_level': 'Evasion', 'rapid_fire_level': 'Rapid Fire',
        }
        for key, value in buff_levels.items():
            name = legacy_map.get(key, key)
            if name in self.reward_system.buff_levels:
                self.reward_system.buff_levels[name] = value

    def _restore_earned_buff_levels(self, earned_buff_levels: dict) -> None:
        if not self.reward_system:
            return
        if not earned_buff_levels:
            self.reward_system.earned_buff_levels = dict(self.reward_system.buff_levels)
            return
        for key, value in earned_buff_levels.items():
            if key in self.reward_system.earned_buff_levels:
                self.reward_system.earned_buff_levels[key] = max(0, int(value))

    def _reapply_buff_effects(self) -> None:
        """Re-apply all buff effects after restoring levels from save."""
        if not self.reward_system or not self.player:
            return
        self.reward_system.reapply_all_effects(self.player)

    def _restore_talent_loadout_effects(self) -> None:
        if not self.reward_system or not self.player:
            return
        if not self.reward_system.talent_loadout:
            self.reward_system.reapply_all_effects(self.player)
            return
        manager = TalentBalanceManager(
            self.reward_system.get_earned_buff_levels(),
            self.reward_system.talent_loadout,
        )
        manager.apply_to_reward_system(self.reward_system, self.player)

    def _restore_to_mothership_state(self) -> None:
        """Restore mothership state with player docked inside."""
        if self._mother_ship_integrator:
            self._mother_ship_integrator.force_docked_state()
            docking_pos = self._mother_ship_integrator._mother_ship.get_docking_position()
            self.player.rect.x = docking_pos[0] - self.player.rect.width // 2
            self.player.rect.y = docking_pos[1] - self.player.rect.height // 2
        else:
            screen_w = get_screen_width()
            screen_h = get_screen_height()
            self.player.rect.x = screen_w // 2 - self.player.rect.width // 2
            self.player.rect.y = screen_h // 2

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
            self._game_loop_manager._explosion_manager.trigger_boss_death(
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
            )

    def add_score(self, amount: int) -> None:
        """Add to score."""
        if self.game_controller:
            self.game_controller.state.score = normalize_score(
                self.game_controller.state.score + amount
            )

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
        if self.spawn_controller:
            self.spawn_controller.boss = None

    def set_player_invincible(self, invincible: bool, timer: int, silent: bool = False) -> None:
        """Set player invincibility state.

        When silent=True, the player is invincible without the blink flash effect.
        """
        if self.game_controller:
            self.game_controller.state.player_invincible = invincible
            self.game_controller.state.invincibility_timer = timer
            self.game_controller.state.silent_invincible = silent

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

    def get_buff_levels(self) -> Dict[str, int]:
        """Get buff levels dictionary."""
        if not self.reward_system:
            return {}
        return dict(self.reward_system.buff_levels)

    def get_earned_buff_levels(self) -> Dict[str, int]:
        if not self.reward_system:
            return {}
        return self.reward_system.get_earned_buff_levels()

    def get_talent_loadout(self) -> Dict[str, str]:
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
        return self.game_controller.state.username if self.game_controller else 'Player'

    def set_paused(self, paused: bool) -> None:
        """Set game paused state."""
        if self.game_controller:
            self.game_controller.state.paused = paused

    def clear_ripple_effects(self) -> None:
        """Clear all ripple effects."""
        if self.game_controller:
            self.game_controller.state.ripple_effects.clear()
