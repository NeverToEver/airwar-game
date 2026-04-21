"""子弹管理器模块

统一管理玩家子弹和敌人子弹的更新、清理和状态同步。
遵循单一职责原则，将子弹相关操作从 GameScene 中分离。

设计原则:
- 单一职责: 仅负责子弹生命周期管理
- 依赖注入: 通过构造函数接收依赖
- 门面模式: 提供统一的子弹操作入口
- 组合优于继承: 通过组合协调不同子弹类型

Usage:
    from airwar.game.managers import BulletManager

    bullet_manager = BulletManager(player, spawn_controller)
    bullet_manager.update_all()
"""

from typing import Protocol


class PlayerProtocol(Protocol):
    """玩家协议 - 定义玩家必须提供的子弹相关接口"""

    def get_bullets(self) -> list: ...
    def remove_bullet(self, bullet) -> None: ...


class SpawnControllerProtocol(Protocol):
    """生成控制器协议 - 定义敌人生成器必须提供的子弹相关接口"""

    @property
    def enemy_bullets(self) -> list: ...


class BulletManager:
    """子弹生命周期管理器

    统一管理玩家子弹和敌人子弹的:
    - 更新 (update)
    - 清理 (cleanup)
    - 清空 (clear)

    职责边界:
    - 管理子弹的更新和清理
    - 不负责碰撞检测 (由 CollisionController 负责)
    - 不负责子弹生成 (由 Player 和 SpawnController 负责)

    Attributes:
        _player: 玩家对象 (提供子弹获取和删除接口)
        _spawn_controller: 敌人生成控制器 (提供敌人子弹列表)
    """

    def __init__(
        self,
        player: PlayerProtocol,
        spawn_controller: SpawnControllerProtocol
    ) -> None:
        """初始化子弹管理器

        Args:
            player: 玩家对象，必须实现 PlayerProtocol
            spawn_controller: 敌人生成控制器，必须实现 SpawnControllerProtocol
        """
        self._player = player
        self._spawn_controller = spawn_controller

    def update_all(self) -> None:
        """更新所有子弹 (玩家子弹 + 敌人子弹)

        不执行清理操作，仅更新子弹位置和状态。
        用于正常游戏循环中的子弹更新。
        """
        self._update_player_bullets(cleanup=False)
        self._update_enemy_bullets(cleanup=False)

    def update_with_cleanup(self) -> None:
        """更新并清理所有子弹

        在更新子弹的同时，移除已非活跃的子弹。
        用于停靠状态或其他需要清理子弹的场景。
        """
        self._update_player_bullets(cleanup=True)
        self._update_enemy_bullets(cleanup=True)

    def cleanup(self) -> None:
        """清理非活跃的敌人子弹

        仅清理敌人子弹中的非活跃项。
        玩家子弹的清理由 Player.cleanup_inactive_bullets() 负责。
        """
        self._cleanup_enemy_bullets()

    def clear_enemy_bullets(self) -> None:
        """清空所有敌人子弹

        将所有敌人子弹标记为非活跃并清空列表。
        通常在 Boss 被击杀后调用。
        """
        for bullet in self._spawn_controller.enemy_bullets[:]:
            bullet.active = False
        self._spawn_controller.enemy_bullets.clear()

    def _update_player_bullets(self, cleanup: bool) -> None:
        """更新玩家子弹

        Args:
            cleanup: 是否在更新后清理非活跃子弹
        """
        for bullet in self._player.get_bullets():
            bullet.update()
            if cleanup and not bullet.active:
                self._player.remove_bullet(bullet)

    def _update_enemy_bullets(self, cleanup: bool) -> None:
        """更新敌人子弹

        Args:
            cleanup: 是否在更新后清理非活跃子弹
        """
        for bullet in self._spawn_controller.enemy_bullets:
            bullet.update()
        if cleanup:
            self._cleanup_enemy_bullets()

    def _cleanup_enemy_bullets(self) -> None:
        """清理敌人子弹列表中的非活跃子弹"""
        active_bullets = [
            bullet for bullet in self._spawn_controller.enemy_bullets
            if bullet.active
        ]
        self._spawn_controller.enemy_bullets.clear()
        self._spawn_controller.enemy_bullets.extend(active_bullets)
