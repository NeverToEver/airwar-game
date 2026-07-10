"""Playable tutorial scene -- controlled lessons for the core game mechanics.

Phase 4 Wave α: god-class split. The scene keeps lifecycle
(``enter``/``exit``/``update``/``render``/``handle_events``), the
stage machine, the input/player helpers, and 1-line forwarders
into five simulator/pool components living under
:mod:`airwar.scenes.tutorial`:

* :class:`~airwar.scenes.tutorial.TutorialPlayer` -- simulated player
* :class:`~airwar.scenes.tutorial.TutorialBossSimulator` -- simulated boss
* :class:`~airwar.scenes.tutorial.TutorialBulletPool` -- bullet pool
* :class:`~airwar.scenes.tutorial.TutorialExplosionPool` -- explosion pool
* :class:`~airwar.scenes.tutorial.TutorialEnemySimulator` -- enemy sim

The four entity dataclasses (``TutorialEnemy``, ``TutorialBullet``,
``TutorialBoss``, ``TutorialExplosion``) stay defined here because the
collision code imports them from :mod:`airwar.scenes.tutorial_scene`.
"""

from __future__ import annotations

import pygame

from airwar.config import TUTORIAL_STAGES, TutorialStage, get_screen_height, get_screen_width
from airwar.config.design_tokens import SceneColors, get_design_tokens
from airwar.i18n import t as _t
from airwar.game.mother_ship import MotherShip
from airwar.game.frame_context import FrameContext
from airwar.game.rendering import GameRenderer
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.base_talent_console import BaseTalentConsole, BaseTalentConsoleAction
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.discrete_battery import DiscreteBatteryIndicator
from airwar.ui.warning_banner import WarningBanner
from airwar.utils.fonts import get_cjk_font
from airwar.utils.mouse_interaction import MouseInteractiveMixin

from .scene import Scene
from .tutorial import (
    TutorialBossSimulator,
    TutorialBulletPool,
    TutorialEnemySimulator,
    TutorialExplosionPool,
    TutorialPlayer,
    aim_assist,
    base_console,
    entities,
)
from .tutorial.models import TutorialBaseGameController, TutorialBasePlayerStatus
from .tutorial.stages import BaseStage, build_stage
from .tutorial_scene_renderer import TutorialSceneRenderer

# Re-export the entity dataclasses from their canonical home so the existing
# import path ``from airwar.scenes.tutorial_scene import TutorialBullet``
# keeps working. The canonical definitions live in
# :mod:`airwar.scenes.tutorial.entities_core` so the sim / entity / pool
# files in the subpackage can import them at module level (M-4).
from airwar.scenes.tutorial.entities_core import (  # noqa: E402,F401
    TutorialBoss,
    TutorialBullet,
    TutorialEnemy,
    TutorialExplosion,
)


# Re-export the base-console data classes so existing imports
# (``from airwar.scenes.tutorial_scene import TutorialBasePlayerStatus``)
# keep working. The canonical definitions live in
# :mod:`airwar.scenes.tutorial.models` so other submodules can import
# them without a circular import.


