"""F07-style component split: Enemy movement batch encoding.

This module extracts the 173-line ``Enemy.get_rust_batch_params``
method and its supporting helpers (Rust parameter configuration)
from the monolithic ``enemy.py`` (1532 lines). The encoding
function is now a module-level helper, and the Enemy class is a
thin caller.

Before: enemy.py 1532 lines, Enemy class ~570 lines, get_rust_batch_params 173 lines.
After:  enemy.py reduced by ~210 lines; this module is ~200 lines.

The Enemy class keeps a 1-line forwarder so callers don't change::

    def get_rust_batch_params(self):
        return encode_rust_movement_params(self)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.config.constants_access import get_game_constants

if TYPE_CHECKING:
    from .enemy import Enemy


# Movement pattern → Rust move_type_code (must match Rust enum in
# airwar_core/src/movement.rs). Defined here as a module-level constant
# shared by the encoder and Rust implementation.
MOVEMENT_TYPE_MAP: dict[str, int] = {
    "straight": 0,
    "sine": 1,
    "zigzag": 2,
    "dive": 3,
    "hover": 4,
    "spiral": 5,
    "noise": 6,
    "aggressive": 7,
}


# Timer scaling constant — must match the Rust multiplier. Kept as a
# module-level constant so the encoder is pure data.
HOVER_TIMER_RUST_SCALE: float = 60.0


# Default values for missing attributes (used as fallbacks when an
# enemy was constructed without all the optional movement fields).
DEFAULT_MOVE_AMPLITUDE: float = 0.0
DEFAULT_MOVE_FREQUENCY: float = 0.0
DEFAULT_MOVE_SPEED: float = 0.0
DEFAULT_NOISE_SPEED: float = 0.0
DEFAULT_AGGRESSIVE_SPEED: float = 0.0
DEFAULT_ZIGZAG_INTERVAL: int = 0
DEFAULT_SPIRAL_RADIUS: float = 0.0
DEFAULT_NOISE_SCALE_X: float = 0.0
DEFAULT_NOISE_SCALE_Y: float = 0.0
DEFAULT_NOISE_AMPLITUDE_X: float = 0.0
DEFAULT_NOISE_AMPLITUDE_Y: float = 0.0
DEFAULT_AGGRESSIVE_AMPLITUDE_X: float = 0.0
DEFAULT_AGGRESSIVE_AMPLITUDE_Y: float = 0.0


def encode_rust_movement_params(enemy: Enemy) -> tuple | tuple[None, None]:
    """Encode an Enemy's movement state into the Rust batch tuple pair.

    Returns ``(base_tuple, extra_tuple)`` matching the struct layout in
    ``airwar_core/src/movement.rs``:

        base  (12 fields):  move_type, timer, active_x, active_y,
                            move_range_x, move_range_y, offset, amplitude,
                            frequency, speed, direction, zigzag_interval
        extra (8 fields):   spiral_radius, current_x, current_y,
                            noise_scale_x, noise_scale_y,
                            noise_amplitude_x, noise_amplitude_y,
                            noise_seed

    Returns ``(None, None)`` if the enemy is not configured for batch
    movement (i.e. was constructed without ``_rust_move_type_code``).
    """
    if not hasattr(enemy, "_rust_move_type_code"):
        return None, None

    params = enemy._rust_params
    timer_attr = enemy._timer_attr
    timer = getattr(enemy, timer_attr, 0.0)
    if enemy.move_type == "hover":
        timer /= HOVER_TIMER_RUST_SCALE

    constants = get_game_constants()
    base = (
        enemy._rust_move_type_code,
        timer,
        enemy.active_position_x,
        enemy.active_position_y,
        float(constants.ENEMY.MOVE_RANGE_X),
        float(constants.ENEMY.MOVE_RANGE_Y),
        params["offset"],
        params["amplitude"],
        params["frequency"],
        params["speed"],
        params["direction"],
        params["zigzag_interval"],
    )
    extra = (
        params["spiral_radius"],
        enemy.rect.x,
        enemy.rect.y,
        params["noise_scale_x"],
        params["noise_scale_y"],
        params["noise_amplitude_x"],
        params["noise_amplitude_y"],
        params["noise_seed"],
    )
    return base, extra


def configure_rust_movement(enemy: Enemy) -> None:
    """Configure the enemy for batch Rust movement.

    This populates ``enemy._rust_move_type_code``, ``_rust_params``,
    and ``_timer_attr`` so subsequent calls to
    :func:`encode_rust_movement_params` can build the batch tuples.

    Idempotent: calling twice yields the same configuration.
    """
    enemy._rust_move_type_code = MOVEMENT_TYPE_MAP.get(enemy.move_type, 0)
    enemy._rust_params = _build_rust_params(enemy)
    if enemy.move_type == "hover":
        enemy._timer_attr = "hover_timer"
    elif enemy.move_type in ("zigzag", "dive", "spiral", "noise", "aggressive"):
        enemy._timer_attr = f"{enemy.move_type}_timer"
    else:
        enemy._timer_attr = "move_timer"


def _build_rust_params(enemy: Enemy) -> dict:
    """Build the ``_rust_params`` dict for an enemy.

    Centralizes the lookup of movement pattern parameters with
    appropriate defaults.
    """
    return {
        "offset": getattr(enemy, "move_offset", 0.0),
        "amplitude": getattr(enemy, "move_amplitude", DEFAULT_MOVE_AMPLITUDE),
        "frequency": _rust_frequency_param(enemy),
        "speed": _rust_speed_param(enemy),
        "direction": getattr(enemy, "direction", 1.0),
        "zigzag_interval": getattr(enemy, "zigzag_interval", DEFAULT_ZIGZAG_INTERVAL),
        "spiral_radius": getattr(enemy, "spiral_radius", DEFAULT_SPIRAL_RADIUS),
        "noise_scale_x": _rust_noise_param(enemy, "scale_x"),
        "noise_scale_y": _rust_noise_param(enemy, "scale_y"),
        "noise_amplitude_x": _rust_noise_param(enemy, "amplitude_x"),
        "noise_amplitude_y": _rust_noise_param(enemy, "amplitude_y"),
        "noise_seed": (
            getattr(enemy, "agg_seed", 0) if enemy.move_type == "aggressive" else getattr(enemy, "noise_seed", 0)
        ),
    }


def _rust_frequency_param(enemy: Enemy) -> float:
    if enemy.move_type == "spiral":
        return getattr(enemy, "spiral_frequency", DEFAULT_MOVE_FREQUENCY)
    return getattr(enemy, "move_frequency", DEFAULT_MOVE_FREQUENCY)


def _rust_speed_param(enemy: Enemy) -> float:
    if enemy.move_type == "zigzag":
        return getattr(enemy, "zigzag_speed", DEFAULT_MOVE_SPEED)
    if enemy.move_type == "noise":
        return getattr(enemy, "noise_speed", DEFAULT_NOISE_SPEED)
    if enemy.move_type == "aggressive":
        return getattr(enemy, "agg_speed", DEFAULT_AGGRESSIVE_SPEED)
    return getattr(enemy, "spiral_speed", DEFAULT_MOVE_SPEED)


def _rust_noise_param(enemy: Enemy, name: str) -> float:
    """Look up a noise/aggressive pattern parameter with fallbacks."""
    if enemy.move_type == "aggressive":
        defaults = {
            "scale_x": DEFAULT_NOISE_SCALE_X,
            "scale_y": DEFAULT_NOISE_SCALE_Y,
            "amplitude_x": DEFAULT_AGGRESSIVE_AMPLITUDE_X,
            "amplitude_y": DEFAULT_AGGRESSIVE_AMPLITUDE_Y,
        }
        return getattr(enemy, f"agg_{name}", defaults[name])

    defaults = {
        "scale_x": DEFAULT_NOISE_SCALE_X,
        "scale_y": DEFAULT_NOISE_SCALE_Y,
        "amplitude_x": DEFAULT_NOISE_AMPLITUDE_X,
        "amplitude_y": DEFAULT_NOISE_AMPLITUDE_Y,
    }
    return getattr(enemy, f"noise_{name}", defaults[name])


__all__ = [
    "DEFAULT_AGGRESSIVE_AMPLITUDE_X",
    "DEFAULT_AGGRESSIVE_AMPLITUDE_Y",
    "DEFAULT_AGGRESSIVE_SPEED",
    "DEFAULT_MOVE_AMPLITUDE",
    "DEFAULT_MOVE_FREQUENCY",
    "DEFAULT_MOVE_SPEED",
    "DEFAULT_NOISE_AMPLITUDE_X",
    "DEFAULT_NOISE_AMPLITUDE_Y",
    "DEFAULT_NOISE_SCALE_X",
    "DEFAULT_NOISE_SCALE_Y",
    "DEFAULT_NOISE_SPEED",
    "DEFAULT_SPIRAL_RADIUS",
    "DEFAULT_ZIGZAG_INTERVAL",
    "HOVER_TIMER_RUST_SCALE",
    "MOVEMENT_TYPE_MAP",
    "configure_rust_movement",
    "encode_rust_movement_params",
]
