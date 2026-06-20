"""F08 god-class split: Mothership gatling turret subsystem.

This module extracts the gatling-turret specification, fire logic, and sweep
calculation from ``GameIntegrator``. The class constants ``MOTHERSHIP_GATLING_*``
and the ``GatlingTurretSpec`` NamedTuple live here; ``GameIntegrator`` keeps
matching class-level attributes that point at the same values so external
test code (``integrator.MOTHERSHIP_GATLING_TURRETS``) still works.

Backward compatibility:
- ``GatlingTurretSpec`` is re-exported from ``game_integrator.py``.
- All ``MOTHERSHIP_GATLING_*`` class constants remain accessible on the
  ``GameIntegrator`` class via re-export.
- The fire / sweep methods remain on ``GameIntegrator`` as 1-line forwarders.
- The integrator's ``_mothership_gatling_timer`` /
  ``_mothership_gatling_sweep_frame`` attributes are exposed as property
  forwarders to this component so existing tests can read/write them.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, NamedTuple

from airwar.entities.base import BulletData
from airwar.entities.bullet import Bullet

if TYPE_CHECKING:
    from .game_integrator import GameIntegrator


class GatlingTurretSpec(NamedTuple):
    """Specification for a mothership gatling turret."""

    name: str
    offset_x: float
    angle_min: float
    angle_max: float
    period: int
    phase_offset: int


# Gatling damage / cadence constants. Moved verbatim from GameIntegrator
# so the firing logic and tests have a single source of truth.
MOTHERSHIP_GATLING_DAMAGE = 24
MOTHERSHIP_GATLING_FIRE_RATE = 8
MOTHERSHIP_GATLING_BULLET_SPEED = 18
MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES = 120
MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES = 80
MOTHERSHIP_GATLING_OVERLAP_DEGREES = 40
MOTHERSHIP_GATLING_SWEEP_PERIOD = 96
MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD = 108
MOTHERSHIP_GATLING_BARREL_X_OFFSETS = (-56, 56)
MOTHERSHIP_GATLING_TURRETS = (
    GatlingTurretSpec("left", MOTHERSHIP_GATLING_BARREL_X_OFFSETS[0], -60.0, 20.0, MOTHERSHIP_GATLING_SWEEP_PERIOD, 0),
    GatlingTurretSpec(
        "right", MOTHERSHIP_GATLING_BARREL_X_OFFSETS[1], -20.0, 60.0, MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD, 21
    ),
)
MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET = -64
MOTHERSHIP_GATLING_BULLET_TYPE = "mothership_gatling"


class MothershipGatling:
    """F08 god-class split: gatling turret fire logic, sweep, bullet spawn.

    Holds the per-frame gatling sweep state (``sweep_frame``, ``fire_timer``)
    and owns the ``_fire_gatling_sweep`` / ``_current_gatling_sweep_angle``
    / ``_get_gatling_turret`` methods. The integrator keeps the
    ``_mothership_gatling_*`` attribute names as forwarders so existing
    tests (which read/write them directly) keep working.
    """

    def __init__(self, integrator: GameIntegrator) -> None:
        self._integrator = integrator
        # Use the legacy attribute names directly on the component. The
        # integrator exposes matching property forwarders so callers that
        # reach into ``integrator._mothership_gatling_*`` (e.g. tests) see
        # the same value.
        self._mothership_gatling_timer = 0
        self._mothership_gatling_sweep_frame = 0

    def tick(self) -> None:
        """Advance sweep + fire timers; emit a sweep volley when due."""
        self._mothership_gatling_sweep_frame += 1
        self._mothership_gatling_timer += 1
        if self._mothership_gatling_timer >= MOTHERSHIP_GATLING_FIRE_RATE:
            self._mothership_gatling_timer = 0
            self._fire_gatling_sweep()

    def reset_timers(self) -> None:
        """Clear sweep and fire timers (used on state reset)."""
        self._mothership_gatling_timer = 0
        self._mothership_gatling_sweep_frame = 0

    def _fire_gatling_sweep(self) -> None:
        if not self._integrator._game_scene or not self._integrator._get_mothership_targets():
            return
        if len(self._integrator._mothership_bullets) >= self._integrator.MOTHERSHIP_MAX_BULLETS:
            return

        mother_ship_pos = self._integrator._mother_ship.get_docking_position()
        for turret in MOTHERSHIP_GATLING_TURRETS:
            angle_rad = math.radians(self._current_gatling_sweep_angle(turret))
            vx = math.sin(angle_rad) * MOTHERSHIP_GATLING_BULLET_SPEED
            vy = -math.cos(angle_rad) * MOTHERSHIP_GATLING_BULLET_SPEED
            bullet = Bullet(
                mother_ship_pos[0] + turret.offset_x,
                mother_ship_pos[1] + MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET,
                BulletData(
                    damage=MOTHERSHIP_GATLING_DAMAGE,
                    speed=MOTHERSHIP_GATLING_BULLET_SPEED,
                    owner="mothership",
                    bullet_type=MOTHERSHIP_GATLING_BULLET_TYPE,
                ),
            )
            bullet.rect.width = 6
            bullet.rect.height = 14
            bullet.velocity.x = vx
            bullet.velocity.y = vy
            self._integrator._mothership_bullets.append(bullet)

    def _current_gatling_sweep_angle(self, turret: str | GatlingTurretSpec = "left") -> float:
        spec = self._get_gatling_turret(turret)
        period = max(2, spec.period)
        phase = ((self._mothership_gatling_sweep_frame + spec.phase_offset) % period) / period
        sweep_t = phase * 2 if phase <= 0.5 else (1.0 - phase) * 2
        return spec.angle_min + (spec.angle_max - spec.angle_min) * sweep_t

    @staticmethod
    def _get_gatling_turret(turret: str | GatlingTurretSpec) -> GatlingTurretSpec:
        if isinstance(turret, GatlingTurretSpec):
            return turret
        for spec in MOTHERSHIP_GATLING_TURRETS:
            if spec.name == turret:
                return spec
        return MOTHERSHIP_GATLING_TURRETS[0]


__all__ = [
    "MOTHERSHIP_GATLING_BARREL_X_OFFSETS",
    "MOTHERSHIP_GATLING_BULLET_SPEED",
    "MOTHERSHIP_GATLING_BULLET_TYPE",
    "MOTHERSHIP_GATLING_DAMAGE",
    "MOTHERSHIP_GATLING_FIRE_RATE",
    "MOTHERSHIP_GATLING_MUZZLE_Y_OFFSET",
    "MOTHERSHIP_GATLING_OVERLAP_DEGREES",
    "MOTHERSHIP_GATLING_RIGHT_SWEEP_PERIOD",
    "MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES",
    "MOTHERSHIP_GATLING_SWEEP_PERIOD",
    "MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES",
    "MOTHERSHIP_GATLING_TURRETS",
    "GatlingTurretSpec",
    "MothershipGatling",
]
