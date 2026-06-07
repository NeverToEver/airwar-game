"""Boost / phase-dash tutorial stage (id ``boost_phase_dash``).

The stage spawns nothing on enter and has no per-frame logic of its
own -- the player fires via the generic pipeline and phase-dash is
triggered from input (``_handle_boost_tap``). The objective counter
advances from kill / boost-tap handlers, so :class:`BoostStage` is
a no-op placeholder.
"""

from __future__ import annotations

from .base import BaseStage

BOOST_STAGE_ID = "boost"


class BoostStage(BaseStage):
    """No-op stage. Boost / phase-dash logic lives in the scene's main update."""

    stage_id: str = BOOST_STAGE_ID

    def update(self) -> None:
        return


__all__ = ["BOOST_STAGE_ID", "BoostStage"]
