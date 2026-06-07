"""Aim-only tutorial stage (id ``aim``).

The legacy coordinator's dispatch table lists an ``"aim"`` entry even
though no configured stage uses that id. The scene never activated
this branch, so :class:`AimStage` is a no-op placeholder that keeps
the dispatch contract intact.
"""

from __future__ import annotations

from .base import BaseStage

AIM_STAGE_ID = "aim"


class AimStage(BaseStage):
    """No-op stage. Kept for backwards compatibility with the dispatch table."""

    stage_id: str = AIM_STAGE_ID

    def update(self) -> None:
        return


__all__ = ["AIM_STAGE_ID", "AimStage"]
