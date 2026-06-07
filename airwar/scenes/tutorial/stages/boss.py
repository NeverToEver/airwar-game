"""Boss-encounter tutorial stage (id ``boss_encounter``).

Per-frame work: count down the post-kill escape timer. Once the
``ESCAPE_FRAMES`` countdown reaches zero the stage progress flips to
``1`` so the scene's completion check sees the objective as met.
The actual boss entity is updated by the scene's main pipeline
(``_update_boss``), not the stage.
"""

from __future__ import annotations

from .base import BaseStage

BOSS_STAGE_ID = "boss"


class BossStage(BaseStage):
    """Per-frame boss-encounter stage logic (escape timer)."""

    stage_id: str = BOSS_STAGE_ID

    def update(self) -> None:
        scene = self._scene
        if scene._boss is not None or scene._escape_timer <= 0:
            return
        scene._escape_timer -= 1
        if scene._escape_timer <= 0:
            scene._stage_progress = 1


__all__ = ["BOSS_STAGE_ID", "BossStage"]
