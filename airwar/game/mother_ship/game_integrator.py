"""Game integrator — bridges mothership state with game systems.

F08 god-class split: animation state machines live in
``mothership_animations.py`` and gatling turret logic in
``mothership_gatling.py``. This class keeps the state bridge, save/load,
status data, ammo magazine, warning trigger, and the public API as
1-line forwarders to the extracted components.
"""

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config import get_screen_height, get_screen_width
from airwar.entities.base import BulletData
from airwar.entities.bullet import Bullet
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.frame_context import FrameContext

from ..rendering.entity_renderer import EntityRenderer
from ..systems.lock_manager import LockLayer, LockRequest
from .mother_ship_state import GameSaveData, MotherShipState
from .mothership_animations import MothershipAnimations
from .mothership_gatling import MothershipGatling
from .progress_bar_ui import ProgressBarUI

if TYPE_CHECKING:
    from .event_bus import EventBus
    from .input_detector import InputDetector
    from .mother_ship import MotherShip
    from .state_machine import MotherShipStateMachine


__all__ = ["GameIntegrator"]


class GameIntegrator:
    """Game integrator — bridges mothership state with game systems.

    Coordinates between game state and mothership docking flow,
    updating entity states and UI during the docking process.

    F08 split:
    - Animation state machines live in :class:`MothershipAnimations`.
    - Gatling turret logic lives in :class:`MothershipGatling`.
    This class keeps the orchestration, save/load, and the public API
    (1-line forwarders for animation and gatling methods).
    """

    # Bullet / explosion damage constants (unchanged)
    MOTHERSHIP_BULLET_DAMAGE = 250
    MOTHERSHIP_FIRE_RATE = 18  # ~3.3 shots/sec at 60fps — heavy missile cadence
    MOTHERSHIP_BULLET_SPEED = 10
    MOTHERSHIP_TARGET_COUNT = 5  # fire at up to 5 closest enemies per volley
    MOTHERSHIP_EXPLOSION_RADIUS = 80
    MOTHERSHIP_EXPLOSION_DAMAGE = 60

    MOTHERSHIP_BULLET_DESPAWN_MARGIN = 80
    MOTHERSHIP_MAX_BULLETS = 20
    AMMO_CELL_COUNT = 10.0
    # F04 M2: link to GAME_CONSTANTS (was bare 1200)
    DOCKING_INVINCIBILITY_FRAMES = GAME_CONSTANTS.PERSISTENCE.DOCKING_INVINCIBILITY_FRAMES

    BAR_TYPE_HOLD = "hold"
    BAR_TYPE_COOLDOWN = "cooldown"
    BAR_TYPE_STAY = "stay"
    BAR_TYPE_EXIT = "exit"

    def __init__(
        self,
        event_bus: "EventBus",
        input_detector: "InputDetector",
        state_machine: "MotherShipStateMachine",
        progress_bar_ui: "ProgressBarUI",
        mother_ship: "MotherShip",
    ):
        self._event_bus = event_bus
        self._input_detector = input_detector
        self._state_machine = state_machine
        self._progress_bar_ui = progress_bar_ui
        self._mother_ship = mother_ship

        self._animations = MothershipAnimations(self)
        self._gatling = MothershipGatling(self)

        self._undocking_cooldown_multiplier = 1.0

        self._game_scene = None
        self._player_control_disabled = False

        self._mothership_bullets: list[Bullet] = []
        self._entity_renderer = EntityRenderer()
        self._mothership_fire_elapsed = 0.0
        self._current_time = 0.0
        self._exit_refund_progress: float = 0.0  # Ammo refund on early exit (0.0-0.3)
        self._score_reduction_factor = 1.0 / 3.0
        # Cached once per frame in update(): True while the boss enrage
        # grab (transition or active dash) is running. The mothership
        # then holds position and ceases fire. Caching avoids querying
        # the boss state machine from several call sites per frame.
        self._boss_enrage_engaged = False

    def _update_entering_animation(self) -> None:
        self._animations.tick_entering()

    def _update_docking_animation(self) -> None:
        self._animations.tick_docking()

    def _update_undocking_animation(self) -> None:
        self._animations.tick_undocking()

    def _update_mothership_gatling(self) -> None:
        self._gatling.tick()

    # ── Event handler that triggers the entering animation ────────────────
    def _on_start_entering_animation(self, **kwargs) -> None:
        self._animations.start_entering()

    def _on_start_docking_animation(self, **kwargs) -> None:
        self._animations.start_docking()

    def _on_start_undocking_animation(self, **kwargs) -> None:
        self._animations.start_undocking()

    def attach_game_scene(self, game_scene) -> None:
        self._game_scene = game_scene
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register mothership event handlers."""
        from .event_hub import MothershipEventHub

        MothershipEventHub(self).register_all()

    def detach_game_scene(self) -> None:
        """Detach the integrator from the current game scene.

        Unregisters all mothership event handlers and clears the
        game scene reference so the integrator can be safely discarded.
        """
        from .event_hub import MothershipEventHub

        MothershipEventHub(self).unregister_all()
        self._state_machine._unregister_handlers()
        self._game_scene = None

    def _sync_boss_enrage_cache(self) -> None:
        """Refresh the cached boss-enrage flag (once per frame).

        Consumed by ``_update_mothership_input`` and the firing guard
        in ``update`` so neither re-queries the boss state machine.
        """
        boss = self._game_scene.get_boss() if self._game_scene else None
        if boss is None or not getattr(boss, "active", False):
            self._boss_enrage_engaged = False
            return
        is_engaged = getattr(boss, "is_enrage_engaged", lambda: False)
        self._boss_enrage_engaged = bool(is_engaged())

    def _update_mothership_input(self) -> None:
        # Mothership movement is only allowed while docked, and is
        # frozen while the boss enrage grab is running (position lock).
        if self._boss_enrage_engaged or not self._mother_ship.is_visible() or not self._state_machine.is_docked():
            self._mother_ship.set_player_input(0, 0)
            return

        keys = pygame.key.get_pressed()
        x_input = 0
        y_input = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            x_input = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            x_input = 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            y_input = -1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            y_input = 1

        self._mother_ship.set_player_input(x_input, y_input)

    def update(self, delta_seconds: float, elapsed_seconds: float) -> None:
        if self._game_scene is None:
            return
        self._current_time = elapsed_seconds
        self._sync_boss_enrage_cache()
        self._update_mothership_input()

        # Run animations without blocking the game loop
        if self._animations._entering_animation_active:
            self._update_entering_animation()

        if self._animations._docking_animation_active:
            self._update_docking_animation()

        if self._animations._undocking_animation_active:
            self._update_undocking_animation()

        # Always update input detector and state machine so the
        # game loop continues running during animations
        self._state_machine.set_current_time(elapsed_seconds)
        self._input_detector.update(elapsed_seconds)
        self._state_machine.update(elapsed_seconds)
        self._mother_ship.update()

        if self._state_machine.is_docked():
            # Cease fire while the boss enrage grab runs: the docked
            # player is invincible, so firing would only pretend to
            # threaten the boss without consequence. In-flight bullets
            # keep flying and the player stays bound to the dock.
            if not self._boss_enrage_engaged:
                self._update_mothership_firing(delta_seconds)
            self._update_mothership_bullets()
            dock_pos = self._mother_ship.get_docking_position()
            self._game_scene.set_player_position(dock_pos[0], dock_pos[1])
        elif self._state_machine.is_entering():
            self._update_mothership_bullets()

    def _update_mothership_firing(self, delta_seconds: float) -> None:
        if not self._game_scene or not self._game_scene.spawn_controller:
            return

        self._mothership_fire_elapsed += delta_seconds
        fire_interval = self.MOTHERSHIP_FIRE_RATE * FrameContext.FIXED_DELTA_SECONDS
        if self._mothership_fire_elapsed >= fire_interval:
            self._mothership_fire_elapsed -= fire_interval
            self._fire_at_enemies()
        self._update_mothership_gatling()

    def _fire_at_enemies(self) -> None:
        if not self._game_scene:
            return
        if len(self._mothership_bullets) >= self.MOTHERSHIP_MAX_BULLETS:
            return

        mother_ship_pos = self._mother_ship.get_docking_position()
        targets = self._get_mothership_targets()
        if not targets:
            return

        # Sort by distance and target the N closest
        active_enemies = [
            (math.sqrt((e.rect.centerx - mother_ship_pos[0]) ** 2 + (e.rect.centery - mother_ship_pos[1]) ** 2), e)
            for e in targets
        ]
        active_enemies.sort(key=lambda x: x[0])

        for dist, target in active_enemies[: self.MOTHERSHIP_TARGET_COUNT]:
            if dist > 0:
                vx = (target.rect.centerx - mother_ship_pos[0]) / dist * self.MOTHERSHIP_BULLET_SPEED
                vy = (target.rect.centery - mother_ship_pos[1]) / dist * self.MOTHERSHIP_BULLET_SPEED

                bullet = Bullet(
                    mother_ship_pos[0],
                    mother_ship_pos[1],
                    BulletData(
                        damage=self.MOTHERSHIP_BULLET_DAMAGE,
                        speed=self.MOTHERSHIP_BULLET_SPEED,
                        owner="mothership",
                        bullet_type="explosive_missile",
                        is_explosive=True,
                    ),
                )
                bullet.velocity.x = vx
                bullet.velocity.y = vy
                self._mothership_bullets.append(bullet)

    def _get_mothership_targets(self) -> list:
        if not self._game_scene:
            return []

        targets = list(self._game_scene.get_enemies())
        boss = self._game_scene.get_boss()
        if boss:
            targets.append(boss)
        return [target for target in targets if getattr(target, "active", False)]

    def _update_mothership_bullets(self) -> None:
        if not self._game_scene:
            return

        enemies = self._game_scene.get_enemies()
        boss = self._game_scene.get_boss()
        screen_width = get_screen_width()
        screen_height = get_screen_height()
        margin = self.MOTHERSHIP_BULLET_DESPAWN_MARGIN

        for bullet in self._mothership_bullets[:]:
            bullet.update()

            if not bullet.active:
                continue

            # Skip collision for off-screen bullets — early despawn avoids
            # the O(bullets × enemies) colliderect loop for distant bullets.
            bx, by = bullet.rect.centerx, bullet.rect.centery
            if bx < -margin or bx > screen_width + margin or by < -margin or by > screen_height + margin:
                bullet.active = False
                continue

            bullet_damage = bullet.data.damage
            hit = False
            hit_x, hit_y = bx, by

            for enemy in enemies:
                if not enemy.active:
                    continue
                if bullet.rect.colliderect(self._entity_collision_rect(enemy)):
                    enemy.take_damage(bullet_damage)
                    if not enemy.active:
                        self._on_mothership_kill_enemy(enemy)
                    hit = True
                    break

            if not hit and boss and boss.active and bullet.rect.colliderect(self._entity_collision_rect(boss)):
                boss.take_damage(bullet_damage)
                if not boss.active:
                    self._on_mothership_kill_boss(boss)
                hit = True

            if hit:
                bullet.active = False
                if bullet.data.is_explosive:
                    self._trigger_explosion(hit_x, hit_y)
                    self._apply_missile_splash(hit_x, hit_y, enemies, boss)

        self._mothership_bullets = [b for b in self._mothership_bullets if b.active]

    def _entity_collision_rect(self, entity):
        if hasattr(entity, "get_hitbox"):
            return entity.get_hitbox()
        return entity.rect

    def _trigger_explosion(self, x: float, y: float) -> None:
        """Trigger explosion visual effect at position."""
        if self._game_scene and hasattr(self._game_scene, "trigger_explosion"):
            self._game_scene.trigger_explosion(x, y, self.MOTHERSHIP_EXPLOSION_RADIUS)

    def _apply_missile_splash(self, x: float, y: float, enemies, boss) -> None:
        """Apply AoE damage to enemies within explosion radius."""
        radius_sq = self.MOTHERSHIP_EXPLOSION_RADIUS**2
        explosion_damage = self.MOTHERSHIP_EXPLOSION_DAMAGE

        for enemy in enemies:
            if not enemy.active:
                continue
            dx = x - enemy.rect.centerx
            dy = y - enemy.rect.centery
            if dx * dx + dy * dy <= radius_sq:
                enemy.take_damage(explosion_damage)
                if not enemy.active and self._game_scene:
                    self._game_scene.add_score(self._get_entity_score(enemy, 100) // 3)
                    self._game_scene.add_kill()

        if boss and boss.active:
            dx = x - boss.rect.centerx
            dy = y - boss.rect.centery
            if dx * dx + dy * dy <= radius_sq:
                boss.take_damage(explosion_damage)
                if not boss.active:
                    self._on_mothership_kill_boss(boss)

    def _on_mothership_kill_enemy(self, enemy) -> None:
        if not self._game_scene:
            return

        base_score = getattr(enemy, "score", 100)
        base_score = self._get_entity_score(enemy, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        self._game_scene.add_score(reduced_score)
        self._game_scene.add_kill()
        self._game_scene.show_notification(f"+{reduced_score} (mothership)")

    def _on_mothership_kill_boss(self, boss) -> None:
        if not self._game_scene:
            return

        base_score = getattr(boss, "score", 1000)
        base_score = self._get_entity_score(boss, base_score)
        reduced_score = int(base_score * self._score_reduction_factor)

        # Route through GameController for RP award and difficulty scaling
        gc = getattr(self._game_scene, "game_controller", None)
        if gc:
            gc.on_boss_killed(reduced_score)
        else:
            self._game_scene.add_score(reduced_score)
            self._game_scene.add_boss_kill()
        if hasattr(self._game_scene, "trigger_boss_death_explosion"):
            self._game_scene.trigger_boss_death_explosion(boss)
        self._game_scene.clear_boss()
        self._game_scene.show_notification(f"BOSS +{reduced_score} (mothership)")

    def _on_state_changed(self, state, **kwargs) -> None:
        if state == MotherShipState.PRESSING:
            self._mother_ship.show_phantom()
            self._clear_ripple_effects()
        elif state == MotherShipState.IDLE:
            self._mother_ship.hide_phantom()
            self._mother_ship.hide()
            self._clear_undocking_cooldown_modifier()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.ENTERING:
            self._mother_ship.hide_phantom()
            self._clear_ripple_effects()
        elif state == MotherShipState.COOLDOWN:
            self._mother_ship.hide()
            self._clear_undocking_cooldown_modifier()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.UNDOCKING:
            self._mother_ship.show()
            self._clear_ripple_effects()
            self._clear_mothership_bullets()
        elif state == MotherShipState.DOCKED:
            self._mother_ship.show()
            self._player_control_disabled = False
            self._activate_invincibility()
            self._clear_ripple_effects()

    def _activate_invincibility(self) -> None:
        if self._game_scene and hasattr(self._game_scene, "acquire_lock"):
            self._game_scene.acquire_lock(
                LockLayer.MOTHERSHIP,
                LockRequest(
                    invincible=True,
                    lock_controls=True,
                    is_silent_invincible=True,
                    invincibility_duration=GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES,
                ),
            )
        elif self._game_scene:
            if hasattr(self._game_scene, "set_player_invincible"):
                self._game_scene.set_player_invincible(
                    True,
                    GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES,
                    silent=True,
                )
            if getattr(self._game_scene, "player", None):
                self._game_scene.player.is_controls_locked = True

    def _on_cooldown_started(self, **kwargs) -> None:
        self._deactivate_invincibility()
        # Apply ammo refund from early exit: start cooldown with partial progress
        # so the player regenerates ammo faster.
        if self._exit_refund_progress > 0.0:
            self._state_machine.restore_cooldown_state(self._exit_refund_progress)
            self._exit_refund_progress = 0.0

    def _on_exit_complete(self, **kwargs) -> None:
        """Calculate ammo refund when player exits mothership early.

        Refund is proportional to remaining stay time, capped at 30% of
        total ammo to prevent abuse.
        """
        stay = self._state_machine.stay_progress
        remaining_ratio = max(0.0, 1.0 - stay.stay_progress)
        # Refund up to 30% of total ammo, proportional to remaining stay
        self._exit_refund_progress = min(0.3, remaining_ratio * 0.5)

    def _on_stay_started(self, **kwargs) -> None:
        pass

    def _on_undock_requested(self, **kwargs) -> None:
        pass

    def _on_exit_started(self, timestamp=None, **kwargs) -> None:
        self._input_detector.start_exit_hold(timestamp)
        self._progress_bar_ui.show(self.BAR_TYPE_EXIT, getattr(self._input_detector, "_exit_required_duration", 2.0))

    def _on_exit_progress_update(self, progress=None, **kwargs) -> None:
        self._progress_bar_ui.update_progress(progress or 0.0)

    def _on_exit_cancelled(self, **kwargs) -> None:
        self._progress_bar_ui.hide()

    def _deactivate_invincibility(self) -> None:
        if self._game_scene and hasattr(self._game_scene, "release_lock"):
            self._game_scene.release_lock(LockLayer.MOTHERSHIP)
        elif self._game_scene:
            if hasattr(self._game_scene, "set_player_invincible"):
                self._game_scene.set_player_invincible(False, 0, silent=False)
            if getattr(self._game_scene, "player", None):
                self._game_scene.player.is_controls_locked = False

    def _apply_cooldown_multiplier_from_player(self) -> None:
        """Read player's Mothership Recall buff and apply to cooldown."""
        if self._game_scene and self._game_scene.player:
            mult = getattr(self._game_scene.player, "mothership_cooldown_mult", 1.0)
            self._state_machine.cooldown.cooldown_multiplier = mult * self._undocking_cooldown_multiplier

    def _clear_undocking_cooldown_modifier(self) -> None:
        self._undocking_cooldown_multiplier = 1.0

    def _calculate_undocking_cooldown_multiplier(self) -> float:
        stay_progress = 1.0
        if self._state_machine and self._state_machine.stay_progress:
            stay_progress = self._state_machine.stay_progress.stay_progress
        remaining_ratio = max(0.0, min(1.0, 1.0 - stay_progress))
        return max(0.6, 1.0 - remaining_ratio * 0.4)

    def create_save_data(self) -> "GameSaveData":
        if not self._game_scene:
            return GameSaveData()

        is_docked = self._state_machine.current_state == MotherShipState.DOCKED

        sm = self._state_machine
        mothership_state = sm.current_state.value
        cooldown_progress = sm.cooldown.cooldown_progress if sm.current_state == MotherShipState.COOLDOWN else 0.0
        stay_progress = sm.stay_progress.stay_progress if is_docked else 0.0

        player = getattr(self._game_scene, "player", None)
        game_controller = getattr(self._game_scene, "game_controller", None)
        game_controller_state = getattr(game_controller, "state", None)
        return GameSaveData(
            score=getattr(self._game_scene, "get_score", lambda: 0)(),
            cycle_count=getattr(self._game_scene, "get_cycle_count", lambda: 0)(),
            kill_count=getattr(self._game_scene, "get_kill_count", lambda: 0)(),
            boss_kill_count=getattr(self._game_scene, "get_boss_kill_count", lambda: 0)(),
            unlocked_buffs=getattr(self._game_scene, "get_unlocked_buffs", lambda: [])(),
            buff_levels=self._get_buff_levels(),
            earned_buff_levels=self._get_earned_buff_levels(),
            talent_loadout=self._get_talent_loadout(),
            player_health=getattr(self._game_scene, "get_player_health", lambda: 0)(),
            player_max_health=getattr(self._game_scene, "get_player_max_health", lambda: 0)(),
            difficulty=getattr(self._game_scene, "get_difficulty", lambda: "medium")(),
            player_x=player.rect.x if player else 0,
            player_y=player.rect.y if player else 0,
            is_in_mothership=is_docked,
            mothership_state=mothership_state,
            mothership_cooldown_progress=cooldown_progress,
            mothership_stay_progress=stay_progress,
            username=getattr(self._game_scene, "get_username", lambda: "")(),
            requisition_points=getattr(game_controller_state, "requisition_points", 0),
        )

    def _on_game_resume(self, **kwargs) -> None:
        if self._game_scene:
            self._game_scene.set_paused(False)

    def _on_undock_cancelled(self, **kwargs) -> None:
        pass

    def _clear_mothership_bullets(self) -> None:
        self._mothership_bullets.clear()
        self._mothership_fire_elapsed = 0.0
        self._gatling.reset_timers()

    def _get_entity_score(self, entity, fallback: int) -> int:
        data = getattr(entity, "data", None)
        return getattr(data, "score", getattr(entity, "score", fallback))

    def _clear_ripple_effects(self) -> None:
        if not self._game_scene:
            return

        self._game_scene.clear_ripple_effects()

    def _get_buff_levels(self) -> dict[str, int]:
        if not self._game_scene:
            return {}
        return self._game_scene.get_buff_levels()

    def _get_earned_buff_levels(self) -> dict[str, int]:
        if not self._game_scene or not hasattr(self._game_scene, "get_earned_buff_levels"):
            return self._get_buff_levels()
        return self._game_scene.get_earned_buff_levels()

    def _get_talent_loadout(self) -> dict[str, str]:
        if not self._game_scene or not hasattr(self._game_scene, "get_talent_loadout"):
            return {}
        return self._game_scene.get_talent_loadout()

    def get_status_data(self) -> dict:
        """Return mothership state data for the ammo magazine and warning UI."""
        state = self._state_machine.current_state
        cd = self._state_machine.cooldown
        stay = self._state_machine.stay_progress
        stay.update_stay(self._current_time)

        # Compute ammo count based on state
        is_present = state in (
            MotherShipState.PRESSING,
            MotherShipState.ENTERING,
            MotherShipState.DOCKING,
            MotherShipState.DOCKED,
            MotherShipState.UNDOCKING,
        )
        is_cooldown = self._state_machine.is_in_cooldown()
        is_docked = state == MotherShipState.DOCKED

        if is_cooldown:
            ammo_count = cd.cooldown_progress * self.AMMO_CELL_COUNT
        elif is_docked:
            ammo_count = (1.0 - stay.stay_progress) * self.AMMO_CELL_COUNT
        elif state in (
            MotherShipState.IDLE,
            MotherShipState.PRESSING,
            MotherShipState.ENTERING,
            MotherShipState.DOCKING,
        ):
            ammo_count = self.AMMO_CELL_COUNT
        else:
            ammo_count = 0.0

        ammo_warning = is_docked and ammo_count <= 4.0

        return {
            "state": state,
            "is_present": is_present,
            "is_in_cooldown": is_cooldown,
            "is_docked": is_docked,
            "cooldown_progress": cd.cooldown_progress,
            "cooldown_remaining": cd.get_remaining_time(self._current_time),
            "cooldown_duration": cd.cooldown_duration,
            "cooldown_base_duration": cd.BASE_COOLDOWN,
            "cooldown_multiplier": cd.cooldown_multiplier,
            "cooldown_reduction": max(0.0, 1.0 - cd.cooldown_multiplier),
            "hold_progress": (
                self._input_detector.get_progress().current_progress if state == MotherShipState.PRESSING else 0.0
            ),
            "stay_progress": stay.stay_progress,
            "stay_remaining": (
                max(0.0, stay.stay_duration - (self._current_time - stay.stay_start_time))
                if stay.is_staying
                else 0.0
            ),
            "stay_duration": stay.stay_duration,
            "ammo_count": ammo_count,
            "ammo_max": self.AMMO_CELL_COUNT,
            "ammo_warning": ammo_warning,
        }

    def render(self, surface) -> None:
        self._mother_ship.render(surface)
        self._render_mothership_bullets(surface)

    def _render_mothership_bullets(self, surface) -> None:
        for bullet in self._mothership_bullets:
            self._entity_renderer.render_bullet(surface, bullet)

    def is_docked(self) -> bool:
        return self._state_machine.current_state == MotherShipState.DOCKED

    @property
    def event_bus(self) -> "EventBus":
        """Expose the mothership event bus for external subscribers.

        Callers must not mutate the returned bus's internal
        subscriber lists; they may subscribe to events via the
        public :meth:`EventBus.subscribe` API. The bus is owned by
        the integrator and outlives this property accessor.
        """
        return self._event_bus

    def get_current_state(self) -> MotherShipState:
        """Return the current mothership state machine state."""
        return self._state_machine.current_state

    def get_docking_position(self) -> tuple:
        return self._mother_ship.get_docking_position()

    def force_docked_state(self, stay_progress: float = 0.0) -> None:
        self._state_machine.restore_docked_state(stay_progress)
        self._mother_ship.show()
        self._player_control_disabled = False
        self._activate_invincibility()
