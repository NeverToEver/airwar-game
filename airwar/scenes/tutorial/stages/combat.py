"""Combat-basics tutorial stage (id ``combat_basics``).

Per-frame work: spawn a new easy enemy whenever the active count is
below 3 and the spawn budget isn't exhausted, paced to one wave per
38 frames. Extracted from
:meth:`TutorialScene._update_stage_logic` where it lived as an
inline ``elif self._stage.id == "combat_basics":`` branch.
"""

from __future__ import annotations

from .base import BaseStage

COMBAT_STAGE_ID = "combat"

#: Frames between successive easy-enemy spawn attempts while the
#: active count is below the lane cap and the spawn budget remains.
_SPAWN_INTERVAL_FRAMES: int = 38


class CombatStage(BaseStage):
    """Paces easy-enemy spawns until the stage objective is met."""

    stage_id: str = COMBAT_STAGE_ID

    def update(self) -> None:
        scene = self._scene
        if len(scene._enemies) >= 3:
            return
        if scene._stage_spawned >= scene._stage.objective_count:
            return
        if scene._animation_time % _SPAWN_INTERVAL_FRAMES != 0:
            return
        scene._spawn_easy_enemy_wave(initial=False)


__all__ = ["COMBAT_STAGE_ID", "CombatStage"]
