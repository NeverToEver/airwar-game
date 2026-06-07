"""Tutorial subpackage.

Houses the per-stage classes split out of :mod:`airwar.scenes.tutorial_scene`
plus the simulator/pool components added in Phase 4 Wave α.
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
from .tutorial_boss_sim import TutorialBoss as TutorialBossSimulator
from .tutorial_bullet_pool import TutorialBulletPool
from .tutorial_enemy_sim import TutorialEnemySim as TutorialEnemySimulator
from .tutorial_explosion_pool import TutorialExplosionPool
from .tutorial_player_sim import TutorialPlayer

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
    "TutorialBossSimulator",
    "TutorialBulletPool",
    "TutorialEnemySimulator",
    "TutorialExplosionPool",
    "TutorialPlayer",
    "build_stage",
]
