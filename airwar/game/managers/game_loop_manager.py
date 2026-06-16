"""Game loop orchestration — coordinates all per-frame update logic."""

import logging
import struct
from collections.abc import Callable

from airwar.config import get_screen_height, get_screen_width
from airwar.config.constants_access import get_game_constants
from airwar.core_bindings import batch_update_movements, batch_update_movements_buf

from ..constants import PlayerConstants
from ..explosion_animation import ExplosionManager
from ..protocols import (
    BossManagerProtocol,
    BulletManagerProtocol,
    CollisionControllerProtocol,
    GameControllerProtocol,
    GameRendererProtocol,
    PlayerProtocol,
    RewardSystemProtocol,
    SpawnControllerProtocol,
)
from ..systems.lock_manager import LockLayer, LockRequest
from .game_controller import GameplayState

logger = logging.getLogger(__name__)


class EntityBuffer:
    """Pre-allocated scratch list reused across frames for entity updates.

    P1-2 perf: the per-frame entity update path used to build a fresh
    list each call (``active_enemies = []`` + ``append``) and discarded
    it at frame end. On boss-death frames with 5-7 effects × 40+
    enemies, this drives measurable allocation bandwidth (project scan
    2026-06-10). ``EntityBuffer`` owns a pre-sized list that callers
    ``reset()`` and refill; the list object is reused across frames so
    steady-state allocation is zero.

    The buffer is single-threaded (called from the main game loop) and
    is intentionally not thread-safe. Capacity is the practical
    maximum (enemies + boss + safety margin).
    """

    DEFAULT_CAPACITY: int = 64

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._buf: list = [None] * max(1, capacity)
        self._size: int = 0
        self._capacity: int = max(1, capacity)

    def reset(self) -> None:
        """Reset the buffer to empty (logical clear, no allocation)."""
        # Replace contents with None rather than re-binding the slice
        # to keep the underlying list object stable.
        for i in range(self._size):
            self._buf[i] = None
        self._size = 0

    def add(self, item) -> None:
        """Append ``item`` to the buffer; grows once if at capacity."""
        if self._size >= self._capacity:
            # Grow once: doubles capacity. Rare in practice — the
            # pre-allocated 64 covers enemies + boss in normal play.
            self._buf.extend([None] * self._capacity)
            self._capacity *= 2
        self._buf[self._size] = item
        self._size += 1

    def __iter__(self):
        # Iterate over the live slice only. Avoids yielding Nones and
        # avoids the cost of ``list(buf)`` materialisation.
        for i in range(self._size):
            yield self._buf[i]

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def to_list(self) -> list:
        """Return a fresh ``list`` snapshot of the live items.

        Use this only when callers require a real list (e.g. slicing,
        len-based indexing, passing to Rust FFI that expects a
        sequence). The returned list is a *copy*; mutating it does
        not affect the buffer.
        """
        return self._buf[: self._size]

    def __getitem__(self, index: int):
        if index < 0:
            index += self._size
        if not 0 <= index < self._size:
            raise IndexError(index)
        return self._buf[index]


# F03 S1: explicit exception for bad Rust batch movement parameters.
# Was previously swallowed with ``logger.warning + continue``; the
# refactor raises so callers cannot accidentally accept silently
# malformed data.
class MovementParamError(ValueError):
    """Raised when an enemy returns invalid Rust batch movement params.

    F03 S1 + S2: replaces the legacy silent ``logger.warning + continue``
    pattern. The data flow is: ``Enemy.get_rust_batch_params() -> tuple``
    and any malformed result (wrong length, mismatched pair) is a bug.
    """


