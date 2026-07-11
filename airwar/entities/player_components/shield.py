"""Player shield component.

Owns: shield duration timer, ``is_shielded`` flag, and the
shield-block damage check.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
The shield duration is decremented in ``update()``, which Player
calls once per frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.player import Player


class PlayerShield:
    """Shield timer and immunity flag.

    Args:
        owner: The Player instance (used so this component can set
            ``owner.is_shielded`` as a legacy alias).
    """

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self.is_shielded: bool = False
        self._shield_duration: int = 0

    def activate(self, duration: int) -> None:
        self.is_shielded = True
        self._shield_duration = max(1, duration)
        if hasattr(self._owner, "_state") and hasattr(self._owner._state, "activate_shield"):
            self._owner._state.activate_shield(duration)

    def is_active(self) -> bool:
        return self.is_shielded

    def update(self) -> None:
        if self._shield_duration > 0:
            self._shield_duration -= 1
            if self._shield_duration <= 0:
                self.is_shielded = False
                if hasattr(self._owner, "_state") and hasattr(self._owner._state, "deactivate_shield"):
                    self._owner._state.deactivate_shield()
