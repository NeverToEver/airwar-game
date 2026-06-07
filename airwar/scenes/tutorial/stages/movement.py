"""Movement / aiming tutorial stage (id ``movement_aiming``).

This stage is the *first* one in the configured sequence (stage id
``movement_aiming``). The legacy coordinator dispatch id was
``"movement"``; we keep that as :data:`MOVEMENT_STAGE_ID` for backwards
compatibility with the existing string-keyed table.

The stage has no per-frame logic of its own -- it relies on the
generic aim-assist + player + enemies pipeline (which the scene drives
outside the stage dispatch). So :class:`MovementStage` is a no-op
placeholder; the completion check (``_stage_progress`` vs.
``objective_count``) is owned by the scene.
"""

from __future__ import annotations

from .base import BaseStage

MOVEMENT_STAGE_ID = "movement"


class MovementStage(BaseStage):
    """No-op stage. Movement / aiming logic lives in the scene's main update."""

    stage_id: str = MOVEMENT_STAGE_ID

    def update(self) -> None:
        return  # scene owns this stage's per-frame work


__all__ = ["MOVEMENT_STAGE_ID", "MovementStage"]
