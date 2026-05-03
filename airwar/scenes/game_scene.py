"""Main game scene -- gameplay loop, entity coordination, and rendering."""
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
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.ui.reward_selector import RewardSelector
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.warning_banner import WarningBanner
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
from airwar.game.managers import (
    BulletManager,
    BossManager,
    MilestoneManager,
    InputCoordinator,
    UIManager,
    GameLoopManager,
)
from airwar.config import DIFFICULTY_SETTINGS, BOOST_CONFIG, get_screen_width, get_screen_height
from airwar.input import PygameInputHandler
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.config.design_tokens import get_design_tokens
from airwar.utils.sprites import prewarm_glow_caches


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
        self._give_up_detector = None
        self._give_up_ui = None
        self._bullet_manager: BulletManager = None
        self._boss_manager: BossManager = None
        self._milestone_manager: MilestoneManager = None
        self._input_coordinator: InputCoordinator = None
        self._ui_manager: UIManager = None
        self._game_loop_manager: GameLoopManager = None

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
        self._loading_progress = 100
        self._is_loading = False

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        self._init_pause_button_layout()

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
        self.player.rect.y = PlayerConstants.INITIAL_Y
        self.player.bullet_damage = settings['bullet_damage']
        boost_cfg = BOOST_CONFIG[difficulty]
        self.player.boost_max = boost_cfg['max_boost']
        self.player.boost_current = boost_cfg['max_boost']
        self.player.boost_recovery_rate = boost_cfg['recovery_rate']
        self.player.boost_speed_mult = boost_cfg['speed_mult']
        self.player.boost_recovery_delay = boost_cfg['recovery_delay']
        self.player.boost_recovery_ramp = boost_cfg['recovery_ramp']
        self._boost_gauge = BoostGauge()
        self._ammo_magazine = AmmoMagazine()
        self._warning_banner = WarningBanner()

        self._setup_reward_selector()
        self._init_mother_ship_system(screen_width, screen_height)
        self._init_give_up_system(screen_width, screen_height)
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

    def _setup_reward_selector(self) -> None:
        self.reward_selector.hide = lambda: setattr(self.reward_selector, 'visible', False)
        self.reward_selector.visible = False

    def _init_mother_ship_system(self, screen_width: int, screen_height: int) -> None:
        event_bus = EventBus()
        input_detector = InputDetector(event_bus)
        state_machine = MotherShipStateMachine(event_bus)
        persistence_manager = PersistenceManager()
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
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.handle_mouse_click(event.pos):
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

        if self.game_renderer and self.game_renderer.integrated_hud:
            unlocked_buffs = getattr(self.reward_system, 'unlocked_buffs', [])
            self.game_renderer.integrated_hud.update_scroll(len(unlocked_buffs))
            if self.player:
                self.game_renderer.integrated_hud.update_health_tank(
                    self.player.health, self.player.max_health)
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
                                     status['max'], status['active'])

        # Ammo magazine -- left-side vertical ammo rack
        if self._ammo_magazine and self._mother_ship_integrator:
            ms_data = self._mother_ship_integrator.get_status_data()
            self._ammo_magazine.render(
                surface,
                ammo_count=ms_data.get('ammo_count', 0.0),
                ammo_max=ms_data.get('ammo_max', 10.0),
                is_cooldown=ms_data.get('is_in_cooldown', False),
                is_docked=ms_data.get('is_docked', False),
                is_warning=ms_data.get('ammo_count', 0.0) <= 3.0,
                is_present=ms_data.get('is_present', False),
            )

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

        self._game_loop_manager.render_explosions(surface)
        self._input_coordinator.render_give_up(surface)

        # Warning banner -- top-of-screen scrolling ammo depletion alert
        if self._warning_banner:
            self._warning_banner.render(surface)

        # Reward selector must render last to cover all game elements
        if self.reward_selector.visible:
            self.reward_selector.render(surface)

        # Render notifications above reward selector so critical messages are not obscured
        self._ui_manager.render_notification(surface)

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
            self.game_controller.state.score = value

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
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = True

    def resume(self) -> None:
        """Resume the game."""
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

        self.game_controller.state.score = save_data.score
        self.game_controller.state.kill_count = save_data.kill_count
        self.game_controller.state.boss_kill_count = save_data.boss_kill_count
        self.game_controller.milestone_index = save_data.cycle_count
        self.game_controller.cycle_count = save_data.cycle_count

        self.player.health = save_data.player_health
        self.player.max_health = save_data.player_max_health

        self.reward_system.unlocked_buffs = save_data.unlocked_buffs
        self._restore_buff_levels(save_data.buff_levels)
        self._reapply_buff_effects()

        self.game_controller.state.difficulty = save_data.difficulty
        self.game_controller.state.username = save_data.username
        self.game_controller.state.score_multiplier = {'easy': 1, 'medium': 2, 'hard': 3}.get(save_data.difficulty, 1)

        if save_data.is_in_mothership:
            self._restore_to_mothership_state()
        elif save_data.player_x != 0 or save_data.player_y != 0:
            self.player.rect.x = save_data.player_x
            self.player.rect.y = save_data.player_y
        else:
            self.player.rect.y = get_screen_height() - PlayerConstants.SCREEN_BOTTOM_OFFSET

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

    def _reapply_buff_effects(self) -> None:
        """Re-apply all buff effects after restoring levels from save."""
        if not self.reward_system or not self.player:
            return
        handlers = self.reward_system._buff_apply_handlers
        for buff_name, level in self.reward_system.buff_levels.items():
            if level > 0 and buff_name in handlers:
                handlers[buff_name](self.player)

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

    def add_score(self, amount: int) -> None:
        """Add to score."""
        if self.game_controller:
            self.game_controller.state.score += amount

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

