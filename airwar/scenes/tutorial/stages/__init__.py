"""Per-stage classes for the playable tutorial scene.

Each class owns the per-frame logic for one of the seven stages
listed in :data:`airwar.config.TUTORIAL_STAGES`. The
:func:`build_stage` factory maps a tutorial ``stage_id`` to the right
:class:`BaseStage` subclass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .aim import AIM_STAGE_ID, AimStage
from .base import BaseStage
from .boost import BOOST_STAGE_ID, BoostStage
from .boss import BOSS_STAGE_ID, BossStage
from .combat import COMBAT_STAGE_ID, CombatStage
from .homecoming_base import HOMECOMING_STAGE_ID, HomecomingBaseStage
from .mothership_docking import MOTHERSHIP_STAGE_ID, MothershipDockingStage
from .movement import MOVEMENT_STAGE_ID, MovementStage

if TYPE_CHECKING:
    from ..tutorial_scene import TutorialScene


#: Maps a tutorial stage ``id`` to the :class:`BaseStage` subclass
#: that drives its per-frame logic. Stages whose configured id differs
#: from the legacy dispatch id (e.g. ``"movement_aiming"`` vs the
#: coordinator's ``"movement"``) are listed under their configured
#: id here; the dispatch table in
#: The dispatch table below maps stage ids to stage classes.
_STAGE_CLASS_BY_ID: dict[str, type[BaseStage]] = {
    "movement_aiming": MovementStage,
    "boost_phase_dash": BoostStage,
    "combat_basics": CombatStage,
    "mothership_docking": MothershipDockingStage,
    "homecoming_base": HomecomingBaseStage,
    "boss_encounter": BossStage,
    "tutorial_complete": AimStage,  # summary stage uses AimStage as placeholder
}


def build_stage(stage_id: str, scene: TutorialScene) -> BaseStage:
    """Construct the :class:`BaseStage` for a tutorial stage id.

    Raises:
        KeyError: if ``stage_id`` is not in the registry (fail-fast on typos).
    """
    cls = _STAGE_CLASS_BY_ID[stage_id]
    return cls(scene)


__all__ = [
    "AIM_STAGE_ID",
    "BOOST_STAGE_ID",
    "BOSS_STAGE_ID",
    "COMBAT_STAGE_ID",
    "HOMECOMING_STAGE_ID",
    "MOTHERSHIP_STAGE_ID",
    "MOVEMENT_STAGE_ID",
    "AimStage",
    "BaseStage",
    "BoostStage",
    "BossStage",
    "CombatStage",
    "HomecomingBaseStage",
    "MothershipDockingStage",
    "MovementStage",
    "build_stage",
]
