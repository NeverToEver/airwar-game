"""Phase 4 god-class split: boss body vs player collision strategy.

Extracted from ``CollisionController``. Owns the boss-body vs player
hitbox test, including the "skip during entering animation" rule.

This is the simplest of the three collision kinds — no spatial hashing
or Rust path is involved. Kept as its own module to maintain symmetry
with the bullet-based strategies and to make the responsibility
boundaries clear in ``collision_controller.py``.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ...constants import GAME_CONSTANTS

if TYPE_CHECKING:
    from airwar.entities.enemy import Boss
    from airwar.entities.player import Player


class BossVsPlayerStrategy:
    """Strategy: boss body vs player body."""

    def check_boss_vs_player(
        self,
        boss: Boss,
        player: Player,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable,
    ) -> bool:
        """Test whether the boss body collides with the player.

        Skips the check while the boss is in its entering animation to
        avoid applying damage before it has settled into the playfield.

        Args:
            boss: Active boss entity to test against.
            player: Player entity whose hitbox participates.
            calculate_damage_func: Callable converting raw damage to final.
            on_player_hit_func: Callable invoked with final damage and player.

        Returns:
            bool: True if the boss hitbox overlaps the player hitbox.
        """
        if boss and boss.active and not boss.is_entering:
            player_hitbox = player.get_hitbox()
            if boss.get_hitbox().colliderect(player_hitbox):
                damage = calculate_damage_func(GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE)
                on_player_hit_func(damage, player)
                return True

        return False
