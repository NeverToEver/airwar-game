"""Collision detection between entities using spatial hashing.

This module coordinates one instance per collision strategy (see
:mod:`airwar.game.managers.collisions`) and delegates the heavy lifting to
them:

* :class:`~airwar.game.managers.collisions.BulletVsEntitiesStrategy`
  -- player bullets vs enemies + boss.
* :class:`~airwar.game.managers.collisions.EnemyBulletVsPlayerStrategy`
  -- enemy bullets vs player.
* :class:`~airwar.game.managers.collisions.BossVsPlayerStrategy`
  -- boss body vs player body.
* :class:`~airwar.game.managers.collisions.CollisionEventDispatcher`
  -- ``CollisionEvent`` + per-frame player-hit handler factory.

The Python spatial-hash helpers (``_add_to_grid``, ``_get_potential_collisions``,
``_get_potential_explosion_targets``, ``_get_potential_boss_bullets``,
``_get_entities_in_cells``) stay on the controller because both the
strategies need them.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..constants import GAME_CONSTANTS
from .collisions import (
    BossVsPlayerStrategy,
    BulletVsEntitiesStrategy,
    CollisionEvent,
    CollisionEventDispatcher,
    EnemyBulletVsPlayerStrategy,
)

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet
    from airwar.entities.enemy import Boss, Enemy
    from airwar.entities.player import Player

from airwar.core_bindings import (
    batch_collide_bullets_vs_entities,
)


@dataclass
class CollisionResult:
    """Collision result dataclass — score gained and enemies killed."""

    player_damaged: bool = False
    enemies_killed: int = 0
    score_gained: int = 0
    boss_damaged: bool = False
    boss_killed: bool = False


@dataclass(frozen=True)
class _QueryRect:
    left: float
    right: float
    top: float
    bottom: float


class CollisionController:
    """Collision controller — detects and handles entity collisions.

    Supports Rust-accelerated spatial hashing for efficient
    collision detection between player bullets, enemy bullets, enemies,
    bosses, and the player.

    Attributes:
        _events: Registered collision event callbacks.
        _use_rust: Whether Rust batch collision is enabled.
        _previous_enemy_ids: Set of enemy ids tracked from the previous frame.
    """

    GRID_CELL_SIZE = 100

    def __init__(self):
        self._events: list[CollisionEvent] = []
        self._explosion_callback: Callable[[float, float, int], None] | None = None
        # Spatial hash grid for collision optimization
        self._grid_cells: dict[tuple[int, int], list[Any]] = {}
        self._enemy_grid_cells: dict[tuple[int, int], list[Any]] = {}
        self._grid_cell_size = self.GRID_CELL_SIZE
        self._use_rust = True
        self._previous_enemy_ids: set = set()
        # Reusable temp containers for Rust batch collision
        self._bullet_data: list[tuple] = []
        self._bullet_map: dict = {}
        self._enemy_data: list[tuple] = []
        self._enemy_map: dict = {}
        # Reusable temp containers for enemy-bullets-vs-player Rust collision
        self._enemy_bullet_data: list[tuple] = []
        self._enemy_bullet_map: dict = {}
        self._player_entity_data: list[tuple] = []

        # Phase 4 split: 4 strategy components, each owns one collision kind.
        self._bullet_vs_entities = BulletVsEntitiesStrategy(
            grid_cell_size=self._grid_cell_size,
            bullet_data=self._bullet_data,
            bullet_map=self._bullet_map,
            enemy_data=self._enemy_data,
            enemy_map=self._enemy_map,
            get_potential_collisions=self._get_potential_collisions,
            get_potential_explosion_targets=self._get_potential_explosion_targets,
            get_potential_boss_bullets=self._get_potential_boss_bullets,
            get_explosion_callback=lambda: self._explosion_callback,
            uses_rust_batch_collision=self._uses_rust_batch_collision,
            bullet_has_hit_enemy=self._bullet_has_hit_enemy,
            record_bullet_enemy_hit=self._record_bullet_enemy_hit,
            is_python_grid_populated=lambda: bool(self._grid_cells),
        )
        self._enemy_bullet_vs_player = EnemyBulletVsPlayerStrategy(
            grid_cell_size=self._grid_cell_size,
            enemy_bullet_data=self._enemy_bullet_data,
            enemy_bullet_map=self._enemy_bullet_map,
            player_entity_data=self._player_entity_data,
            get_use_rust=lambda: bool(self._use_rust),
        )
        self._boss_vs_player = BossVsPlayerStrategy()

    # ---- Spatial-hash helpers (shared with Python fallback in strategies) ----

    def _clear_grid(self) -> None:
        """Clear the spatial hash grid."""
        self._grid_cells.clear()
        self._enemy_grid_cells.clear()

    def _get_rect_bounds(self, rect) -> tuple[int, int, int, int]:
        """Get (left, right, top, bottom) from rect, supporting both pygame.Rect and MockRect."""
        if hasattr(rect, "left"):
            return rect.left, rect.right, rect.top, rect.bottom
        else:
            # MockRect uses centerx, centery, width, height
            left = rect.centerx - rect.width // 2
            top = rect.centery - rect.height // 2
            return left, left + rect.width, top, top + rect.height

    def _get_cell_key(self, x: int, y: int) -> tuple[int, int]:
        """Get grid cell key for a position."""
        return (math.floor(x / self._grid_cell_size), math.floor(y / self._grid_cell_size))

    def _add_to_grid(self, entity, rect) -> None:
        """Add entity to spatial hash grid based on its rect."""
        self._add_entity_to_cells(self._grid_cells, entity, rect)

    def _add_to_enemy_grid(self, entity, rect) -> None:
        """Add enemy to the reusable enemy spatial grid."""
        self._add_entity_to_cells(self._enemy_grid_cells, entity, rect)

    def _add_entity_to_cells(self, cells: dict, entity, rect) -> None:
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = math.floor(left / self._grid_cell_size)
        max_x = math.floor(right / self._grid_cell_size)
        min_y = math.floor(top / self._grid_cell_size)
        max_y = math.floor(bottom / self._grid_cell_size)

        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key not in cells:
                    cells[key] = []
                cells[key].append(entity)

    def _get_potential_collisions(self, rect) -> list:
        """Get entities that might collide with the given rect."""
        return self._get_entities_in_cells(self._grid_cells, rect)

    def _get_potential_explosion_targets(self, x: float, y: float, radius: float, enemies: list[Enemy]) -> list:
        if not self._enemy_grid_cells:
            return [enemy for enemy in enemies if enemy.active]
        rect = self._make_query_rect(x, y, radius)
        return self._get_entities_in_cells(self._enemy_grid_cells, rect)

    def _get_potential_boss_bullets(self, player_bullets: list[Bullet], boss_hitbox, active_count: int) -> list[Bullet]:
        if active_count < 32:
            return [bullet for bullet in player_bullets if bullet.active]

        grid: dict = {}
        for bullet in player_bullets:
            if bullet.active:
                self._add_entity_to_cells(grid, bullet, bullet.get_rect())
        return list(self._get_entities_in_cells(grid, boss_hitbox))

    def _get_entities_in_cells(self, cells: dict, rect) -> list:
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = math.floor(left / self._grid_cell_size)
        max_x = math.floor(right / self._grid_cell_size)
        min_y = math.floor(top / self._grid_cell_size)
        max_y = math.floor(bottom / self._grid_cell_size)

        potential = []
        seen_ids = set()
        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key in cells:
                    for entity in cells[key]:
                        entity_id = id(entity)
                        if entity_id not in seen_ids:
                            potential.append(entity)
                            seen_ids.add(entity_id)
        return potential

    @staticmethod
    def _make_query_rect(center_x: float, center_y: float, radius: float):
        return _QueryRect(
            left=center_x - radius,
            right=center_x + radius,
            top=center_y - radius,
            bottom=center_y + radius,
        )

    # ---- Bullet-per-enemy hit helpers (shared with strategies) ----

    def _get_enemy_collision_id(self, enemy: Enemy) -> int:
        return id(enemy)

    def _bullet_has_hit_enemy(self, bullet: Bullet, enemy: Enemy) -> bool:
        enemy_id = self._get_enemy_collision_id(enemy)
        has_hit_enemy = getattr(bullet, "has_hit_enemy", None)
        return bool(has_hit_enemy and has_hit_enemy(enemy_id))

    def _record_bullet_enemy_hit(self, bullet: Bullet, enemy: Enemy) -> None:
        add_hit_enemy = getattr(bullet, "add_hit_enemy", None)
        if add_hit_enemy:
            add_hit_enemy(self._get_enemy_collision_id(enemy))

    def _uses_rust_batch_collision(self) -> bool:
        return bool(self._use_rust and batch_collide_bullets_vs_entities is not None)

    # ---- Public API (Phase 4: 1-line forwarders to strategies) ----

    @property
    def events(self) -> list[CollisionEvent]:
        """Return a copy of the collision events recorded during the last check.

        Returns:
            list[CollisionEvent]: Snapshot of recorded events (safe to iterate
            without mutating the controller's internal list).
        """
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear all recorded collision events.

        Called by `check_all_collisions` at the start of each frame to
        ensure events reflect only the current frame's collisions.
        """
        self._events.clear()

    def set_explosion_callback(self, callback: Callable[[float, float, int], None]) -> None:
        """Set explosion callback function

        Args:
            callback: Callback function with signature (x, y, radius) -> None
        """
        self._explosion_callback = callback

    def check_all_collisions(
        self,
        player: Player,
        enemies: list[Enemy],
        boss: Boss | None,
        enemy_bullets: list[Bullet],
        reward_system: Any,
        explosive_level: int = 0,
        piercing_level: int = 0,
        player_invincible: bool = False,
        score_multiplier: float = 1.0,
        on_enemy_killed: Callable[[int], None] | None = None,
        on_boss_killed: Callable[[int], None] | None = None,
        on_boss_hit: Callable[[int], None] | None = None,
        on_player_hit: Callable[[int, Player], None] | None = None,
        on_lifesteal: Callable | None = None,
        on_clear_bullets: Callable | None = None,
    ) -> None:
        """Run all collision checks for the current frame and dispatch callbacks.

        Checks player bullets vs enemies/boss, enemy bullets vs player,
        player vs enemies, and boss vs player. Records resulting
        `CollisionEvent` entries in `self.events` and invokes the matching
        optional callbacks.

        Args:
            player: Player entity whose bullets and hitbox participate.
            enemies: Active enemy entities checked for collisions.
            boss: Active boss entity or None if not in boss phase.
            enemy_bullets: Live enemy bullets checked against the player.
            reward_system: RewardSystem providing `piercing_level`,
                `calculate_damage_taken`, and `try_dodge` helpers.
            explosive_level: Talent level for explosive bullet AoE.
            piercing_level: Talent level for piercing bullets.
            player_invincible: If True, skip player-side hit checks.
            score_multiplier: Multiplier applied to enemy kill scores.
            on_enemy_killed: Callback invoked with score gained per kill.
            on_boss_killed: Callback invoked when boss dies.
            on_boss_hit: Callback invoked when boss takes damage.
            on_player_hit: Callback invoked with damage and player entity.
            on_lifesteal: Optional lifesteal hook (player, score_gained).
            on_clear_bullets: Optional hook to clear remaining enemy bullets.
        """
        if player is None:
            return
        self._events.clear()
        player_hit_handler = CollisionEventDispatcher.make_player_hit_handler(
            player,
            on_player_hit,
            on_clear_bullets,
        )

        # The Rust collision path builds its own spatial data from batch input.
        # Keep the Python grid for the non-Rust collision path.
        self._clear_grid()
        if self._uses_rust_batch_collision():
            for enemy in enemies:
                if enemy.active:
                    self._add_to_enemy_grid(enemy, enemy.get_hitbox())
        else:
            for enemy in enemies:
                if enemy.active:
                    self._add_to_grid(enemy, enemy.get_hitbox())
                    self._add_to_enemy_grid(enemy, enemy.get_hitbox())

        score_gained, enemies_killed = self.check_player_bullets_vs_enemies(
            player.get_bullets(),
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )

        if enemies_killed > 0:
            self._events.append(CollisionEvent(type="enemy_killed", score=score_gained))
            if on_enemy_killed:
                on_enemy_killed(score_gained)
            if on_lifesteal:
                on_lifesteal(player, score_gained)

        if not player_invincible and self.check_enemy_bullets_vs_player(
            enemy_bullets, player, reward_system.calculate_damage_taken, player_hit_handler
        ):
            self._events.append(CollisionEvent(type="player_hit"))
            player_invincible = True  # Prevent double-hit this frame

        if not player_invincible and self.check_player_vs_enemies(
            player.get_hitbox(), enemies, reward_system.try_dodge, player_hit_handler
        ):
            self._events.append(CollisionEvent(type="player_hit"))
            player_invincible = True  # Prevent double-hit this frame

        if boss:
            boss_score, boss_killed = self.check_player_bullets_vs_boss(
                player.get_bullets(), boss, reward_system.piercing_level
            )

            if boss_killed:
                self._events.append(CollisionEvent(type="boss_killed", score=boss_score))
                if on_boss_killed:
                    on_boss_killed(boss_score)
            elif boss_score > 0:
                self._events.append(CollisionEvent(type="boss_hit", score=boss_score))
                if on_boss_hit:
                    on_boss_hit(boss_score)

            if not player_invincible and self.check_boss_vs_player(
                boss, player, reward_system.calculate_damage_taken, player_hit_handler
            ):
                self._events.append(CollisionEvent(type="player_hit"))

    def check_player_bullets_vs_enemies(
        self,
        player_bullets: list[Bullet],
        enemies: list[Enemy],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int = 0,
    ) -> tuple[int, int]:
        return self._bullet_vs_entities.check_player_bullets_vs_enemies(
            player_bullets,
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )

    def check_player_bullets_vs_boss(
        self, player_bullets: list[Bullet], boss: Boss, piercing_level: int
    ) -> tuple[int, bool]:
        return self._bullet_vs_entities.check_player_bullets_vs_boss(player_bullets, boss, piercing_level)

    def check_player_vs_enemies(
        self, player_hitbox, enemies: list[Enemy], try_dodge_func: Callable, on_player_hit_func: Callable
    ) -> bool:
        """Check whether the player's hitbox collides with any active enemy.

        Args:
            player_hitbox: pygame.Rect-like hitbox for the player.
            enemies: Active enemy entities checked for collisions.
            try_dodge_func: Callable returning True if the player dodged.
            on_player_hit_func: Callable invoked with damage on collision.

        Returns:
            bool: True if a non-dodged enemy collision occurred.
        """
        for enemy in enemies:
            if enemy.active and player_hitbox.colliderect(enemy.get_hitbox()) and not try_dodge_func():
                on_player_hit_func(GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE)
                return True

        return False

    def check_enemy_bullets_vs_player(
        self, enemy_bullets: list[Bullet], player, calculate_damage_func: Callable, on_player_hit_func: Callable
    ) -> bool:
        return self._enemy_bullet_vs_player.check_enemy_bullets_vs_player(
            enemy_bullets, player, calculate_damage_func, on_player_hit_func
        )

    def check_boss_vs_player(
        self, boss: Boss, player, calculate_damage_func: Callable, on_player_hit_func: Callable
    ) -> bool:
        return self._boss_vs_player.check_boss_vs_player(boss, player, calculate_damage_func, on_player_hit_func)
