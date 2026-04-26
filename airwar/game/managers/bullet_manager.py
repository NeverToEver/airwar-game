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
import pygame

# Try to import Rust batch update function
try:
    from airwar.core_bindings import batch_update_bullets, RUST_AVAILABLE
except ImportError:
    batch_update_bullets = None
    RUST_AVAILABLE = False

from ...config import get_screen_height


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
        self._use_rust = RUST_AVAILABLE and batch_update_bullets is not None

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
        if self._use_rust:
            self._update_bullets_batch(self._player.get_bullets(), cleanup)
        else:
            for bullet in self._player.get_bullets():
                bullet.update()
        if cleanup:
            self._player.cleanup_inactive_bullets()

    def _update_enemy_bullets(self, cleanup: bool) -> None:
        """更新敌人子弹

        Args:
            cleanup: 是否在更新后清理非活跃子弹
        """
        if self._use_rust:
            self._update_bullets_batch(self._spawn_controller.enemy_bullets, cleanup)
        else:
            for bullet in self._spawn_controller.enemy_bullets:
                bullet.update()
        if cleanup:
            self._cleanup_enemy_bullets()

    def _update_bullets_batch(self, bullets: list, cleanup: bool) -> None:
        """Batch update bullets using Rust for position updates.

        Handles position updates and screen boundary checks in Rust,
        then applies results back. For laser bullets, still calls
        bullet.update() for trail management.

        Args:
            bullets: List of bullet entities
            cleanup: Whether to remove inactive bullets
        """
        if not bullets:
            return

        # Build bullet data for Rust: (id, x, y, vx, vy, bullet_type, is_laser, screen_height)
        # Use object id as unique identifier
        # bullet_type: 0=normal, 1=single, 2=laser (not used in current Rust impl)
        bullet_data = []
        bullet_map = {}
        for i, bullet in enumerate(bullets):
            if not bullet.active:
                continue
            bullet_id = id(bullet)
            vx = bullet.velocity.x
            vy = bullet.velocity.y
            is_laser = bullet.data.bullet_type == "laser" or bullet.data.is_laser
            bullet_data.append((
                bullet_id,
                bullet.rect.x,
                bullet.rect.y,
                vx,
                vy,
                0,  # bullet_type (reserved for future use)
                is_laser,
                float(get_screen_height())
            ))
            bullet_map[bullet_id] = bullet

        if not bullet_data:
            return

        # Call Rust batch update
        results = batch_update_bullets(bullet_data)

        # Apply results back to bullets
        for bullet_id, new_x, new_y, is_active in results:
            if bullet_id not in bullet_map:
                continue
            bullet = bullet_map[bullet_id]

            # Update position
            bullet.rect.x = new_x
            bullet.rect.y = new_y

            # Handle laser trail (still needs Python for pygame operations)
            if bullet.data.bullet_type == "laser" or bullet.data.is_laser:
                bullet._trail.append(pygame.Rect(
                    bullet.rect.x, bullet.rect.y,
                    bullet.rect.width, bullet.rect.height
                ))
                if len(bullet._trail) > 8:
                    bullet._trail.pop(0)

            # Update active state
            if not is_active:
                bullet.active = False

        # 注意：cleanup 由调用者处理
        # - 玩家子弹：由 Player.cleanup_inactive_bullets() 清理
        # - 敌人子弹：由 _cleanup_enemy_bullets() 清理

    def _cleanup_enemy_bullets(self) -> None:
        """清理敌人子弹列表中的非活跃子弹"""
        if not self._spawn_controller.enemy_bullets:
            return
        # Use in-place filter to preserve list reference for EnemyBulletSpawner
        self._spawn_controller.enemy_bullets[:] = [
            b for b in self._spawn_controller.enemy_bullets if b.active
        ]
