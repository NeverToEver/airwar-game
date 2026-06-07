"""Enemy and Boss entities with movement patterns and attack behaviors.

Re-exports the public surface previously defined in
``airwar/entities/enemy.py``. The Boss implementation now lives in the
``boss/`` subpackage; this module preserves the legacy import path.
"""

from .enemy import (
    MOVEMENT_TYPE_MAP,
    Boss,
    BossData,
    EliteEnemy,
    EliteEnemyData,
    Enemy,
    EnemyData,
    EnemySpawner,
    EnemyState,
)

__all__ = [
    "MOVEMENT_TYPE_MAP",
    "Boss",
    "BossData",
    "EliteEnemy",
    "EliteEnemyData",
    "Enemy",
    "EnemyData",
    "EnemySpawner",
    "EnemyState",
]
