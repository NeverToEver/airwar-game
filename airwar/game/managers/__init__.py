"""游戏管理器模块

集中管理游戏相关的专业管理器组件，遵循单一职责原则。
各管理器负责特定领域的业务逻辑协调。

Manager Classes:
    BulletManager: 统一管理玩家子弹和敌人子弹的更新、碰撞和清理
    BossManager: 管理 Boss 生命周期、行为和战斗逻辑
    MilestoneManager: 处理里程碑触发和奖励选择流程
    InputCoordinator: 统一管理输入事件处理和投降系统
    UIManager: 统一管理游戏UI渲染
    GameLoopManager: 统一管理游戏主循环逻辑

Usage:
    from airwar.game.managers import BulletManager

    bullet_manager = BulletManager(player, spawn_controller)
    bullet_manager.update_all()
"""

from airwar.game.managers.bullet_manager import BulletManager
from airwar.game.managers.boss_manager import BossManager
from airwar.game.managers.milestone_manager import MilestoneManager
from airwar.game.managers.input_coordinator import InputCoordinator
from airwar.game.managers.ui_manager import UIManager
from airwar.game.managers.game_loop_manager import GameLoopManager
