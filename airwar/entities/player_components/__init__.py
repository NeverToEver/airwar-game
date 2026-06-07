"""Player components subpackage (Phase 4 W-delta).

Extracted from the 755-line Player god class. Each component owns
state and behavior for one of seven responsibilities:

* :class:`PlayerMovement`     -- position update, ctrl/precision mode
* :class:`PlayerWeapon`       -- bullet pool, fire/auto_fire, weapon mods
* :class:`PlayerBoost`        -- boost energy, recovery, ramp
* :class:`PlayerShield`       -- shield timer, immunity
* :class:`PlayerPhaseDash`    -- phase dash state machine (incl. enum)
* :class:`PlayerAim`          -- facing angle, rotated sprite cache
* :class:`PlayerHitbox`       -- hitbox rect, glow surface, alpha pulse

The :class:`airwar.entities.player.Player` class is now a thin
coordinator that assembles these seven components and forwards every
public method to the right one.

Backward compatibility is preserved: the 40 public methods on Player
continue to work as 1-line forwarders, and all 30+ property reads
(``player.bullet_damage``, ``player.boost_max``, ``player.health``,
``player.is_phase_dash_enabled``, etc.) are exposed as Player-level
attributes/properties that delegate to the matching component.
"""

from .aim import PlayerAim
from .boost import PlayerBoost
from .hitbox import PlayerHitbox
from .movement import PlayerMovement
from .phase_dash import PhaseDashState, PlayerPhaseDash
from .shield import PlayerShield
from .weapon import PlayerWeapon

__all__ = [
    "PhaseDashState",
    "PlayerAim",
    "PlayerBoost",
    "PlayerHitbox",
    "PlayerMovement",
    "PlayerPhaseDash",
    "PlayerShield",
    "PlayerWeapon",
]
