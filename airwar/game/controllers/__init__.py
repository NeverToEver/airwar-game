"""Controller 层兼容层

本模块已废弃，所有功能已迁移到 game.managers。
保留此模块用于向后兼容，新代码应直接导入 game.managers。

预计删除时间：下一个主要版本发布后
"""

from airwar.game.managers import (
    GameController, GameState,
    SpawnController,
    CollisionController, CollisionResult,
)

__all__ = [
    'GameController', 'GameState',
    'SpawnController',
    'CollisionController', 'CollisionResult',
]