class TutorialScene(Scene, MouseInteractiveMixin):
    """Self-contained tutorial with a stage machine and simplified combat."""

    uses_fixed_simulation = True

    PLAYER_W = 68
    PLAYER_H = 82
    ENEMY_SIZE = 56
    BOSS_W = 210
    BOSS_H = 170
    WING_MUZZLE_X_OFFSETS = (-24, 24)
    WING_MUZZLE_Y_OFFSET = -36
    PLAYER_SPEED = 5.0
    BOOST_MULT = 1.75
    ENERGY_MAX = 100.0
    ENERGY_DRAIN = 0.95
    ENERGY_RECOVER = 0.55
    PHASE_DASH_COST = 24.0
    PHASE_DASH_FRAMES = 12
    FIRE_INTERVAL = 10
    PLAYER_BULLET_DAMAGE = 16
    PLAYER_HIT_COOLDOWN = 42
    DOCK_HOLD_FRAMES = 180
    HOME_HOLD_FRAMES = 144
    FADE_FRAMES = 24
    COMPLETION_DELAY = 48
    DOCK_ENTER_FRAMES = 30
    DOCK_UNDOCK_FRAMES = 80
    DEPART_FRAMES = 72
    MOTHERSHIP_VOLLEY_FRAMES = 30
    MOTHERSHIP_STARTING_AMMO = 5.0
    MOTHERSHIP_AMMO_DRAIN = 0.04
    ESCAPE_FRAMES = 300
    STAGE_CARD_SLIDE_FRAMES = 22
    STAGE_CARD_HOLD_FRAMES = 90
    STAGE_CARD_FADE_FRAMES = 28
    AIM_ASSIST_SWITCH_DISTANCE = 90.0
    AIM_ASSIST_RELEASE_DISTANCE = 230.0
    AIM_ASSIST_DIRECTION_CONE_DOT = 0.42
    AIM_INPUT_DELAY_BLEND = 0.28
    AIM_INPUT_SNAP_DISTANCE = 10.0
    AIM_ASSIST_RELEASE_FRAMES = 12
    BOSS_ENRAGE_THRESHOLD = 0.30
    WARNING_CELL_THRESHOLD = AmmoMagazine.WARNING_CELL_THRESHOLD

    # Runtime state populated by ``enter()`` / the player simulator.
    # Declared here so split renderers and helpers can type-check.
    _player: pygame.Rect
    _player_health: int
    _player_max_health: int
    _player_energy: float
    _player_hit_cooldown: int
    _dash_frames: int
    _dash_velocity: pygame.Vector2
    _fire_timer: int
    _bullets: list[TutorialBullet]
    _enemy_bullets: list[TutorialBullet]
    _enemies: list[TutorialEnemy]
    _boss: TutorialBoss | None
    _tutorial_explosions: list[TutorialExplosion]
    _score: int
    _kills: int
    _stage_progress: int
    _stage_spawned: int
    _hold_h_frames: int
    _hold_b_frames: int
    _mothership_ammo: float
    _ammo_warning_triggered: bool
    _escape_timer: int
    _boost_feedback_timer: int
    _player_enter_start_center: pygame.Vector2
    _dock_eject_position: pygame.Vector2
    _pending_base_sub_phase: str | None
    _dock_undock_phase: str
    _dock_sub_phase: str
    _base_sub_phase: str
    _mothership_fire_timer: int
    _base_ready: bool
    _docked: bool
    _player_enter_timer: int
    _dock_undock_timer: int
    _dock_undock_player_frames: int
    _depart_timer: int
    _stage_card_timer: int
    _stage_completed: bool
    _completion_delay: int
    _fade_phase: str
    _fade_alpha: int
    _pending_stage_index: int | None
    _cleared_stage_ids: list[str]
    _animation_time: int
    _stage_index: int
    _keys_down: set[int]
    _raw_aim_position: tuple[float, float]
    _previous_raw_aim_position: tuple[float, float]
    _smoothed_raw_aim_position: tuple[float, float]
    _aim_pos: tuple[float, float]
    _aim_assist_target: TutorialEnemy | TutorialBoss | None
    _aim_input_initialized: bool
    _aim_assist_release_timer: int

    def __init__(self) -> None:
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._tokens = get_design_tokens()
        self._game_renderer: GameRenderer | None = None
        self._background_size: tuple[int, int] | None = None
        self._aim_crosshair = AimCrosshair()
        self._boost_gauge = BoostGauge()
        self._battery_indicator = DiscreteBatteryIndicator(
            width=30,
            height=180,
            num_segments=30,
            orientation="vertical",
        )
        self._mothership: MotherShip | None = None
        self._ammo_magazine: AmmoMagazine | None = None
        self._warning_banner: WarningBanner | None = None
        self._base_talent_console: BaseTalentConsole | None = None
        self._base_reward_system = None
        self._base_player_status: TutorialBasePlayerStatus | None = None
        self._base_game_controller: TutorialBaseGameController | None = None
        self._viewport = None
        self._renderer: TutorialSceneRenderer | None = None
        # Active per-stage logic instance. Rebuilt by ``_load_stage``;
        # ``None`` until ``enter()`` runs.
        self._stage_instance: BaseStage | None = None
        # Simulator and pool components are built once per scene.
        self._player_sim = TutorialPlayer(self)
        self._boss_sim = TutorialBossSimulator(self)
        self._bullet_pool = TutorialBulletPool(self)
        self._explosion_pool = TutorialExplosionPool(self)
        self._enemy_sim = TutorialEnemySimulator(self)
        self._talent_balance_manager = None
        self.running = False
        self.skipped = False

    def enter(self, **kwargs) -> None:
        pygame.font.init()
        self.running = True
        self.skipped = False
        self._viewport = kwargs.get("viewport")
        self.clear_hover()
        self.clear_buttons()

        self._title_font = get_cjk_font(36)
        self._heading_font = get_cjk_font(28)
        self._body_font = get_cjk_font(22)
        self._small_font = get_cjk_font(18)
        self._tiny_font = get_cjk_font(15)

        self._animation_time = 0
        self._stage_index = 0
        self._cleared_stage_ids: list[str] = []
        self._fade_phase = "in"
        self._fade_alpha = 255
        self._pending_stage_index: int | None = None
        self._completion_delay = 0
        self._stage_completed = False
        self._stage_card_timer = 0

        self._keys_down: set[int] = set()
        self._raw_aim_position = (0.0, 0.0)
        self._previous_raw_aim_position = (0.0, 0.0)
        self._smoothed_raw_aim_position = (0.0, 0.0)
        self._aim_pos = (0.0, 0.0)
        self._aim_assist_target: TutorialEnemy | TutorialBoss | None = None
        self._aim_input_initialized = False
        self._aim_assist_release_timer = 0
        self._set_raw_aim_position(self._get_logical_mouse_pos())
        self._player_sim.initialise()

        self._bullets: list[TutorialBullet] = []
        self._enemy_bullets: list[TutorialBullet] = []
        self._enemies: list[TutorialEnemy] = []
        self._boss: TutorialBoss | None = None
        self._score = 0
        self._kills = 0
        self._stage_progress = 0
        self._stage_spawned = 0
        self._hold_h_frames = 0
        self._hold_b_frames = 0
        self._docked = False
        self._dock_sub_phase = "approach"
        self._player_enter_timer = 0
        self._player_enter_start_center = pygame.Vector2(self._player.center)
        self._dock_undock_timer = 0
        self._dock_undock_player_frames = 24
        self._dock_undock_phase = ""
        self._dock_eject_position = pygame.Vector2(self._player.center)
        self._mothership_fire_timer = self.MOTHERSHIP_VOLLEY_FRAMES
        self._base_ready = False
        self._base_sub_phase = "combat"
        self._depart_timer = 0
        self._pending_base_sub_phase: str | None = None
        self._mothership_ammo = 10.0
        self._ammo_warning_triggered = False
        self._tutorial_explosions: list[TutorialExplosion] = []
        self._escape_timer = 0
        self._boost_feedback_timer = 0

        sw = get_screen_width()
        sh = get_screen_height()
        self._game_renderer = GameRenderer(use_integrated_hud=False)
        self._game_renderer.init_background(sw, sh)
        self._background_size = (sw, sh)
        self._mothership = MotherShip(sw, sh)
        self._ammo_magazine = AmmoMagazine()
        self._warning_banner = WarningBanner()
        self._base_talent_console = BaseTalentConsole(sw, sh)
        self._setup_base_console_data()
        self._renderer = TutorialSceneRenderer(self)
        self._load_stage(0)

    def exit(self) -> None:
        self.clear_buttons()
        self._keys_down.clear()

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._keys_down.add(event.key)
            if event.key == pygame.K_ESCAPE:
                self._return_to_menu(skipped=True)
                return
            if self._is_summary_stage() and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._return_to_menu(skipped=False)
                return
            if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self._handle_boost_tap()
        elif event.type == pygame.KEYUP:
            self._keys_down.discard(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self._set_raw_aim_position(event.pos)
            if self._is_base_console_active() and self._base_talent_console:
                self._base_talent_console.handle_mouse_motion(event.pos)
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._set_raw_aim_position(event.pos)
                if self._is_base_console_active() and self._handle_base_console_click(event.pos):
                    return
                if self.handle_mouse_click(event.pos):
                    self._handle_button_click(self.get_hovered_button())

    def update(self, frame: FrameContext | None = None, *args, **kwargs) -> None:
        steps = frame.simulation_steps if frame is not None else 1
        for _ in range(steps):
            self._update_simulation()

    def _update_simulation(self) -> None:
        if not self.running:
            return

        self._animation_time += 1
        if self._stage_card_timer > 0:
            self._stage_card_timer -= 1
        if self._player_hit_cooldown > 0:
            self._player_hit_cooldown -= 1
        if self._boost_feedback_timer > 0:
            self._boost_feedback_timer -= 1

        self._aim_crosshair.update()
        self._battery_indicator.set_health(self._player_health, self._player_max_health)
        if self._warning_banner:
            self._warning_banner.update()
        if self._base_talent_console and self._is_base_console_active():
            self._base_talent_console.update()

        self._update_fade()
        if self._fade_phase == "out":
            return

        if self._is_summary_stage():
            return

        self._update_aim_assist()
        if self._world_update_locked():
            self._update_stage_logic()
            self._cleanup_entities()
            self._update_tutorial_effects()
            self._check_stage_completion()
            return

        self._update_player()
        self._update_stage_logic()
        self._update_bullets()
        self._update_enemies()
        self._update_boss()
        self._handle_collisions()
        self._cleanup_entities()
        self._update_tutorial_effects()
        self._check_stage_completion()

    def render(self, surface: pygame.Surface) -> None:
        if self._renderer:
            self._renderer.render(surface)
        else:
            # Fallback before enter() is called
            surface.fill(SceneColors.BG_PRIMARY)

    def is_running(self) -> bool:
        return self.running

    def was_skipped(self) -> bool:
        return self.skipped

    # -- Stage machine -------------------------------------------------

    @property
    def _stage(self) -> TutorialStage:
        return TUTORIAL_STAGES[self._stage_index]

    def _load_stage(self, index: int) -> None:
        self._stage_index = max(0, min(index, len(TUTORIAL_STAGES) - 1))
        self._stage_progress = 0
        self._stage_spawned = 0
        self._stage_completed = False
        self._completion_delay = 0
        self._stage_card_timer = (
            self.STAGE_CARD_SLIDE_FRAMES + self.STAGE_CARD_HOLD_FRAMES + self.STAGE_CARD_FADE_FRAMES
        )
        self._hold_h_frames = 0
        self._hold_b_frames = 0
        self._docked = False
        self._dock_sub_phase = "approach"
        self._player_enter_timer = 0
        self._player_enter_start_center = pygame.Vector2(self._player.center)
        self._dock_undock_timer = 0
        self._dock_undock_player_frames = 24
        self._dock_undock_phase = ""
        self._dock_eject_position = pygame.Vector2(self._player.center)
        self._mothership_fire_timer = self.MOTHERSHIP_VOLLEY_FRAMES
        self._base_ready = False
        self._base_sub_phase = "combat"
        self._depart_timer = 0
        self._pending_base_sub_phase = None
        self._mothership_ammo = 10.0
        self._ammo_warning_triggered = False
        self._escape_timer = 0
        self._bullets.clear()
        self._enemy_bullets.clear()
        self._enemies.clear()
        self._tutorial_explosions.clear()
        self._boss = None
        self._fire_timer = 0
        if self._warning_banner:
            self._warning_banner.reset()
        if self._mothership:
            self._mothership.hide()
            self._mothership.hide_phantom()
            self._mothership.deactivate_flyaway()

        self._player_sim.reset_to_spawn()

        setup = self._stage.spawn_setup
        if setup == "movement_targets":
            self._spawn_training_targets()
        elif setup == "easy_enemies":
            self._spawn_easy_enemy_wave(initial=True)
        elif setup == "boss":
            self._spawn_boss()

        if self._stage.id == "mothership_docking":
            self._spawn_training_targets()
            sw = get_screen_width()
            sh = get_screen_height()
            if self._mothership:
                self._mothership.show()
                self._mothership.show_phantom()
                self._mothership.set_position(sw // 2, max(190, int(sh * 0.32)))
        elif self._stage.id == "homecoming_base":
            self._spawn_homecoming_enemy_wave()
            self._player_health = self._player_max_health
            self._player_energy = self.ENERGY_MAX
            if self._base_talent_console:
                self._base_talent_console._active_module = "supply"
            if self._base_game_controller:
                self._base_game_controller.state.requisition_points = 10
            if self._base_player_status:
                self._base_player_status.health = max(1, self._base_player_status.max_health - 42)
                self._base_player_status.boost_current = max(0.0, self._base_player_status.boost_max - 36.0)

        if self._is_summary_stage():
            self._mark_current_stage_cleared()

        # Build the per-frame stage instance for the active stage.
        self._stage_instance = build_stage(self._stage.id, self)

    def _start_stage_transition(self, next_index: int) -> None:
        if self._fade_phase:
            return
        self._pending_stage_index = next_index
        self._fade_phase = "out"
        self._fade_alpha = 0

    def _update_fade(self) -> None:
        if not self._fade_phase:
            return

        step = max(1, 255 // self.FADE_FRAMES)
        if self._fade_phase == "out":
            self._fade_alpha = min(255, self._fade_alpha + step)
            if self._fade_alpha >= 255:
                if self._pending_base_sub_phase == "base":
                    self._enter_homecoming_base()
                elif self._pending_stage_index is not None:
                    self._load_stage(self._pending_stage_index)
                self._pending_base_sub_phase = None
                self._pending_stage_index = None
                self._fade_phase = "in"
            return

        self._fade_alpha = max(0, self._fade_alpha - step)
        if self._fade_alpha <= 0:
            self._fade_phase = ""

    def _check_stage_completion(self) -> None:
        if self._stage_completed or self._fade_phase:
            return

        if self._stage.id == "mothership_docking":
            if (
                self._dock_sub_phase == "eject_player"
                and self._dock_undock_phase == "mothership"
                and (not self._mothership or not self._mothership.is_visible())
            ):
                self._enemies.clear()
                self._enemy_bullets.clear()
                self._bullets.clear()
                self._mark_stage_complete()
            return

        if self._stage.id == "homecoming_base":
            if self._base_sub_phase == "depart" and self._depart_timer <= 0:
                self._mark_stage_complete()
            return

        if self._stage_progress >= self._stage.objective_count:
            self._mark_stage_complete()
            return

        if self._stage_completed:
            return

    def _mark_stage_complete(self) -> None:
        self._stage_completed = True
        self._completion_delay = self.COMPLETION_DELAY
        self._mark_current_stage_cleared()

    def _mark_current_stage_cleared(self) -> None:
        if self._stage.id not in self._cleared_stage_ids:
            self._cleared_stage_ids.append(self._stage.id)

    def _advance_after_delay(self) -> None:
        if not self._stage_completed:
            return
        self._completion_delay -= 1
        if self._completion_delay <= 0:
            self._start_stage_transition(self._stage_index + 1)

    def _is_summary_stage(self) -> bool:
        return self._stage.id == "tutorial_complete"

    def _setup_base_console_data(self) -> None:
        base_console.setup_base_console_data(self)

    # -- Input and player ----------------------------------------------

    def _handle_button_click(self, button_name: str | None) -> None:
        if button_name == "skip_tutorial":
            self._return_to_menu(skipped=True)
        elif button_name == "return_menu":
            self._return_to_menu(skipped=False)

    def _handle_base_console_click(self, pos: tuple[int, int]) -> bool:
        if not self._base_talent_console or not self._talent_balance_manager:
            return False
        action = self._base_talent_console.handle_mouse_click(pos)
        if action is None:
            return False
        self._handle_base_console_action(action)
        return True

    def _handle_base_console_action(self, action: BaseTalentConsoleAction) -> None:
        base_console.handle_base_console_action(self, action)

    def _repair_at_tutorial_base(self) -> None:
        base_console.repair_at_tutorial_base(self)

    def _recharge_at_tutorial_base(self) -> None:
        base_console.recharge_at_tutorial_base(self)

    def _resupply_at_tutorial_base(self) -> None:
        base_console.resupply_at_tutorial_base(self)

    def _return_to_menu(self, *, skipped: bool) -> None:
        self.skipped = skipped
        self.running = False

    def _handle_boost_tap(self) -> None:
        if self._stage.id != "boost_phase_dash" or self._stage_completed:
            return
        if self._player_energy < 8:
            return

        direction = self._movement_direction()
        if direction.length_squared() > 0 and self._player_energy >= self.PHASE_DASH_COST:
            direction = direction.normalize()
            self._dash_frames = self.PHASE_DASH_FRAMES
            self._dash_velocity = direction * 18
            self._player_energy = max(0, self._player_energy - self.PHASE_DASH_COST)
        else:
            self._player_energy = max(0, self._player_energy - 8)

        self._boost_feedback_timer = 24
        self._stage_progress = min(self._stage.objective_count, self._stage_progress + 1)

    def _movement_direction(self) -> pygame.Vector2:
        dx = 0
        dy = 0
        if pygame.K_a in self._keys_down or pygame.K_LEFT in self._keys_down:
            dx -= 1
        if pygame.K_d in self._keys_down or pygame.K_RIGHT in self._keys_down:
            dx += 1
        if pygame.K_w in self._keys_down or pygame.K_UP in self._keys_down:
            dy -= 1
        if pygame.K_s in self._keys_down or pygame.K_DOWN in self._keys_down:
            dy += 1
        vector = pygame.Vector2(dx, dy)
        if vector.length_squared() > 0:
            vector = vector.normalize()
        return vector

    def _boost_held(self) -> bool:
        return pygame.K_LSHIFT in self._keys_down or pygame.K_RSHIFT in self._keys_down

    def _is_base_console_active(self) -> bool:
        return self._stage.id == "homecoming_base" and self._base_sub_phase == "base"

    def _world_update_locked(self) -> bool:
        if self._stage.id == "mothership_docking":
            return self._dock_sub_phase in ("entering", "docked", "eject_player")
        if self._stage.id == "homecoming_base":
            return self._base_sub_phase in ("base", "depart")
        return False

    def _set_raw_aim_position(self, position: tuple[float, float]) -> None:
        x = max(0.0, min(float(position[0]), float(get_screen_width())))
        y = max(0.0, min(float(position[1]), float(get_screen_height())))
        if not self._aim_input_initialized:
            self._aim_input_initialized = True
            self._previous_raw_aim_position = (x, y)
            self._raw_aim_position = (x, y)
            self._smoothed_raw_aim_position = (x, y)
            self._aim_pos = (x, y)
            return
        self._previous_raw_aim_position = self._raw_aim_position
        self._raw_aim_position = (x, y)

    def _get_logical_mouse_pos(self) -> tuple[float, float]:
        pos = pygame.mouse.get_pos()
        if self._viewport:
            return self._viewport.screen_to_logical(*pos)
        return pos

    def _get_screen_dimensions(self) -> tuple[int, int]:
        """Return ``(width, height)`` of the active logical viewport."""
        return get_screen_width(), get_screen_height()

    def _update_aim_assist(self) -> None:
        aim_assist.update_aim_assist(self)

    def _update_smoothed_raw_aim_position(self) -> None:
        aim_assist.update_smoothed_raw_aim_position(self)

    def _resolve_aim_assist_target(self):
        return aim_assist.resolve_aim_assist_target(self)

    def _aim_assist_candidates(self):
        return aim_assist.aim_assist_candidates(self)

    def _is_aim_assist_locked(self, target, raw_x: float, raw_y: float) -> bool:
        return aim_assist.is_aim_assist_locked(self, target, raw_x, raw_y)

    def _raw_aim_movement(self) -> tuple[float, float]:
        return aim_assist.raw_aim_movement(self)

    def _target_in_movement_direction(self, candidates, movement):
        return aim_assist.target_in_movement_direction(self, candidates, movement)

    def _distance_sq_to_target(self, target, raw_x: float, raw_y: float) -> float:
        return aim_assist.distance_sq_to_target(target, raw_x, raw_y)

    def _update_player(self) -> None:
        self._player_sim.update()

    def _update_player_fire(self) -> None:
        self._player_sim.fire()

    # -- Stage logic ---------------------------------------------------
    #
    # The per-stage bodies live in :mod:`airwar.scenes.tutorial.stages`.
    # :meth:`_update_stage_logic` is the single dispatch site the scene's
    # per-frame update flow uses.

    def _update_stage_logic(self) -> None:
        if self._stage_instance is not None:
            self._stage_instance.update()
            return
        if self._stage_completed:
            self._advance_after_delay()

    def _update_docking_stage(self) -> None:
        """Run the active mothership-docking stage."""
        if self._stage_instance is not None and self._stage.id == "mothership_docking":
            self._stage_instance.update()
            return
        # No active stage is a no-op.
        return

    def _update_homecoming_stage(self) -> None:
        """Run the active homecoming-base stage."""
        if self._stage_instance is not None and self._stage.id == "homecoming_base":
            self._stage_instance.update()

    def _docking_player_center(self) -> tuple[int, int]:
        if not self._mothership:
            return self._player.center
        return self._mothership.get_docking_position()

    def _enter_homecoming_base(self) -> None:
        self._base_sub_phase = "base"
        self._base_ready = True
        self._stage_progress = 0
        self._enemies.clear()
        self._bullets.clear()
        self._enemy_bullets.clear()
        self._aim_assist_target = None
        if self._base_talent_console:
            self._base_talent_console._active_module = "supply"

    # -- Entity setup and update ---------------------------------------
    #
    # The bodies live in :mod:`airwar.scenes.tutorial.entities` and
    # the simulator/pool components. The scene delegates to them from
    # its update flow.

    def _spawn_training_targets(self) -> None:
        self._enemy_sim.spawn_training_targets()

    def _spawn_easy_enemy_wave(self, *, initial: bool) -> None:
        self._enemy_sim.spawn_easy_enemy_wave(initial=initial)

    def _spawn_homecoming_enemy_wave(self) -> None:
        self._enemy_sim.spawn_homecoming_enemy_wave()

    def _spawn_boss(self) -> None:
        self._boss_sim.spawn()

    def _mothership_destroy_nearest_enemy(self) -> None:
        entities.mothership_destroy_nearest_enemy(self)

    def _update_bullets(self) -> None:
        self._bullet_pool.update()

    def _update_tutorial_effects(self) -> None:
        self._explosion_pool.update()

    def _update_enemies(self) -> None:
        self._enemy_sim.update()

    def _update_boss(self) -> None:
        self._boss_sim.update()

    def _spawn_enemy_bullet(self, center: tuple[int, int], *, damage: int) -> None:
        self._bullet_pool.spawn_enemy_bullet(center, damage=damage)

    def _handle_collisions(self) -> None:
        entities.handle_collisions(self)

    def _damage_player(self, damage: int) -> None:
        entities.damage_player(self, damage)

    def _cleanup_entities(self) -> None:
        entities.cleanup_entities(self)

    # -- Data for renderer -----------------------------------------------

    def _mothership_status_data(self) -> dict:
        ammo_count = max(0.0, min(self.MOTHERSHIP_STARTING_AMMO, float(self._mothership_ammo)))
        return {
            "ammo_count": ammo_count,
            "ammo_max": self.MOTHERSHIP_STARTING_AMMO,
            "is_in_cooldown": False,
            "is_docked": self._dock_sub_phase == "docked",
            "ammo_warning": ammo_count < self.WARNING_CELL_THRESHOLD,
            "is_present": self._stage.id == "mothership_docking",
            "cooldown_remaining": 0.0,
            "cooldown_reduction": 0.5,
        }

    def _tutorial_missions(self) -> list[dict]:
        return [
            {
                "name": _t("tutorial.mission.eliminate.name"),
                "desc": _t("tutorial.mission.eliminate.desc"),
                "target": "kills",
                "goal": 5,
                "progress": min(self._kills, 5),
                "done": self._kills >= 5,
                "claimed": False,
            },
            {
                "name": _t("tutorial.mission.support.name"),
                "desc": _t("tutorial.mission.support.desc"),
                "target": "mothership",
                "goal": 1,
                "progress": 1 if self._dock_sub_phase in ("docked", "eject_player") else 0,
                "done": self._dock_sub_phase in ("docked", "eject_player"),
                "claimed": False,
            },
            {
                "name": _t("tutorial.mission.homecoming.name"),
                "desc": _t("tutorial.mission.homecoming.desc"),
                "target": "homecoming",
                "goal": 1,
                "progress": 1 if self._base_sub_phase in ("base", "depart") else 0,
                "done": self._base_sub_phase in ("base", "depart"),
                "claimed": False,
            },
        ]
