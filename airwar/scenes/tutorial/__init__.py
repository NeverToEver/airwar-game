"""Tutorial subpackage.

Houses the per-stage classes split out of :mod:`airwar.scenes.tutorial_scene`.
"""

from .stages import (
    AIM_STAGE_ID,
    BOOST_STAGE_ID,
    BOSS_STAGE_ID,
    COMBAT_STAGE_ID,
    HOMECOMING_STAGE_ID,
    MOTHERSHIP_STAGE_ID,
    MOVEMENT_STAGE_ID,
    AimStage,
    BaseStage,
    BoostStage,
    BossStage,
    CombatStage,
    HomecomingBaseStage,
    MothershipDockingStage,
    MovementStage,
    build_stage,
)

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
