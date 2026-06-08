"""Boss subpackage.

Public surface (re-exported for callers):

* :class:`BossState`, :class:`BossStateMachine`, and enrage constants
  (defined in :mod:`.boss_state`)
* :class:`BossMovement` and movement tuning constants
  (defined in :mod:`.boss_movement`)
* :class:`BossAttackPatterns` and attack tuning constants
  (defined in :mod:`.boss_attack`)
* :class:`BossRenderer` (defined in :mod:`.boss_render`)

The :class:`Boss` class itself lives in
:mod:`airwar.entities.enemy.enemy` and holds one of each component above.
"""

from .boss import Boss, BossData
from .boss_attack import (
    AIM_BULLET_COUNT,
    AIM_DAMAGE_INCREMENT,
    ATTACK_DIRECTIONS,
    SPREAD_DAMAGE_INCREMENT,
    WAVE_BULLET_COUNT,
    BossAttackPatterns,
)
from .boss_movement import (
    AIM_DASH_DISTANCE,
    AIM_DASH_DURATION,
    AIM_DASH_MAX_DISTANCE_RATIO,
    AIM_DASH_PHASE_BONUS,
    CENTER_OFFSET,
    DEFAULT_PHASE_DURATION,
    ENTRY_SPEED,
    ESCAPE_DRIFT,
    LERP_FACTOR,
    MIN_Y,
    BossMovement,
)
from .boss_render import BossRenderer
from .boss_state import (
    ENRAGE_ATTACK_INTERVAL,
    ENRAGE_ATTACK_WINDUP,
    ENRAGE_BULLET_SPEED,
    ENRAGE_CORE_COLOR,
    ENRAGE_DANGER_COLOR,
    ENRAGE_DURATION,
    ENRAGE_EXIT_BACK_OFFSET,
    ENRAGE_LASER_SPEED,
    ENRAGE_MUZZLE_FLASH_DURATION,
    ENRAGE_MUZZLE_FLASH_PULSES,
    ENRAGE_MUZZLE_FORWARD_SCALE,
    ENRAGE_MUZZLE_SIDE_SCALE,
    ENRAGE_PATH_RADIUS_SCALE,
    ENRAGE_RELEASE_BULLET_SPEED,
    ENRAGE_RELEASE_HOLD_DURATION,
    ENRAGE_RELEASE_INTERVAL,
    ENRAGE_RELEASE_LASER_SPEED,
    ENRAGE_RETURN_DURATION,
    ENRAGE_SLOW_FACTOR,
    ENRAGE_SNAPSHOT_LASER_COUNT,
    ENRAGE_SNAPSHOT_RING_COUNT,
    ENRAGE_SQUARE_PATH_RATIO,
    ENRAGE_TRAIL_BLUR_PASSES,
    ENRAGE_TRAIL_FINAL_SCALE,
    ENRAGE_TRAIL_LENGTH,
    ENRAGE_TRAIL_RENDER_MAX,
    ENRAGE_TRAIL_SCALE,
    ENRAGE_TRAIL_TINT,
    ENRAGE_TRANSITION_DURATION,
    ENRAGE_TRIGGER_RATIO,
    BossState,
    BossStateMachine,
)
from .boss_sub_state import EnrageSubMachine

__all__ = [
    "AIM_BULLET_COUNT",
    "AIM_DAMAGE_INCREMENT",
    "AIM_DASH_DISTANCE",
    "AIM_DASH_DURATION",
    "AIM_DASH_MAX_DISTANCE_RATIO",
    "AIM_DASH_PHASE_BONUS",
    "ATTACK_DIRECTIONS",
    "CENTER_OFFSET",
    "DEFAULT_PHASE_DURATION",
    "ENRAGE_ATTACK_INTERVAL",
    "ENRAGE_ATTACK_WINDUP",
    "ENRAGE_BULLET_SPEED",
    "ENRAGE_CORE_COLOR",
    "ENRAGE_DANGER_COLOR",
    "ENRAGE_DURATION",
    "ENRAGE_EXIT_BACK_OFFSET",
    "ENRAGE_LASER_SPEED",
    "ENRAGE_MUZZLE_FLASH_DURATION",
    "ENRAGE_MUZZLE_FLASH_PULSES",
    "ENRAGE_MUZZLE_FORWARD_SCALE",
    "ENRAGE_MUZZLE_SIDE_SCALE",
    "ENRAGE_PATH_RADIUS_SCALE",
    "ENRAGE_RELEASE_BULLET_SPEED",
    "ENRAGE_RELEASE_HOLD_DURATION",
    "ENRAGE_RELEASE_INTERVAL",
    "ENRAGE_RELEASE_LASER_SPEED",
    "ENRAGE_RETURN_DURATION",
    "ENRAGE_SLOW_FACTOR",
    "ENRAGE_SNAPSHOT_LASER_COUNT",
    "ENRAGE_SNAPSHOT_RING_COUNT",
    "ENRAGE_SQUARE_PATH_RATIO",
    "ENRAGE_TRAIL_BLUR_PASSES",
    "ENRAGE_TRAIL_FINAL_SCALE",
    "ENRAGE_TRAIL_LENGTH",
    "ENRAGE_TRAIL_RENDER_MAX",
    "ENRAGE_TRAIL_SCALE",
    "ENRAGE_TRAIL_TINT",
    "ENRAGE_TRANSITION_DURATION",
    "ENRAGE_TRIGGER_RATIO",
    "ENTRY_SPEED",
    "ESCAPE_DRIFT",
    "LERP_FACTOR",
    "MIN_Y",
    "SPREAD_DAMAGE_INCREMENT",
    "WAVE_BULLET_COUNT",
    "Boss",
    "BossAttackPatterns",
    "BossData",
    "BossMovement",
    "BossRenderer",
    "BossState",
    "BossStateMachine",
    "EnrageSubMachine",
]