class GameLoopManager:
    """Game loop manager — orchestrates all per-frame update logic.

    Coordinates the update order of all managers and systems each frame:
    input → player update → spawn controller → boss → collision → UI.

    Attributes:
        _controllers: Ordered list of per-frame update callables.
    """

    def __init__(
        self,
        game_controller: GameControllerProtocol,
        game_renderer: GameRendererProtocol,
        spawn_controller: SpawnControllerProtocol,
        reward_system: RewardSystemProtocol,
        bullet_manager: BulletManagerProtocol,
        boss_manager: BossManagerProtocol,
        collision_controller: CollisionControllerProtocol,
        lock_manager=None,
    ):
        self._game_controller = game_controller
        self._game_renderer = game_renderer
        self._spawn_controller = spawn_controller
        self._reward_system = reward_system
        self._bullet_manager = bullet_manager
        self._boss_manager = boss_manager
        self._collision_controller = collision_controller
        self._lock_manager = lock_manager

        # P1-2: pre-allocated scratch buffers for the entity-update
        # hot path. ``_entity_buf`` is reused across frames to avoid
        # per-frame list allocation; ``_batch_indices`` ditto.
        self._entity_buf: EntityBuffer = EntityBuffer()
        self._batch_indices: EntityBuffer = EntityBuffer()

        self._init_explosion_system()

    def _init_explosion_system(self) -> None:
        """Initialize explosion animation system"""
        self._explosion_manager = ExplosionManager()
        self._collision_controller.set_explosion_callback(self._on_explosion)

    def _on_explosion(self, x: float, y: float, radius: int) -> None:
        """Explosion callback handler"""
        self._explosion_manager.trigger(x, y, radius)

    def _on_boss_destroyed(self) -> None:
        boss = self._spawn_controller.boss
        if boss:
            self._explosion_manager.trigger_boss_death(
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
            )
        self._boss_manager.on_boss_killed()

    def _handle_boss_killed(self, score: int) -> None:
        """Handle boss killed event with proper error handling.

        Args:
            score: Score gained from killing the boss.
        """
        try:
            self._on_boss_destroyed()
        except Exception:
            logger.exception("Error in _on_boss_destroyed")
        self._game_controller.on_boss_killed(score)

    def update_entrance(self, player: PlayerProtocol) -> bool:
        state = self._game_controller.state
        state.entrance_timer += 1
        progress = state.entrance_timer / state.entrance_duration

        if progress >= 1.0:
            state.is_entrance_playing = False
            player.rect.y = get_screen_height() - PlayerConstants.SCREEN_BOTTOM_OFFSET
            return False
        else:
            self._animate_entrance(player, progress)
            return True

    def _animate_entrance(self, player: PlayerProtocol, progress: float) -> None:
        screen_width = get_screen_width()
        target_y = get_screen_height() - PlayerConstants.SCREEN_BOTTOM_OFFSET
        start_y = PlayerConstants.INITIAL_Y
        player.rect.y = int(start_y + (target_y - start_y) * progress)
        player.rect.x = screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET

    def update_game(self, player: PlayerProtocol) -> None:
        self._update_core(player)

    def _update_core(self, player: PlayerProtocol) -> None:
        has_regen = "Regeneration" in self._reward_system.unlocked_buffs
        self._game_controller.update(player, has_regen)
        self._refresh_locks()

        if self._game_controller.state.gameplay_state == GameplayState.DYING:
            self._game_renderer.update_death_animation()
            self._explosion_manager.update()
            return

        self._game_renderer.update_death_animation()
        self._explosion_manager.update()
        # F02 D3: single-path — LockManager is always wired in production.
        # The legacy backup/restore branch was reachable only in unit
        # tests that constructed GameLoopManager without a lock_manager;
        # those tests now also wire one (see test_game_loop_manager.py).
        if self._lock_manager is None:
            raise RuntimeError("GameLoopManager requires a LockManager. Pass lock_manager=... in the constructor.")
        # BOSS_ENRAGE is a transient lock — applied only for the duration
        # of player.update() and released immediately after, matching the
        # legacy "lock only during update" contract.
        self._sync_boss_enrage_lock()
        player.update()
        player.auto_fire()
        self._lock_manager.release(LockLayer.BOSS_ENRAGE)

        self._bullet_manager.update_all()
        self._update_enemy_spawning(player)
        self._update_entities()

        if self._spawn_controller.boss:
            self._boss_manager.update(player)

        if not player.active:
            self._game_controller.state.running = False

    def _should_lock_player_for_boss_enrage(self) -> bool:
        boss = self._boss_manager.boss
        return bool(boss and getattr(boss, "should_lock_player_movement", lambda: False)())

    def _sync_boss_enrage_lock(self) -> None:
        if not self._lock_manager:
            return
        boss = self._boss_manager.boss
        if not boss:
            self._lock_manager.release(LockLayer.BOSS_ENRAGE)
            return
        if self._should_lock_player_for_boss_enrage():
            in_transition = getattr(boss, "_enrage_transition_timer", 0) > 0
            enrage_transition_duration = get_game_constants().BOSS_ENRAGE.TRANSITION_DURATION
            self._lock_manager.acquire(
                LockLayer.BOSS_ENRAGE,
                LockRequest(
                    lock_controls=True,
                    invincible=in_transition,
                    invincibility_duration=enrage_transition_duration if in_transition else 0,
                ),
            )
        else:
            self._lock_manager.release(LockLayer.BOSS_ENRAGE)

    def _refresh_locks(self) -> None:
        if self._lock_manager and self._lock_manager.has_locks():
            self._lock_manager.refresh()

    def _update_enemy_spawning(self, player: PlayerProtocol) -> None:
        player_pos = (player.rect.centerx, player.rect.centery)
        player_dps = self._estimate_player_dps(player)
        self._spawn_controller.balance_for_player_dps(player_dps)
        spawn_needed = self._spawn_controller.update(
            self._game_controller.state.score, self._reward_system.slow_factor, player_pos
        )

        if spawn_needed:
            boss = self._spawn_controller.spawn_boss(
                self._game_controller.state.boss_kill_count, player.bullet_damage, player_dps
            )
            self._game_controller.show_notification(f"! BOSS 来袭 ({int(boss.data.escape_time / 60)}秒) !")

    def _estimate_player_dps(self, player: PlayerProtocol) -> float:
        weapon_status = player.get_weapon_status() if hasattr(player, "get_weapon_status") else {}
        bullets_per_shot = 6 if weapon_status.get("spread") else 2
        fire_interval = max(1, int(getattr(player, "fire_interval", PlayerConstants.FIRE_COOLDOWN)))
        damage = float(getattr(player, "bullet_damage", PlayerConstants.BULLET_DAMAGE))
        return damage * bullets_per_shot / fire_interval * 60

    # Binary buffer formats for movement FFI.
    # base: B(move_type) + 3*pad + 11*f32 = 48 bytes. Must match Rust
    # `BASE_BUF_STRIDE = 48` in `airwar_core/src/movement.rs`. The
    # previous fmt "<Bxxxfff fffffff" was 9 floats (44 bytes / 11
    # fields) and crashed the FFI because
    # `Enemy.get_rust_batch_params` returns a 12-element base tuple.
    # Fixed 2026-06-07.
    _MOVEMENT_BASE_FMT = "<Bxxx fffffffffff"
    _MOVEMENT_BASE_SIZE = struct.calcsize(_MOVEMENT_BASE_FMT)  # 48
    # extra: 7*f32 + i32 = 32 bytes
    _MOVEMENT_EXTRA_FMT = "<fffffffI"
    _MOVEMENT_EXTRA_SIZE = struct.calcsize(_MOVEMENT_EXTRA_FMT)  # 32

    def _update_entities(self) -> None:
        enemies = self._spawn_controller.enemies
        if not enemies:
            return

        # F03 S1 + S2: raise MovementParamError instead of silently
        # skipping bad params. The data flow is strictly typed
        # (Enemy -> 12-base + 8-extra tuple) and any mismatch is a bug.

        # P1-2: reuse pre-allocated buffers for batch indices so we
        # don't allocate fresh lists every frame. ``_entity_buf`` and
        # ``_batch_indices`` are reset, not re-bound, to keep the
        # underlying list objects stable across calls.
        # Lazy-init guards the ``__new__``-style test harness (some
        # perf tests bypass ``__init__`` and call private methods).
        batch_indices = getattr(self, "_batch_indices", None)
        if batch_indices is None:
            batch_indices = EntityBuffer()
            self._batch_indices = batch_indices
        batch_indices.reset()

        # Batch Rust movement — only for enemies in 'active' state (not entering/exiting)
        if batch_update_movements_buf is not None:
            base_buf_parts: list[bytes] = []
            extra_buf_parts: list[bytes] = []

            for i, enemy in enumerate(enemies):
                if enemy.is_ready_for_batch_movement():
                    base, extra = enemy.get_rust_batch_params()
                    if base is None and extra is None:
                        # Enemy not ready — that's fine, skip
                        continue
                    if base is not None and extra is not None:
                        # Pack base: (move_type:u8, pad, timer, active_x, active_y,
                        #   move_range_x, move_range_y, offset, amplitude, frequency,
                        #   speed, direction, zigzag_interval)
                        if len(base) != 12:
                            raise MovementParamError(
                                f"Enemy {enemy!r} returned base tuple of length {len(base)}, "
                                f"expected 12 (move_type + 11 fields)"
                            )
                        if len(extra) != 8:
                            raise MovementParamError(
                                f"Enemy {enemy!r} returned extra tuple of length {len(extra)}, "
                                f"expected 8 (spiral_radius + 7 fields)"
                            )
                        base_buf_parts.append(
                            struct.pack(
                                self._MOVEMENT_BASE_FMT,
                                base[0],
                                base[1],
                                base[2],
                                base[3],
                                base[4],
                                base[5],
                                base[6],
                                base[7],
                                base[8],
                                base[9],
                                base[10],
                                base[11],
                            )
                        )
                        # Pack extra: (spiral_radius, current_x, current_y,
                        #   noise_scale_x, noise_scale_y, noise_amplitude_x,
                        #   noise_amplitude_y, noise_seed)
                        extra_buf_parts.append(
                            struct.pack(
                                self._MOVEMENT_EXTRA_FMT,
                                extra[0],
                                extra[1],
                                extra[2],
                                extra[3],
                                extra[4],
                                extra[5],
                                extra[6],
                                extra[7],
                            )
                        )
                        batch_indices.add(i)
                    else:
                        # F03 S2: mismatched pair is a programming error.
                        raise MovementParamError(
                            f"get_rust_batch_params returned mismatched pair: "
                            f"base={base!r} extra={extra!r} for {enemy!r}. "
                            f"Both must be either None or valid tuples."
                        )

            if base_buf_parts:
                base_buf = b"".join(base_buf_parts)
                extra_buf = b"".join(extra_buf_parts)
                results = batch_update_movements_buf(base_buf, extra_buf)
                for j, (new_x, new_y, new_timer) in enumerate(results):
                    idx = batch_indices[j]
                    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))
        elif batch_update_movements is not None:
            # Fallback: tuple-based batch movement
            base_list = []
            extra_list = []
            for i, enemy in enumerate(enemies):
                if enemy.is_ready_for_batch_movement():
                    base, extra = enemy.get_rust_batch_params()
                    if base is None and extra is None:
                        continue
                    if base is not None and extra is not None:
                        if len(base) != 12:
                            raise MovementParamError(f"Fallback path: enemy {enemy!r} base len {len(base)}")
                        if len(extra) != 8:
                            raise MovementParamError(f"Fallback path: enemy {enemy!r} extra len {len(extra)}")
                        base_list.append(base)
                        extra_list.append(extra)
                        batch_indices.add(i)
                    else:
                        raise MovementParamError(f"Fallback path: mismatched pair for {enemy!r}")
            if base_list:
                results = batch_update_movements(base_list, extra_list)
                for j, (new_x, new_y, new_timer) in enumerate(results):
                    idx = batch_indices[j]
                    enemies[idx].apply_batch_movement_result((new_x, new_y, new_timer))

        for enemy in enemies:
            enemy.update(self._spawn_controller.enemies, self._reward_system.slow_factor)

    def check_collisions(
        self,
        player: PlayerProtocol,
        enemy_bullets: list,
        on_player_hit: Callable,
    ) -> None:
        self._collision_controller.check_all_collisions(
            player=player,
            enemies=self._spawn_controller.enemies,
            boss=self._spawn_controller.boss,
            enemy_bullets=enemy_bullets,
            reward_system=self._reward_system,
            explosive_level=self._reward_system.explosive_level,
            piercing_level=self._reward_system.piercing_level,
            player_invincible=self._game_controller.state.is_player_invincible,
            score_multiplier=self._game_controller.state.score_multiplier,
            on_enemy_killed=self._game_controller.on_enemy_killed,
            on_boss_killed=self._handle_boss_killed,
            on_boss_hit=self._boss_manager.on_boss_hit,
            on_player_hit=on_player_hit,
            on_lifesteal=self._reward_system.apply_lifesteal,
        )

    def is_entrance_playing(self) -> bool:
        return self._game_controller.state.is_entrance_playing

    def is_game_running(self) -> bool:
        return self._game_controller.state.running

    def render_explosions(self, surface) -> None:
        """Render all active explosion effects

        Args:
            surface: PyGame rendering surface
        """
        self._explosion_manager.render(surface)

    def get_explosion_stats(self) -> dict:
        """Get explosion system statistics

        Returns:
            dict: Statistics about the explosion system
        """
        return self._explosion_manager.get_stats()

    def trigger_boss_death_explosion(self, centerx: int, centery: int, width: int, height: int) -> None:
        """Trigger a boss death explosion at the given position."""
        self._explosion_manager.trigger_boss_death(centerx, centery, width, height)
