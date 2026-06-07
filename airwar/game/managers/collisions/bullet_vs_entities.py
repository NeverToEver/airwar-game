"""Phase 4 god-class split: player bullets vs enemies/boss collision strategy.

Extracted from ``CollisionController`` (33-method god class). This module owns
the collision logic between player-fired bullets and enemy entities (including
the boss), including the Rust-vs-Python spatial-hash dispatch and explosive
AoE handling.

The strategy class is stateless from the caller's perspective — the parent
``CollisionController`` provides shared containers (bullet data buffers,
explosion callback, grid cell size) via the constructor. Public entry
points mirror the legacy ``CollisionController`` API so callers see no change.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ...constants import GAME_CONSTANTS

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet
    from airwar.entities.enemy import Boss, Enemy


class BulletVsEntitiesStrategy:
    """Strategy: player bullets vs enemies + boss.

    The strategy exposes two public methods that mirror the legacy
    ``CollisionController`` API:

    * ``check_player_bullets_vs_enemies(...)`` -- bullets against every active
      enemy, with piercing and explosive talent handling.
    * ``check_player_bullets_vs_boss(...)`` -- bullets against the active boss.

    Both methods internally pick the Rust batch path when available and
    fall back to a Python spatial-hash scan otherwise.
    """

    def __init__(
        self,
        grid_cell_size: int,
        bullet_data: list[tuple],
        bullet_map: dict,
        enemy_data: list[tuple],
        enemy_map: dict,
        get_potential_collisions: Callable,
        get_potential_explosion_targets: Callable,
        get_potential_boss_bullets: Callable,
        get_explosion_callback: Callable[[], Callable | None],
        uses_rust_batch_collision: Callable[[], bool],
        bullet_has_hit_enemy: Callable[[Bullet, Enemy], bool],
        record_bullet_enemy_hit: Callable[[Bullet, Enemy], None],
        is_python_grid_populated: Callable[[], bool],
    ) -> None:
        self._grid_cell_size = grid_cell_size
        self._bullet_data = bullet_data
        self._bullet_map = bullet_map
        self._enemy_data = enemy_data
        self._enemy_map = enemy_map
        self._get_potential_collisions = get_potential_collisions
        self._get_potential_explosion_targets = get_potential_explosion_targets
        self._get_potential_boss_bullets = get_potential_boss_bullets
        self._get_explosion_callback = get_explosion_callback
        self._uses_rust_batch_collision = uses_rust_batch_collision
        self._bullet_has_hit_enemy = bullet_has_hit_enemy
        self._record_bullet_enemy_hit = record_bullet_enemy_hit
        self._is_python_grid_populated = is_python_grid_populated

    def check_player_bullets_vs_enemies(
        self,
        player_bullets: list[Bullet],
        enemies: list[Enemy],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int = 0,
    ) -> tuple[int, int]:
        """Resolve collisions between player bullets and enemy entities.

        Dispatches to Rust batch collision when available, otherwise falls
        back to a Python spatial-hash scan. Applies damage, triggers AoE
        explosions for explosive bullets, and respects piercing level.

        Args:
            player_bullets: Bullets fired by the player.
            enemies: Active enemy entities to test against.
            score_multiplier: Multiplier applied to kill scores.
            explosive_level: Talent level for AoE explosions.
            piercing_level: Talent level for bullet piercing.

        Returns:
            tuple[int, int]: (total_score_gained, enemies_killed_count).
        """
        if self._uses_rust_batch_collision():
            return self._check_player_bullets_vs_enemies_rust(
                player_bullets,
                enemies,
                score_multiplier,
                explosive_level,
                piercing_level,
            )
        return self._check_player_bullets_vs_enemies_python(
            player_bullets,
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )

    def _check_player_bullets_vs_enemies_rust(
        self,
        player_bullets: list[Bullet],
        enemies: list[Enemy],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> tuple[int, int]:
        # Reference the parent module so test monkeypatches on
        # ``airwar.game.managers.collision_controller.batch_collide_bullets_vs_entities``
        # take effect. Attribute access on the module picks up patches at call time.
        from airwar.game.managers import collision_controller as _cc_module

        batch_collide = _cc_module.batch_collide_bullets_vs_entities

        score_gained = 0
        enemies_killed = 0

        bullet_data, bullet_map = self._build_bullet_collision_data(player_bullets)
        enemy_data, enemy_map = self._build_enemy_collision_data(enemies)
        if not bullet_data or not enemy_data:
            return score_gained, enemies_killed

        hits = batch_collide(bullet_data, enemy_data, self._grid_cell_size)

        for bid, eid in hits:
            bullet = bullet_map.get(bid)
            enemy = enemy_map.get(eid)
            if bullet is None or enemy is None or not bullet.active or not enemy.active:
                continue
            if piercing_level > 0 and self._bullet_has_hit_enemy(bullet, enemy):
                continue
            killed, score = self._apply_player_bullet_hit(
                bullet,
                enemy,
                enemies,
                score_multiplier,
                explosive_level,
                piercing_level,
            )
            enemies_killed += killed
            score_gained += score

        return score_gained, enemies_killed

    def _build_bullet_collision_data(self, player_bullets: list[Bullet]) -> tuple[list[tuple], dict]:
        bullet_data = self._bullet_data
        bullet_map = self._bullet_map
        bullet_data.clear()
        bullet_map.clear()
        for i, bullet in enumerate(player_bullets):
            if bullet.active:
                r = bullet.rect
                bullet_data.append((i, float(r.left), float(r.top), float(r.width), float(r.height)))
                bullet_map[i] = bullet
        return bullet_data, bullet_map

    def _build_enemy_collision_data(self, enemies: list[Enemy]) -> tuple[list[tuple], dict]:
        enemy_data = self._enemy_data
        enemy_map = self._enemy_map
        enemy_data.clear()
        enemy_map.clear()
        for i, enemy in enumerate(enemies):
            if enemy.active:
                eid = -i - 1
                hb = enemy.get_hitbox()
                enemy_data.append((eid, float(hb.left), float(hb.top), float(hb.width), float(hb.height)))
                enemy_map[eid] = enemy
        return enemy_data, enemy_map

    def _check_player_bullets_vs_enemies_python(
        self,
        player_bullets: list[Bullet],
        enemies: list[Enemy],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

        use_spatial_hash = self._is_python_grid_populated()

        for bullet in player_bullets:
            if not bullet.active:
                continue

            bullet_rect = bullet.rect

            if use_spatial_hash:
                potential_enemies = self._get_potential_collisions(bullet_rect)
            else:
                potential_enemies = [e for e in enemies if e.active]

            for enemy in potential_enemies:
                if not enemy.active:
                    continue

                if bullet_rect.colliderect(enemy.get_hitbox()):
                    if piercing_level > 0 and self._bullet_has_hit_enemy(bullet, enemy):
                        continue
                    killed, score = self._apply_player_bullet_hit(
                        bullet,
                        enemy,
                        enemies,
                        score_multiplier,
                        explosive_level,
                        piercing_level,
                    )
                    enemies_killed += killed
                    score_gained += score
                    break

        return score_gained, enemies_killed

    def _apply_player_bullet_hit(
        self,
        bullet: Bullet,
        enemy: Enemy,
        enemies: list[Enemy],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> tuple[int, int]:
        enemy.take_damage(bullet.data.damage)
        if bullet.data.owner == "player" and piercing_level > 0:
            self._record_bullet_enemy_hit(bullet, enemy)

        if explosive_level > 0:
            self._handle_explosive_damage(bullet, enemies, explosive_level)

        enemies_killed = 0
        score_gained = 0
        if not enemy.active:
            enemies_killed = 1
            score_gained = _scaled_score(enemy.data.score, score_multiplier)

        if bullet.data.owner == "player" and piercing_level <= 0:
            bullet.active = False

        return enemies_killed, score_gained

    def _handle_explosive_damage(self, bullet: Bullet, enemies: list[Enemy], explosive_level: int) -> None:
        bullet_x = bullet.rect.centerx
        bullet_y = bullet.rect.centery
        explosion_radius_sq = (GAME_CONSTANTS.BALANCE.EXPLOSION_RADIUS * explosive_level) ** 2
        explosion_radius = GAME_CONSTANTS.BALANCE.EXPLOSION_RADIUS * explosive_level

        explosion_triggered = False
        explosion_callback = self._get_explosion_callback()

        for enemy in self._get_potential_explosion_targets(bullet_x, bullet_y, explosion_radius, enemies):
            if enemy.active:
                dx = bullet_x - enemy.rect.centerx
                dy = bullet_y - enemy.rect.centery
                distance_sq = dx * dx + dy * dy

                if distance_sq <= explosion_radius_sq:
                    explosion_damage = GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE * explosive_level
                    enemy.take_damage(explosion_damage)

                    if not explosion_triggered and explosion_callback:
                        explosion_callback(bullet_x, bullet_y, explosion_radius)
                        explosion_triggered = True

    def check_player_bullets_vs_boss(
        self, player_bullets: list[Bullet], boss: Boss, piercing_level: int
    ) -> tuple[int, bool]:
        """Resolve collisions between player bullets and the active boss.

        Applies bullet damage to the boss until a killing blow is dealt
        (in which case remaining bullets are skipped to avoid hitting a
        corpse). For non-piercing bullets, hit bullets are deactivated.

        Args:
            player_bullets: Bullets fired by the player.
            boss: Active boss entity to test against.
            piercing_level: Talent level for bullet piercing.

        Returns:
            tuple[int, bool]: (score_gained, boss_killed_flag).
        """
        if not boss or not boss.active:
            return 0, False

        score_gained = 0
        boss_killed = False

        boss_hitbox = boss.get_hitbox()
        active_count = 0
        found_hit = False
        for bullet in player_bullets:
            if not bullet.active:
                continue
            active_count += 1
            if bullet.get_rect().colliderect(boss_hitbox):
                found_hit = True
                break
            if active_count >= 32:
                break
        if active_count < 32 and not found_hit:
            return 0, False

        for bullet in self._get_potential_boss_bullets(player_bullets, boss_hitbox, active_count):
            if bullet.active and bullet.get_rect().colliderect(boss_hitbox):
                score_reward = boss.take_damage(bullet.data.damage)
                if score_reward > 0:
                    score_gained += score_reward
                    boss_killed = True
                    break  # Boss killed -- stop iterating, remaining bullets would hit a corpse
                if piercing_level <= 0:
                    bullet.active = False

        return score_gained, boss_killed


def _scaled_score(base_score: int, multiplier: float) -> int:
    return round(base_score * multiplier)
