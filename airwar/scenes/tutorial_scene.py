"""Playable tutorial scene -- controlled lessons for the core game mechanics."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from .scene import Scene
from airwar.config import TUTORIAL_STAGES, TutorialStage, get_screen_width, get_screen_height
from airwar.config.design_tokens import SceneColors, get_design_tokens
from airwar.game.mother_ship import MotherShip
from airwar.game.rendering import GameRenderer
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.ui.aim_crosshair import AimCrosshair
from airwar.ui.ammo_magazine import AmmoMagazine
from airwar.ui.base_talent_console import BaseTalentConsole
from airwar.ui.boost_gauge import BoostGauge
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.discrete_battery import DiscreteBatteryIndicator
from airwar.ui.scene_rendering_utils import fit_text_to_width, wrap_text
from airwar.ui.warning_banner import WarningBanner
from airwar.utils.fonts import get_cjk_font
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.utils.sprites import draw_boss_ship, draw_bullet, draw_enemy_ship, draw_player_ship


@dataclass
class TutorialEnemy:
    rect: pygame.Rect
    health: int
    max_health: int
    speed: float
    score_value: int
    kind: str = "target"
    active: bool = True
    phase: float = 0.0
    fire_timer: int = 0


@dataclass
class TutorialBullet:
    rect: pygame.Rect
    velocity: pygame.Vector2
    owner: str
    damage: int
    bullet_type: str = "single"
    active: bool = True


@dataclass
class TutorialBoss:
    rect: pygame.Rect
    health: int
    max_health: int
    active: bool = True
    phase: float = 0.0
    fire_timer: int = 0
    enraged: bool = False


@dataclass
class TutorialBasePlayerStatus:
    """Minimal player-shaped status object for the real base console."""

    health: int = 78
    max_health: int = 120
    boost_current: float = 64.0
    boost_max: float = 100.0
    bullet_damage: int = 62
    fire_interval: int = 7
    boost_recovery_rate: float = 1.0
    phase_dash_enabled: bool = True
    mothership_cooldown_mult: float = 0.5

    def get_boost_status(self) -> dict:
        return {
            "current": self.boost_current,
            "max": self.boost_max,
            "active": False,
            "dash_enabled": self.phase_dash_enabled,
            "dash_cooldown": 0,
        }

    def set_weapon_modifiers(self, spread: bool, laser: bool, explosive: bool) -> None:
        self.weapon_spread = spread
        self.weapon_laser = laser
        self.weapon_explosive = explosive

    def activate_shotgun(self) -> None:
        self.weapon_spread = True

    def activate_laser(self, _duration: int) -> None:
        self.weapon_laser = True

    def activate_explosive(self) -> None:
        self.weapon_explosive = True

    def activate_phase_dash(self) -> None:
        self.phase_dash_enabled = True


@dataclass
class TutorialBaseGameState:
    score: int = 860
    kill_count: int = 5
    boss_kill_count: int = 1
    difficulty: str = "medium"
    requisition_points: int = 80


class TutorialBaseGameController:
    """Small controller facade with the methods read by BaseTalentConsole."""

    def __init__(self) -> None:
        self.state = TutorialBaseGameState()

    def get_next_progress(self) -> int:
        return 72

    def get_next_threshold(self) -> int:
        return 1200


class TutorialScene(Scene, MouseInteractiveMixin):
    """Self-contained tutorial with a stage machine and simplified combat."""

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

    def __init__(self):
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
        self._talent_balance_manager: TalentBalanceManager | None = None
        self._base_reward_system: RewardSystem | None = None
        self._base_player_status: TutorialBasePlayerStatus | None = None
        self._base_game_controller: TutorialBaseGameController | None = None
        self.running = False
        self.skipped = False

    def enter(self, **kwargs) -> None:
        pygame.font.init()
        self.running = True
        self.skipped = False
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
        self._set_raw_aim_position(pygame.mouse.get_pos())
        self._player = pygame.Rect(
            get_screen_width() // 2 - self.PLAYER_W // 2,
            get_screen_height() - 126,
            self.PLAYER_W,
            self.PLAYER_H,
        )
        self._player_health = 100
        self._player_max_health = 100
        self._player_energy = self.ENERGY_MAX
        self._player_hit_cooldown = 0
        self._dash_frames = 0
        self._dash_velocity = pygame.Vector2(0, 0)
        self._fire_timer = 0

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
        self._base_ready = False
        self._mothership_ammo = 10.0
        self._ammo_warning_triggered = False
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
            if self._stage.id == "homecoming_base" and self._base_talent_console:
                self._base_talent_console.handle_mouse_motion(event.pos)
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._set_raw_aim_position(event.pos)
                if self._stage.id == "homecoming_base" and self._handle_base_console_click(event.pos):
                    return
                if self.handle_mouse_click(event.pos):
                    self._handle_button_click(self.get_hovered_button())

    def update(self, *args, **kwargs) -> None:
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
        if self._base_talent_console and self._stage.id == "homecoming_base":
            self._base_talent_console.update()

        self._update_fade()
        if self._fade_phase == "out":
            return

        if self._is_summary_stage():
            return

        self._update_aim_assist()
        self._update_player()
        self._update_stage_logic()
        self._update_bullets()
        self._update_enemies()
        self._update_boss()
        self._handle_collisions()
        self._cleanup_entities()
        self._check_stage_completion()

    def render(self, surface: pygame.Surface) -> None:
        self.clear_buttons()
        self._render_background(surface)

        if self._is_summary_stage():
            self._render_summary(surface)
        else:
            if self._stage.id == "homecoming_base":
                self._render_base_talent_console(surface)
            else:
                self._render_world(surface)
            self._render_stage_overlay(surface)
            self._render_status_bar(surface)

        self._render_skip_button(surface)
        self._render_fade(surface)
        self._render_stage_title_card(surface)

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
            self.STAGE_CARD_SLIDE_FRAMES
            + self.STAGE_CARD_HOLD_FRAMES
            + self.STAGE_CARD_FADE_FRAMES
        )
        self._hold_h_frames = 0
        self._hold_b_frames = 0
        self._docked = False
        self._base_ready = False
        self._mothership_ammo = 10.0
        self._ammo_warning_triggered = False
        self._escape_timer = 0
        self._bullets.clear()
        self._enemy_bullets.clear()
        self._enemies.clear()
        self._boss = None
        self._fire_timer = 0
        if self._warning_banner:
            self._warning_banner.reset()
        if self._mothership:
            self._mothership.hide()
            self._mothership.deactivate_flyaway()

        sw = get_screen_width()
        sh = get_screen_height()
        self._player.center = (sw // 2, sh - 112)
        self._player_health = self._player_max_health
        self._player_energy = self.ENERGY_MAX
        self._dash_frames = 0
        self._dash_velocity.update(0, 0)

        setup = self._stage.spawn_setup
        if setup == "movement_targets":
            self._spawn_training_targets()
        elif setup == "easy_enemies":
            self._spawn_easy_enemy_wave(initial=True)
        elif setup == "boss":
            self._spawn_boss()

        if self._stage.id == "mothership_docking" and self._mothership:
            self._mothership.show()
            self._mothership.set_position(sw // 2, max(190, int(sh * 0.32)))

        if self._is_summary_stage():
            self._mark_current_stage_cleared()

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
                if self._pending_stage_index is not None:
                    self._load_stage(self._pending_stage_index)
                self._pending_stage_index = None
                self._fade_phase = "in"
            return

        self._fade_alpha = max(0, self._fade_alpha - step)
        if self._fade_alpha <= 0:
            self._fade_phase = ""

    def _check_stage_completion(self) -> None:
        if self._stage_completed or self._fade_phase:
            return

        if self._stage_progress >= self._stage.objective_count:
            self._stage_completed = True
            self._completion_delay = self.COMPLETION_DELAY
            self._mark_current_stage_cleared()
            return

        if self._stage_completed:
            return

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
        self._base_player_status = TutorialBasePlayerStatus()
        self._base_game_controller = TutorialBaseGameController()
        self._base_reward_system = RewardSystem("medium")
        earned_levels = {
            "Spread Shot": 1,
            "Laser": 1,
            "Phase Dash": 1,
            "Mothership Recall": 1,
            "Power Shot": 1,
            "Boost Recovery": 1,
        }
        self._talent_balance_manager = TalentBalanceManager(
            earned_levels,
            {"offense": "Laser", "support": "Mothership Recall"},
        )
        self._talent_balance_manager.apply_to_reward_system(
            self._base_reward_system,
            self._base_player_status,
        )

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
        if action.kind == "continue":
            self._base_ready = True
            self._stage_progress = 1
            return True
        if action.kind in ("resupply", "repair"):
            self._base_ready = True
            self._stage_progress = 1
            if self._base_player_status:
                self._base_player_status.health = self._base_player_status.max_health
        if action.kind in ("resupply", "recharge"):
            self._base_ready = True
            self._stage_progress = 1
            if self._base_player_status:
                self._base_player_status.boost_current = self._base_player_status.boost_max
        if action.route:
            self._talent_balance_manager.next_option(action.route)
            if self._base_reward_system and self._base_player_status:
                self._talent_balance_manager.apply_to_reward_system(
                    self._base_reward_system,
                    self._base_player_status,
                )
        return True

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

    def _set_raw_aim_position(self, position: tuple[int, int]) -> None:
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

    def _update_aim_assist(self) -> None:
        self._update_smoothed_raw_aim_position()
        target = self._resolve_aim_assist_target()
        self._aim_pos = target.rect.center if target is not None else self._smoothed_raw_aim_position

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

    def _resolve_aim_assist_target(self) -> TutorialEnemy | TutorialBoss | None:
        if self._stage.id not in ("movement_aiming", "combat_basics", "boss_encounter"):
            self._aim_assist_target = None
            return None

        raw_x, raw_y = self._smoothed_raw_aim_position
        candidates = self._aim_assist_candidates()
        if not candidates:
            self._aim_assist_target = None
            return None

        movement = self._raw_aim_movement()
        movement_len_sq = movement[0] * movement[0] + movement[1] * movement[1]
        if movement_len_sq >= self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE:
            self._aim_assist_target = None
            self._aim_assist_release_timer = self.AIM_ASSIST_RELEASE_FRAMES
            return None

        if self._aim_assist_release_timer > 0:
            self._aim_assist_release_timer -= 1
            self._aim_assist_target = None
            return None

        if movement_len_sq >= self.AIM_ASSIST_SWITCH_DISTANCE * self.AIM_ASSIST_SWITCH_DISTANCE:
            directional_target = self._target_in_movement_direction(candidates, movement)
            if directional_target is not None:
                self._aim_assist_target = directional_target
                return directional_target
            if self._aim_assist_target in candidates:
                return self._aim_assist_target

        if self._aim_assist_target in candidates and self._is_aim_assist_locked(self._aim_assist_target, raw_x, raw_y):
            return self._aim_assist_target

        for target in candidates:
            if target.rect.collidepoint(raw_x, raw_y):
                self._aim_assist_target = target
                return target

        target = min(candidates, key=lambda candidate: self._distance_sq_to_target(candidate, raw_x, raw_y))
        self._aim_assist_target = target
        return target

    def _aim_assist_candidates(self) -> list[TutorialEnemy | TutorialBoss]:
        targets: list[TutorialEnemy | TutorialBoss] = [enemy for enemy in self._enemies if enemy.active]
        if self._boss is not None and self._boss.active:
            targets.append(self._boss)
        return targets

    def _is_aim_assist_locked(self, target: TutorialEnemy | TutorialBoss, raw_x: float, raw_y: float) -> bool:
        if not target.active:
            return False
        if target.rect.collidepoint(raw_x, raw_y):
            return True
        return self._distance_sq_to_target(target, raw_x, raw_y) <= (
            self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE
        )

    def _raw_aim_movement(self) -> tuple[float, float]:
        return (
            self._raw_aim_position[0] - self._previous_raw_aim_position[0],
            self._raw_aim_position[1] - self._previous_raw_aim_position[1],
        )

    def _target_in_movement_direction(
        self,
        candidates: list[TutorialEnemy | TutorialBoss],
        movement: tuple[float, float],
    ) -> TutorialEnemy | TutorialBoss | None:
        origin = self._aim_assist_target.rect.center if self._aim_assist_target in candidates else self._raw_aim_position
        movement_len = math.hypot(movement[0], movement[1])
        if movement_len <= 0:
            return None

        move_x = movement[0] / movement_len
        move_y = movement[1] / movement_len
        best_target = None
        best_score = 0.0
        for target in candidates:
            if target is self._aim_assist_target:
                continue
            tx = target.rect.centerx - origin[0]
            ty = target.rect.centery - origin[1]
            distance = math.hypot(tx, ty)
            if distance <= 0:
                continue
            dot = (tx / distance) * move_x + (ty / distance) * move_y
            if dot > best_score and dot >= self.AIM_ASSIST_DIRECTION_CONE_DOT:
                best_score = dot
                best_target = target
        return best_target

    def _distance_sq_to_target(self, target: TutorialEnemy | TutorialBoss, raw_x: float, raw_y: float) -> float:
        dx = raw_x - target.rect.centerx
        dy = raw_y - target.rect.centery
        return dx * dx + dy * dy

    def _update_player(self) -> None:
        if self._dash_frames > 0:
            self._player.x += int(self._dash_velocity.x)
            self._player.y += int(self._dash_velocity.y)
            self._dash_frames -= 1
        else:
            direction = self._movement_direction()
            speed = self.PLAYER_SPEED
            if self._boost_held() and self._player_energy > 0:
                speed *= self.BOOST_MULT
                self._player_energy = max(0, self._player_energy - self.ENERGY_DRAIN)
            else:
                self._player_energy = min(self.ENERGY_MAX, self._player_energy + self.ENERGY_RECOVER)
            self._player.x += int(direction.x * speed)
            self._player.y += int(direction.y * speed)

        sw = get_screen_width()
        sh = get_screen_height()
        self._player.clamp_ip(pygame.Rect(0, 128, sw, sh - 128))
        self._update_player_fire()

    def _update_player_fire(self) -> None:
        self._fire_timer -= 1
        if self._fire_timer > 0:
            return
        self._fire_timer = self.FIRE_INTERVAL

        aim_direction = pygame.Vector2(
            self._aim_pos[0] - self._player.centerx,
            self._aim_pos[1] - self._player.centery,
        )
        aim_direction = pygame.Vector2(0, -1) if aim_direction.length_squared() <= 1 else aim_direction.normalize()
        right = pygame.Vector2(-aim_direction.y, aim_direction.x)
        forward = aim_direction

        for offset_x in self.WING_MUZZLE_X_OFFSETS:
            muzzle = pygame.Vector2(self._player.center) + right * offset_x + forward * abs(self.WING_MUZZLE_Y_OFFSET)
            bullet_rect = pygame.Rect(0, 0, 10, 18)
            bullet_rect.center = (round(muzzle.x), round(muzzle.y))
            self._bullets.append(
                TutorialBullet(
                    rect=bullet_rect,
                    velocity=aim_direction * 13.0,
                    owner="player",
                    damage=self.PLAYER_BULLET_DAMAGE,
                )
            )

    # -- Stage logic ---------------------------------------------------

    def _update_stage_logic(self) -> None:
        if self._stage.id == "mothership_docking":
            self._update_docking_stage()
            if self._stage_completed:
                self._advance_after_delay()
            return

        if self._stage_completed:
            self._advance_after_delay()
            return

        if self._stage.id == "homecoming_base":
            self._update_homecoming_stage()
        elif self._stage.id == "combat_basics":
            if len(self._enemies) < 3 and self._stage_spawned < self._stage.objective_count:
                if self._animation_time % 38 == 0:
                    self._spawn_easy_enemy_wave(initial=False)
        elif self._stage.id == "boss_encounter":
            self._update_escape_timer()

    def _update_docking_stage(self) -> None:
        if self._mothership:
            sw, sh = get_screen_width(), get_screen_height()
            self._mothership.show()
            self._mothership.set_player_input(0, 0)
            self._mothership.set_position(sw // 2, max(190, int(sh * 0.32)))
            self._mothership.update()

        if pygame.K_h in self._keys_down:
            self._hold_h_frames = min(self.DOCK_HOLD_FRAMES, self._hold_h_frames + 1)
        elif not self._docked:
            self._hold_h_frames = max(0, self._hold_h_frames - 3)

        if not self._docked and self._hold_h_frames >= self.DOCK_HOLD_FRAMES:
            self._docked = True
            self._mothership_ammo = 4.0
            self._stage_progress = 1

        if self._docked:
            self._mothership_ammo = max(0.0, self._mothership_ammo - 0.045)
            if (
                not self._ammo_warning_triggered
                and self._mothership_ammo < self.WARNING_CELL_THRESHOLD
            ):
                self._ammo_warning_triggered = True
                if self._warning_banner:
                    self._warning_banner.activate()

    def _update_homecoming_stage(self) -> None:
        if pygame.K_b in self._keys_down:
            self._hold_b_frames = min(self.HOME_HOLD_FRAMES, self._hold_b_frames + 1)
        elif not self._base_ready:
            self._hold_b_frames = max(0, self._hold_b_frames - 3)

        if not self._base_ready and self._hold_b_frames >= self.HOME_HOLD_FRAMES:
            self._base_ready = True
            self._stage_progress = 1
            if self._base_talent_console:
                self._base_talent_console._active_module = "loadout"

    def _update_escape_timer(self) -> None:
        if self._boss is not None or self._escape_timer <= 0:
            return
        self._escape_timer -= 1
        if self._escape_timer <= 0:
            self._stage_progress = 1

    # -- Entity setup and update ---------------------------------------

    def _spawn_training_targets(self) -> None:
        sw = get_screen_width()
        y = max(230, int(get_screen_height() * 0.30))
        for index, x_ratio in enumerate((0.28, 0.50, 0.72)):
            rect = pygame.Rect(0, 0, self.ENEMY_SIZE, self.ENEMY_SIZE)
            rect.center = (int(sw * x_ratio), y + (index % 2) * 56)
            self._enemies.append(
                TutorialEnemy(
                    rect=rect,
                    health=34,
                    max_health=34,
                    speed=0.25,
                    score_value=75,
                    kind="target",
                    phase=index * 1.7,
                )
            )
            self._stage_spawned += 1

    def _spawn_easy_enemy_wave(self, *, initial: bool) -> None:
        spawn_slots = 3 if initial else 1
        sw = get_screen_width()
        for _ in range(spawn_slots):
            if self._stage_spawned >= self._stage.objective_count:
                return
            lane = self._stage_spawned % 5
            rect = pygame.Rect(0, 0, self.ENEMY_SIZE, self.ENEMY_SIZE)
            rect.center = (
                int(sw * (0.18 + lane * 0.16)),
                220 + (lane % 2) * 62,
            )
            self._enemies.append(
                TutorialEnemy(
                    rect=rect,
                    health=44,
                    max_health=44,
                    speed=0.65,
                    score_value=110,
                    kind="enemy",
                    phase=self._stage_spawned * 1.2,
                    fire_timer=40 + lane * 15,
                )
            )
            self._stage_spawned += 1

    def _spawn_boss(self) -> None:
        sw = get_screen_width()
        rect = pygame.Rect(0, 0, self.BOSS_W, self.BOSS_H)
        rect.center = (sw // 2, 246)
        self._boss = TutorialBoss(rect=rect, health=280, max_health=280)

    def _update_bullets(self) -> None:
        sw = get_screen_width()
        sh = get_screen_height()
        bounds = pygame.Rect(-120, -120, sw + 240, sh + 240)
        for bullet in self._bullets + self._enemy_bullets:
            if not bullet.active:
                continue
            bullet.rect.x += int(bullet.velocity.x)
            bullet.rect.y += int(bullet.velocity.y)
            if not bounds.colliderect(bullet.rect):
                bullet.active = False

    def _update_enemies(self) -> None:
        for enemy in self._enemies:
            if not enemy.active:
                continue
            enemy.phase += 0.035
            enemy.rect.x += int(math.sin(enemy.phase) * enemy.speed)
            if enemy.kind == "enemy":
                enemy.rect.y += int(math.sin(enemy.phase * 0.7) * 0.55)
                enemy.fire_timer -= 1
                if enemy.fire_timer <= 0:
                    enemy.fire_timer = 92
                    self._spawn_enemy_bullet(enemy.rect.center, damage=6)

    def _update_boss(self) -> None:
        boss = self._boss
        if boss is None or not boss.active:
            return

        boss.phase += 0.028
        center_x = get_screen_width() // 2 + int(math.sin(boss.phase) * 170)
        boss.rect.centerx = center_x
        boss.enraged = boss.health <= boss.max_health * self.BOSS_ENRAGE_THRESHOLD
        boss.fire_timer -= 1
        fire_interval = 22 if boss.enraged else 62
        if boss.fire_timer <= 0:
            boss.fire_timer = fire_interval
            spread = (-0.42, -0.20, 0.0, 0.20, 0.42) if boss.enraged else (-0.16, 0.16)
            for offset in spread:
                direction = pygame.Vector2(offset, 1).normalize()
                self._enemy_bullets.append(
                    TutorialBullet(
                        rect=pygame.Rect(boss.rect.centerx - 6, boss.rect.bottom - 4, 12, 16),
                        velocity=direction * (6.2 if boss.enraged else 4.4),
                        owner="enemy",
                        damage=9 if boss.enraged else 6,
                        bullet_type="laser" if boss.enraged else "single",
                    )
                )

    def _spawn_enemy_bullet(self, center: tuple[int, int], *, damage: int) -> None:
        direction = pygame.Vector2(
            self._player.centerx - center[0],
            self._player.centery - center[1],
        )
        direction = pygame.Vector2(0, 1) if direction.length_squared() <= 1 else direction.normalize()
        rect = pygame.Rect(0, 0, 10, 14)
        rect.center = center
        self._enemy_bullets.append(
            TutorialBullet(
                rect=rect,
                velocity=direction * 4.2,
                owner="enemy",
                damage=damage,
            )
        )

    def _handle_collisions(self) -> None:
        for bullet in self._bullets:
            if not bullet.active:
                continue
            for enemy in self._enemies:
                if not enemy.active or not bullet.rect.colliderect(enemy.rect):
                    continue
                bullet.active = False
                enemy.health -= bullet.damage
                if enemy.health <= 0:
                    enemy.active = False
                    self._score += enemy.score_value
                    self._kills += 1
                    self._stage_progress = min(self._stage.objective_count, self._stage_progress + 1)
                break

            boss = self._boss
            if bullet.active and boss is not None and boss.active and bullet.rect.colliderect(boss.rect):
                bullet.active = False
                boss.health -= bullet.damage
                if boss.health <= 0:
                    boss.active = False
                    self._score += 500
                    self._kills += 1
                    self._boss = None
                    self._escape_timer = self.ESCAPE_FRAMES

        vulnerable = self._stage.id in ("combat_basics", "boss_encounter")
        if not vulnerable:
            return

        for bullet in self._enemy_bullets:
            if not bullet.active or not bullet.rect.colliderect(self._player):
                continue
            bullet.active = False
            self._damage_player(bullet.damage)

        for enemy in self._enemies:
            if enemy.active and enemy.rect.colliderect(self._player):
                self._damage_player(8)

    def _damage_player(self, damage: int) -> None:
        if self._player_hit_cooldown > 0:
            return
        self._player_hit_cooldown = self.PLAYER_HIT_COOLDOWN
        self._player_health = max(20, self._player_health - damage)

    def _cleanup_entities(self) -> None:
        self._bullets[:] = [bullet for bullet in self._bullets if bullet.active]
        self._enemy_bullets[:] = [bullet for bullet in self._enemy_bullets if bullet.active]
        self._enemies[:] = [enemy for enemy in self._enemies if enemy.active]

    # -- Rendering ------------------------------------------------------

    def _render_background(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_width(), surface.get_height()
        if self._game_renderer is None:
            self._game_renderer = GameRenderer(use_integrated_hud=False)
            self._game_renderer.init_background(sw, sh)
            self._background_size = (sw, sh)

        if self._background_size != (sw, sh):
            self._game_renderer.init_background(sw, sh)
            self._background_size = (sw, sh)

        background = self._game_renderer.background_renderer
        if background:
            background.update()
            background.draw(surface)
        else:
            surface.fill(SceneColors.BG_PRIMARY)

    def _render_world(self, surface: pygame.Surface) -> None:
        self._render_stage_props(surface)

        if self._stage.id != "homecoming_base":
            for bullet in self._bullets:
                draw_bullet(surface, bullet.rect.x, bullet.rect.y, bullet.rect.width, bullet.rect.height, "single", "player")
            for bullet in self._enemy_bullets:
                draw_bullet(surface, bullet.rect.x, bullet.rect.y, bullet.rect.width, bullet.rect.height, bullet.bullet_type, "enemy")

            for enemy in self._enemies:
                health_ratio = max(0.0, enemy.health / enemy.max_health)
                draw_enemy_ship(surface, enemy.rect.centerx, enemy.rect.centery, enemy.rect.width, enemy.rect.height, health_ratio)
                self._draw_entity_health_bar(surface, enemy.rect, health_ratio)

            if self._boss is not None:
                boss = self._boss
                health_ratio = max(0.0, boss.health / boss.max_health)
                if boss.enraged:
                    self._render_boss_enrage_aura(surface, boss)
                draw_boss_ship(surface, boss.rect.centerx, boss.rect.centery, boss.rect.width, boss.rect.height, health_ratio)
                self._draw_boss_health(surface, boss)
                if boss.enraged:
                    self._render_boss_enrage_warning(surface, boss)

            self._aim_crosshair.render(surface, self._aim_pos)
            self._render_player(surface)

    def _render_stage_props(self, surface: pygame.Surface) -> None:
        if self._stage.id == "mothership_docking":
            self._render_mothership_components(surface)
        elif self._stage.id == "boost_phase_dash":
            self._render_boost_gate(surface)
        elif self._stage.id == "boss_encounter" and self._boss is None and self._escape_timer > 0:
            self._render_escape_countdown(surface)

    def _render_player(self, surface: pygame.Surface) -> None:
        if self._player_hit_cooldown > 0 and (self._animation_time // 4) % 2 == 0:
            return
        if self._dash_frames > 0:
            dash_glow = pygame.Surface((96, 96), pygame.SRCALPHA)
            pygame.draw.circle(dash_glow, (*SceneColors.ACCENT_TEAL_BRIGHT, 55), (48, 48), 42)
            surface.blit(dash_glow, dash_glow.get_rect(center=self._player.center))
        draw_player_ship(surface, self._player.centerx, self._player.centery, self.PLAYER_W, self.PLAYER_H)

    def _render_stage_overlay(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_width(), surface.get_height()
        skip_reserved_w = 210 if sw >= 760 else 0
        panel_w = min(sw - 48 - skip_reserved_w, 1040)
        panel_w = max(380, panel_w)
        x = 24 if skip_reserved_w else (sw - panel_w) // 2
        y = 20
        badge_size = 62
        right_badge_w = 154
        content_left = x + 96
        content_right = x + panel_w - right_badge_w - 26
        max_text_w = max(230, content_right - content_left)

        instruction_lines: list[str] = []
        for line in self._stage.instructions:
            instruction_lines.extend(wrap_text(line, self._small_font, max_text_w, max_lines=2))
        instruction_lines = instruction_lines[:4]
        panel_h = min(sh - 156, 120 + len(instruction_lines) * 24)
        panel_h = max(184, panel_h)

        transition_pulse = 1.0 if self._stage_card_timer > self.STAGE_CARD_FADE_FRAMES else 0.0
        border_alpha = 150 + int(55 * math.sin(self._animation_time * 0.08))
        glow_alpha = 42 + int(48 * transition_pulse)
        draw_chamfered_panel(
            surface,
            x - 3,
            y - 3,
            panel_w + 6,
            panel_h + 6,
            SceneColors.BG_PANEL,
            (*SceneColors.ACCENT_TEAL_BRIGHT, min(235, border_alpha + int(40 * transition_pulse))),
            (*SceneColors.ACCENT_TEAL_BRIGHT, glow_alpha),
            14,
        )
        draw_chamfered_panel(
            surface,
            x,
            y,
            panel_w,
            panel_h,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.BORDER_DIM, 210),
            None,
            12,
        )

        panel_tint = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_tint.fill((0, 0, 0, 28))
        pygame.draw.line(panel_tint, (*SceneColors.ACCENT_TEAL_BRIGHT, 80), (24, panel_h - 36), (panel_w - 24, panel_h - 36), 1)
        surface.blit(panel_tint, (x, y))

        badge_rect = pygame.Rect(0, 0, badge_size, badge_size)
        badge_rect.center = (x + 42, y + 48)
        badge_layer = pygame.Surface((badge_size + 14, badge_size + 14), pygame.SRCALPHA)
        pygame.draw.circle(
            badge_layer,
            (*SceneColors.ACCENT_TEAL_BRIGHT, 34 + int(24 * math.sin(self._animation_time * 0.07))),
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2 + 6,
        )
        pygame.draw.circle(
            badge_layer,
            (*SceneColors.BG_PANEL, 240),
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2,
        )
        pygame.draw.circle(
            badge_layer,
            SceneColors.ACCENT_TEAL_BRIGHT,
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2,
            2,
        )
        surface.blit(badge_layer, badge_layer.get_rect(center=badge_rect.center))

        badge_top = self._tiny_font.render("阶段", True, SceneColors.TEXT_DIM)
        badge_num = self._body_font.render(str(self._stage_index + 1), True, SceneColors.TEXT_BRIGHT)
        surface.blit(badge_top, badge_top.get_rect(center=(badge_rect.centerx, badge_rect.centery - 12)))
        surface.blit(badge_num, badge_num.get_rect(center=(badge_rect.centerx, badge_rect.centery + 12)))

        title = self._heading_font.render(self._stage.title, True, SceneColors.ACCENT_TEAL_BRIGHT)
        surface.blit(title, title.get_rect(midleft=(content_left, y + 32)))

        objective = f"目标: {self._stage.objective}"
        obj_surf = fit_text_to_width(self._small_font, objective, SceneColors.ACCENT_PRIMARY, max_text_w)
        surface.blit(obj_surf, obj_surf.get_rect(midleft=(content_left, y + 66)))

        line_y = y + 92
        for wrapped in instruction_lines:
            text = self._small_font.render(wrapped, True, SceneColors.TEXT_PRIMARY)
            surface.blit(text, (content_left, line_y))
            line_y += 24

        counter_rect = pygame.Rect(x + panel_w - right_badge_w - 20, y + 28, right_badge_w, 48)
        draw_chamfered_panel(
            surface,
            counter_rect.x,
            counter_rect.y,
            counter_rect.width,
            counter_rect.height,
            SceneColors.BG_PANEL,
            (*SceneColors.ACCENT_PRIMARY, 220),
            (*SceneColors.ACCENT_TEAL_BRIGHT, 38),
            8,
        )
        counter_label = self._tiny_font.render("进度", True, SceneColors.TEXT_DIM)
        counter = self._objective_counter_text()
        counter_surf = fit_text_to_width(self._body_font, counter, SceneColors.TEXT_BRIGHT, counter_rect.width - 20)
        surface.blit(counter_label, counter_label.get_rect(midtop=(counter_rect.centerx, counter_rect.y + 5)))
        surface.blit(counter_surf, counter_surf.get_rect(midbottom=(counter_rect.centerx, counter_rect.bottom - 4)))

        hold_ratio = self._stage_hold_ratio()
        if hold_ratio is not None:
            bar = pygame.Rect(x + 96, y + panel_h - 24, panel_w - 192, 10)
            self._draw_bar(surface, bar, hold_ratio, SceneColors.ACCENT_TEAL_BRIGHT)

    def _objective_counter_text(self) -> str:
        if self._stage.id == "mothership_docking" and not self._docked:
            return f"{int(self._hold_h_frames / self.DOCK_HOLD_FRAMES * 100)}%"
        if self._stage.id == "homecoming_base" and not self._base_ready:
            return f"{int(self._hold_b_frames / self.HOME_HOLD_FRAMES * 100)}%"
        if self._stage.id == "boss_encounter" and self._boss is None and self._escape_timer > 0:
            seconds = max(0, math.ceil(self._escape_timer / 60))
            return f"撤离 {seconds}s"
        if self._stage_completed:
            return "完成"
        return f"{self._stage_progress}/{self._stage.objective_count}"

    def _stage_hold_ratio(self) -> float | None:
        if self._stage.id == "mothership_docking" and not self._docked:
            return self._hold_h_frames / self.DOCK_HOLD_FRAMES
        if self._stage.id == "homecoming_base" and not self._base_ready:
            return self._hold_b_frames / self.HOME_HOLD_FRAMES
        return None

    def _render_status_bar(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_width(), surface.get_height()
        self._boost_gauge.render(
            surface,
            self._player_energy,
            self.ENERGY_MAX,
            self._boost_held(),
            {"dash_enabled": True, "dash_cooldown": 0},
        )
        self._render_health_battery(surface)

        panel_w = min(460, sw - 44)
        panel_h = 54
        panel = pygame.Rect((sw - panel_w) // 2, sh - panel_h - 24, panel_w, panel_h)
        draw_chamfered_panel(
            surface,
            panel.x - 3,
            panel.y - 3,
            panel.width + 6,
            panel.height + 6,
            SceneColors.BG_PANEL,
            (*SceneColors.BORDER_DIM, 190),
            (*SceneColors.ACCENT_TEAL_BRIGHT, 38),
            10,
        )
        draw_chamfered_panel(
            surface,
            panel.x,
            panel.y,
            panel.width,
            panel.height,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.ACCENT_PRIMARY, 190),
            None,
            8,
        )

        score_text = self._small_font.render(f"得分 {self._score:04d}", True, SceneColors.TEXT_PRIMARY)
        kills_text = self._small_font.render(f"击杀 {self._kills}", True, SceneColors.ACCENT_PRIMARY)
        metric_gap = 58
        total_w = score_text.get_width() + metric_gap + kills_text.get_width()
        start_x = panel.centerx - total_w // 2
        surface.blit(score_text, score_text.get_rect(midleft=(start_x, panel.centery)))
        surface.blit(kills_text, kills_text.get_rect(midleft=(start_x + score_text.get_width() + metric_gap, panel.centery)))

    def _render_health_battery(self, surface: pygame.Surface) -> None:
        battery_x = 24
        battery_y = max(136, surface.get_height() - self._battery_indicator._h - 214)
        self._battery_indicator.set_health(self._player_health, self._player_max_health)
        self._battery_indicator.render(surface, battery_x, battery_y)
        border = pygame.Rect(
            battery_x,
            battery_y,
            self._battery_indicator._w,
            self._battery_indicator._h,
        )
        pygame.draw.rect(surface, (*SceneColors.BORDER_DIM, 140), border, 1, border_radius=4)

    def _draw_bar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
        fill_color: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, SceneColors.SEGMENT_EMPTY, rect, border_radius=3)
        fill = rect.copy()
        fill.width = int(rect.width * ratio)
        if fill.width > 0:
            pygame.draw.rect(surface, fill_color, fill, border_radius=3)
        pygame.draw.rect(surface, SceneColors.SEGMENT_BORDER, rect, 1, border_radius=3)

    def _draw_entity_health_bar(self, surface: pygame.Surface, rect: pygame.Rect, ratio: float) -> None:
        bar = pygame.Rect(rect.x, rect.y - 13, rect.width, 5)
        pygame.draw.rect(surface, SceneColors.BOSS_BAR_EMPTY, bar)
        fill = bar.copy()
        fill.width = int(bar.width * ratio)
        pygame.draw.rect(surface, SceneColors.HEALTH_LOW, fill)

    def _draw_boss_health(self, surface: pygame.Surface, boss: TutorialBoss) -> None:
        sw = surface.get_width()
        bar = pygame.Rect(sw // 2 - 230, 196, 460, 16)
        ratio = max(0.0, boss.health / boss.max_health)
        pygame.draw.rect(surface, SceneColors.BOSS_BAR_EMPTY, bar, border_radius=4)
        color = SceneColors.DANGER_RED if boss.enraged else SceneColors.BOSS_BAR_FULL
        fill = bar.copy()
        fill.width = int(bar.width * ratio)
        pygame.draw.rect(surface, color, fill, border_radius=4)
        pygame.draw.rect(surface, SceneColors.BORDER_DIM, bar, 1, border_radius=4)
        label = "首领装甲  激怒" if boss.enraged else "首领装甲"
        text = self._small_font.render(label, True, color)
        surface.blit(text, text.get_rect(midbottom=(bar.centerx, bar.y - 3)))

    def _render_boss_enrage_aura(self, surface: pygame.Surface, boss: TutorialBoss) -> None:
        pulse = 0.5 + 0.5 * math.sin(self._animation_time * 0.16)
        aura_size = (
            int(boss.rect.width * (1.22 + 0.08 * pulse)),
            int(boss.rect.height * (1.20 + 0.08 * pulse)),
        )
        aura = pygame.Surface(aura_size, pygame.SRCALPHA)
        rect = aura.get_rect()
        pygame.draw.ellipse(aura, (*SceneColors.ACCENT_TEAL_BRIGHT, int(58 + 52 * pulse)), rect, 4)
        inner = rect.inflate(-max(8, aura_size[0] // 5), -max(8, aura_size[1] // 5))
        pygame.draw.ellipse(aura, (*SceneColors.DANGER_RED, int(42 + 38 * pulse)), inner, 2)
        surface.blit(aura, aura.get_rect(center=boss.rect.center), special_flags=pygame.BLEND_RGBA_ADD)

    def _render_boss_enrage_warning(self, surface: pygame.Surface, boss: TutorialBoss) -> None:
        pulse = 0.55 + 0.45 * math.sin(self._animation_time * 0.13)
        text = self._heading_font.render("核心过载", True, SceneColors.ACCENT_TEAL_BRIGHT)
        text.set_alpha(int(150 + 80 * pulse))
        surface.blit(text, text.get_rect(center=(boss.rect.centerx, boss.rect.y - 34)))

    def _render_mothership_components(self, surface: pygame.Surface) -> None:
        if self._mothership:
            self._mothership.show()
            self._mothership.render(surface)
        if self._docked and self._ammo_magazine:
            is_warning = self._mothership_ammo < self.WARNING_CELL_THRESHOLD
            self._ammo_magazine.render(
                surface,
                ammo_count=self._mothership_ammo,
                ammo_max=10.0,
                is_cooldown=False,
                is_docked=True,
                is_warning=is_warning,
                is_present=True,
            )
        if self._warning_banner:
            self._warning_banner.render(surface)

    def _render_base_talent_console(self, surface: pygame.Surface) -> None:
        if not (
            self._base_talent_console
            and self._talent_balance_manager
            and self._base_reward_system
            and self._base_player_status
            and self._base_game_controller
        ):
            return
        self._base_talent_console.render(
            surface,
            self._talent_balance_manager,
            self._base_reward_system,
            player=self._base_player_status,
            game_controller=self._base_game_controller,
            mothership_status=self._mothership_status_data(),
            requisition_points=self._base_game_controller.state.requisition_points,
            missions=self._tutorial_missions(),
        )

    def _mothership_status_data(self) -> dict:
        ammo_count = max(0.0, min(10.0, float(self._mothership_ammo)))
        return {
            "ammo_count": ammo_count,
            "ammo_max": 10.0,
            "is_in_cooldown": False,
            "is_docked": self._docked,
            "ammo_warning": ammo_count < self.WARNING_CELL_THRESHOLD,
            "is_present": self._stage.id == "mothership_docking",
            "cooldown_remaining": 0.0,
            "cooldown_reduction": 0.5,
        }

    def _tutorial_missions(self) -> list[dict]:
        return [
            {
                "name": "歼灭先锋",
                "desc": "击杀5个敌人",
                "target": "kills",
                "goal": 5,
                "progress": min(self._kills, 5),
                "done": self._kills >= 5,
                "claimed": False,
            },
            {
                "name": "支援链路",
                "desc": "完成一次母舰停靠",
                "target": "mothership",
                "goal": 1,
                "progress": 1,
                "done": True,
                "claimed": False,
            },
            {
                "name": "返航整备",
                "desc": "进入基地控制台",
                "target": "homecoming",
                "goal": 1,
                "progress": 1 if self._base_ready else 0,
                "done": self._base_ready,
                "claimed": False,
            },
        ]

    def _render_boost_gate(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_width(), surface.get_height()
        gate_rect = pygame.Rect(sw // 2 - 170, sh // 2 - 80, 340, 160)
        gate_layer = pygame.Surface(gate_rect.size, pygame.SRCALPHA)
        pulse = 70 + int(35 * math.sin(self._animation_time * 0.08))
        pygame.draw.ellipse(gate_layer, (*SceneColors.ACCENT_TEAL_BRIGHT, pulse), gate_layer.get_rect(), 4)
        pygame.draw.ellipse(gate_layer, (*SceneColors.ACCENT_PRIMARY, 45), gate_layer.get_rect().inflate(-70, -52), 2)
        surface.blit(gate_layer, gate_rect)
        if self._boost_feedback_timer > 0:
            text = self._heading_font.render("相位突进", True, SceneColors.ACCENT_TEAL_BRIGHT)
            surface.blit(text, text.get_rect(center=(gate_rect.centerx, gate_rect.centery)))

    def _render_escape_countdown(self, surface: pygame.Surface) -> None:
        seconds = max(0, math.ceil(self._escape_timer / 60))
        text = self._title_font.render(f"撤离窗口 {seconds}", True, SceneColors.WARNING_ACCENT)
        surface.blit(text, text.get_rect(center=(surface.get_width() // 2, 250)))

    def _render_skip_button(self, surface: pygame.Surface) -> None:
        if not self.running:
            return
        sw = surface.get_width()
        if self._is_summary_stage():
            return
        rect = pygame.Rect(sw - 190, 24, 164, 42)
        self.register_button("skip_tutorial", rect)
        hover = self.is_button_hovered("skip_tutorial")
        fill = SceneColors.BG_PANEL_LIGHT if hover else SceneColors.BG_PANEL
        border = SceneColors.ACCENT_PRIMARY if hover else SceneColors.BORDER_DIM
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, fill, border, None, 6)
        text = self._small_font.render("跳过教程", True, SceneColors.TEXT_PRIMARY if hover else SceneColors.TEXT_DIM)
        surface.blit(text, text.get_rect(center=rect.center))

    def _render_summary(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_width(), surface.get_height()
        panel_w = min(720, sw - 80)
        panel_h = min(560, sh - 90)
        panel = pygame.Rect((sw - panel_w) // 2, (sh - panel_h) // 2, panel_w, panel_h)
        draw_chamfered_panel(surface, panel.x, panel.y, panel.width, panel.height,
                             SceneColors.BG_PANEL_LIGHT, SceneColors.ACCENT_PRIMARY, SceneColors.GOLD_GLOW, 12)

        title = self._title_font.render("教程完成", True, SceneColors.ACCENT_TEAL_BRIGHT)
        surface.blit(title, title.get_rect(center=(panel.centerx, panel.y + 54)))

        summary = self._body_font.render(
            f"已完成 {len(self._cleared_stage_ids)}/{len(TUTORIAL_STAGES)} 个训练阶段",
            True,
            SceneColors.TEXT_PRIMARY,
        )
        surface.blit(summary, summary.get_rect(center=(panel.centerx, panel.y + 98)))

        y = panel.y + 142
        for index, stage in enumerate(TUTORIAL_STAGES, start=1):
            mark_color = SceneColors.ACCENT_TEAL_BRIGHT if stage.id in self._cleared_stage_ids else SceneColors.TEXT_DIM
            label = f"{index}. {stage.title}"
            text = self._small_font.render(label, True, mark_color)
            surface.blit(text, (panel.x + 72, y))
            y += 36

        wrap_y = y + 10
        for line in wrap_text("进入正式战斗后，优先保持移动，适时使用加速、母舰停靠和基地返航。", self._small_font, panel.width - 112, max_lines=3):
            surface.blit(self._small_font.render(line, True, SceneColors.TEXT_DIM), (panel.x + 56, wrap_y))
            wrap_y += 26

        btn = pygame.Rect(panel.centerx - 120, panel.bottom - 74, 240, 48)
        self.register_button("return_menu", btn)
        hover = self.is_button_hovered("return_menu")
        draw_chamfered_panel(surface, btn.x, btn.y, btn.width, btn.height,
                             SceneColors.ACCENT_TEAL if hover else SceneColors.ACCENT_TEAL_DIM,
                             SceneColors.ACCENT_PRIMARY, None, 6)
        btn_text = self._body_font.render("返回主菜单", True, SceneColors.TEXT_BRIGHT)
        surface.blit(btn_text, btn_text.get_rect(center=btn.center))

    def _render_fade(self, surface: pygame.Surface) -> None:
        if self._fade_alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self._fade_alpha))
        surface.blit(overlay, (0, 0))

    def _render_stage_title_card(self, surface: pygame.Surface) -> None:
        if self._stage_card_timer <= 0 or self._is_summary_stage():
            return

        total = self.STAGE_CARD_SLIDE_FRAMES + self.STAGE_CARD_HOLD_FRAMES + self.STAGE_CARD_FADE_FRAMES
        elapsed = total - self._stage_card_timer
        sw = surface.get_width()
        card_w = min(620, sw - 80)
        card_h = 116
        target_y = 106

        if elapsed < self.STAGE_CARD_SLIDE_FRAMES:
            t = elapsed / max(1, self.STAGE_CARD_SLIDE_FRAMES)
            eased = 1 - (1 - t) * (1 - t)
            y = int(-card_h + eased * (target_y + card_h))
            alpha = int(255 * t)
        else:
            y = target_y
            alpha = 255

        fade_start = self.STAGE_CARD_SLIDE_FRAMES + self.STAGE_CARD_HOLD_FRAMES
        if elapsed > fade_start:
            t = (elapsed - fade_start) / max(1, self.STAGE_CARD_FADE_FRAMES)
            alpha = int(255 * max(0.0, 1.0 - t))

        x = (sw - card_w) // 2
        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self._animation_time * 0.1)
        draw_chamfered_panel(
            card,
            4,
            4,
            card_w - 8,
            card_h - 8,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.ACCENT_TEAL_BRIGHT, 235),
            (*SceneColors.ACCENT_TEAL_BRIGHT, int(alpha * (0.16 + 0.10 * pulse))),
            14,
        )

        stage_text = self._body_font.render(f"第{self._stage_index + 1}阶段", True, SceneColors.ACCENT_PRIMARY)
        title_text = fit_text_to_width(self._heading_font, self._stage.title, SceneColors.TEXT_BRIGHT, card_w - 96)
        card.blit(stage_text, stage_text.get_rect(center=(card_w // 2, 34)))
        card.blit(title_text, title_text.get_rect(center=(card_w // 2, 76)))

        card.set_alpha(alpha)
        surface.blit(card, (x, y))
