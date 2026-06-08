"""Per-buff apply strategies used by :class:`RewardSystem`.

Phase 5-δ extraction: this module owns the per-buff-type apply functions
that previously lived as private methods on ``RewardSystem``. They are
keyed by buff name in :data:`BUFF_APPLY_HANDLERS` and dispatched by
:class:`RewardSystem.reapply_all_effects`.

The handlers mutate the player and a small ``BuffApplyContext`` that
exposes the reward system's current state. They are kept module-level
(no class) so the strategy table reads as data.

Public surface:
    - :data:`BUFF_APPLY_HANDLERS` -- ``dict[str, Callable[[BuffApplyContext, Any], None]]``
    - :class:`BuffApplyContext` -- mutable context passed to each handler
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from airwar.game.buffs.buff_registry import create_buff
from airwar.game.constants import GAME_CONSTANTS

if TYPE_CHECKING:
    from airwar.game.buffs.base_buff import Buff


@dataclass
class BuffApplyContext:
    """Mutable state passed to each buff apply handler.

    The context is rebuilt by :class:`RewardSystem` once per apply call
    and read+written by the strategy functions. Keeping it explicit
    avoids the per-handler dance of poking private attributes on the
    coordinator.
    """

    buff_levels: dict[str, int]
    base_bullet_damage: int
    base_fire_cooldown: int
    base_boost_recovery_rate: float
    active_buffs: dict[str, Buff]
    slow_factor: float = 1.0


# ---------------------------------------------------------------------------
# Per-buff apply strategies.  Each function is a thin closure over
# ``ctx`` and ``player``; they share the same signature so they can sit in
# a flat strategy table.
# ---------------------------------------------------------------------------


def _apply_power_shot(ctx: BuffApplyContext, player: Any) -> None:
    level = ctx.buff_levels.get("Power Shot", 0)
    buff = create_buff("Power Shot")
    player.bullet_damage = buff.calculate_value(ctx.base_bullet_damage, level)


def _apply_rapid_fire(ctx: BuffApplyContext, player: Any) -> None:
    level = ctx.buff_levels.get("Rapid Fire", 0)
    buff = create_buff("Rapid Fire")
    if hasattr(player, "fire_interval"):
        player.fire_interval = buff.calculate_value(ctx.base_fire_cooldown, level)
    else:
        player.fire_cooldown = buff.calculate_value(ctx.base_fire_cooldown, level)


def _apply_piercing(ctx: BuffApplyContext, player: Any) -> None:
    player.pierce_count = ctx.buff_levels.get("Piercing", 0)


def _apply_spread_shot(ctx: BuffApplyContext, player: Any) -> None:
    if ctx.buff_levels.get("Spread Shot", 0) > 0:
        player.activate_shotgun()


def _apply_explosive(ctx: BuffApplyContext, player: Any) -> None:
    if ctx.buff_levels.get("Explosive", 0) > 0:
        player.activate_explosive()


def _apply_laser(ctx: BuffApplyContext, player: Any) -> None:
    if ctx.buff_levels.get("Laser", 0) > 0:
        player.activate_laser(GAME_CONSTANTS.REWARD.LASER_DURATION)


def _apply_armor(ctx: BuffApplyContext, player: Any) -> None:
    pass


def _apply_evasion(ctx: BuffApplyContext, player: Any) -> None:
    pass


def _apply_slow_field(ctx: BuffApplyContext, player: Any) -> None:
    ctx.slow_factor = 0.8


def _apply_boost_recovery(ctx: BuffApplyContext, player: Any) -> None:
    level = ctx.buff_levels.get("Boost Recovery", 0)
    player.boost_recovery_rate = ctx.base_boost_recovery_rate * (1.5**level)


def _apply_phase_dash(ctx: BuffApplyContext, player: Any) -> None:
    buff = create_buff("Phase Dash")
    buff.apply(player)


def _apply_mothership_recall(ctx: BuffApplyContext, player: Any) -> None:
    level = ctx.buff_levels.get("Mothership Recall", 0)
    player.mothership_cooldown_mult = 0.5**level


def _apply_extra_life(ctx: BuffApplyContext, player: Any) -> None:
    from airwar.game.systems.reward_system import RewardSystem  # lazy: avoid cycle

    player.max_health += RewardSystem.EXTRA_LIFE_BONUS_HP
    player.health = min(player.health + RewardSystem.EXTRA_LIFE_HEAL, player.max_health)


# The strategy table.  Order matches the previous ``_init_buff_apply_handlers``
# to keep diff small; future splits can sort by category.
BUFF_APPLY_HANDLERS: dict[str, Callable[[BuffApplyContext, Any], None]] = {
    "Power Shot": _apply_power_shot,
    "Rapid Fire": _apply_rapid_fire,
    "Piercing": _apply_piercing,
    "Spread Shot": _apply_spread_shot,
    "Explosive": _apply_explosive,
    "Laser": _apply_laser,
    "Armor": _apply_armor,
    "Evasion": _apply_evasion,
    "Slow Field": _apply_slow_field,
    "Boost Recovery": _apply_boost_recovery,
    "Phase Dash": _apply_phase_dash,
    "Mothership Recall": _apply_mothership_recall,
    "Extra Life": _apply_extra_life,
}


__all__ = [
    "BUFF_APPLY_HANDLERS",
    "BuffApplyContext",
]
