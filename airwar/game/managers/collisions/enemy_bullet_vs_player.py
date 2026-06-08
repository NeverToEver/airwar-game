"""Phase 4 god-class split: enemy bullets vs player collision strategy.

Extracted from ``CollisionController``. Owns the logic for testing active
enemy bullets against the player hitbox, choosing between the Rust
spatial-hash path and a Python linear scan fallback.

The strategy is parameterised by a few parent-owned containers and
``get_use_rust`` predicate so the parent ``CollisionController`` retains
single-source-of-truth for runtime configuration flags.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet
    from airwar.entities.player import Player


class EnemyBulletVsPlayerStrategy:
    """Strategy: enemy bullets vs player.

    Public method ``check_enemy_bullets_vs_player`` mirrors the legacy
    ``CollisionController`` API. The Rust path reuses the parent's
    reusable temp containers to avoid per-frame allocations.
    """

    def __init__(
        self,
        grid_cell_size: int,
        enemy_bullet_data: list[tuple],
        enemy_bullet_map: dict,
        player_entity_data: list[tuple],
        get_use_rust: Callable[[], bool],
    ) -> None:
        self._grid_cell_size = grid_cell_size
        self._enemy_bullet_data = enemy_bullet_data
        self._enemy_bullet_map = enemy_bullet_map
        self._player_entity_data = player_entity_data
        self._get_use_rust = get_use_rust

    def check_enemy_bullets_vs_player(
        self,
        enemy_bullets: list[Bullet],
        player: Player,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable,
    ) -> bool:
        """Test enemy bullets against the player and apply damage on hit.

        Uses the Rust spatial hash when available; otherwise performs a
        linear scan. Deactivates the first hit bullet so it cannot
        damage the player again on the next frame.

        Args:
            enemy_bullets: Active enemy bullets to test.
            player: Player entity whose hitbox participates.
            calculate_damage_func: Callable converting raw damage to final.
            on_player_hit_func: Callable invoked with final damage and player.

        Returns:
            bool: True if at least one bullet hit the player.
        """
        player_hitbox = player.get_hitbox()

        if self._get_use_rust() and enemy_bullets:
            # Reference the parent module so test monkeypatches on
            # ``airwar.game.managers.collision_controller.batch_collide_bullets_vs_entities``
            # take effect. Attribute access on the module picks up patches at call time.
            from airwar.game.managers import collision_controller as _cc_module

            batch_collide = _cc_module.batch_collide_bullets_vs_entities

            # Use Rust spatial hash: build bullet data + single player entity
            eb_data = self._enemy_bullet_data
            eb_map = self._enemy_bullet_map
            eb_data.clear()
            eb_map.clear()
            for i, eb in enumerate(enemy_bullets):
                if eb.active and not getattr(eb, "held", False):
                    r = eb.rect
                    eb_data.append((i, float(r.left), float(r.top), float(r.width), float(r.height)))
                    eb_map[i] = eb

            if eb_data:
                self._player_entity_data.clear()
                self._player_entity_data.append(
                    (
                        -1,
                        float(player_hitbox.left),
                        float(player_hitbox.top),
                        float(player_hitbox.width),
                        float(player_hitbox.height),
                    )
                )
                hits = batch_collide(eb_data, self._player_entity_data, self._grid_cell_size)
                if hits:
                    bullet_id = hits[0][0]
                    eb = eb_map[bullet_id]
                    damage = calculate_damage_func(eb.data.damage)
                    on_player_hit_func(damage, player)
                    eb.active = False
                    return True
            return False

        # Python fallback: linear scan
        for eb in enemy_bullets:
            if eb.active and not getattr(eb, "held", False) and eb.rect.colliderect(player_hitbox):
                damage = calculate_damage_func(eb.data.damage)
                on_player_hit_func(damage, player)
                eb.active = False  # Deactivate bullet so it doesn't re-hit next frame
                return True

        return False
