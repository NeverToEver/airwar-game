"""Boss管理器模块

统一管理 Boss 的生命周期、行为和战斗逻辑。
遵循单一职责原则，将 Boss 相关操作从 GameScene 中分离。

设计原则:
- 单一职责: 仅负责 Boss 生命周期和战斗逻辑
- 依赖注入: 通过构造函数接收依赖
- 门面模式: 提供统一的 Boss 操作入口
- 组合优于继承: 通过协调不同组件实现功能

Usage:
    from airwar.game.managers import BossManager

    boss_manager = BossManager(spawn_controller, game_controller, reward_system, bullet_manager)
    boss_manager.update(player)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.game.managers.spawn_controller import SpawnController
    from airwar.game.managers.game_controller import GameController
    from airwar.game.systems.reward_system import RewardSystem
    from airwar.game.managers import BulletManager


class BossManager:
    """Boss 生命周期和战斗逻辑管理器

    统一管理 Boss 的:
    - 移动更新 (update)
    - 逃跑处理 (escape handling)
    - 击杀回调 (hit callback)
    - 玩家碰撞 (player collision)

    职责边界:
    - 管理 Boss 的移动和状态更新
    - 处理 Boss 击杀后的分数结算和奖励
    - 不负责 Boss 生成 (由 SpawnController 负责)
    - 不负责碰撞检测 (由 CollisionController 负责)

    Attributes:
        _spawn_controller: 敌人生成控制器 (提供 Boss 实例和敌人列表)
        _game_controller: 游戏控制器 (提供状态访问和通知)
        _reward_system: 奖励系统 (提供吸血效果)
        _bullet_manager: 子弹管理器 (提供敌人子弹清空)
    """

    def __init__(
        self,
        spawn_controller: 'SpawnController',
        game_controller: 'GameController',
        reward_system: 'RewardSystem',
        bullet_manager: 'BulletManager'
    ) -> None:
        """初始化 Boss 管理器

        Args:
            spawn_controller: 敌人生成控制器
            game_controller: 游戏控制器
            reward_system: 奖励系统
            bullet_manager: 子弹管理器
        """
        self._spawn_controller = spawn_controller
        self._game_controller = game_controller
        self._reward_system = reward_system
        self._bullet_manager = bullet_manager
        self._player = None

    def update(self, player) -> None:
        """更新 Boss 状态

        调用时机: 在敌人生成更新流程中调用

        Args:
            player: 玩家对象，用于计算追踪位置
        """
        self._player = player
        boss = self._spawn_controller.boss
        if not boss:
            return

        self._update_boss_movement(boss, player)
        self._handle_boss_escape(boss)

    def _update_boss_movement(self, boss, player) -> None:
        """更新 Boss 移动

        Args:
            boss: Boss 实例
            player: 玩家对象
        """
        player_pos = (player.rect.centerx, player.rect.centery)
        enemies = self._spawn_controller.enemies
        boss.update(enemies, player_pos=player_pos)

    def _handle_boss_escape(self, boss) -> None:
        """处理 Boss 逃跑

        当 Boss 存活但逃离时，显示逃跑通知。

        Args:
            boss: Boss 实例
        """
        if not boss or boss.active:
            return

        if boss.is_escaped():
            self._game_controller.show_notification("BOSS ESCAPED! (+0)")

    def on_boss_hit(self, score: int) -> None:
        """处理 Boss 被击中回调

        当 Boss 被玩家子弹击中时调用。
        更新分数、检查是否击杀、处理击杀奖励。

        Args:
            score: 击中获得的分数
        """
        self._game_controller.state.score += score
        self._game_controller.show_notification(f"+{score} BOSS SCORE!")

        if not self._spawn_controller.boss.active:
            self._on_boss_killed()

    def _on_boss_killed(self) -> None:
        """处理 Boss 被击杀

        执行:
        1. 应用吸血效果
        2. 清空敌人子弹
        """
        boss = self._spawn_controller.boss
        if boss and self._player:
            self._reward_system.apply_lifesteal(self._player, boss.data.score)
        self._bullet_manager.clear_enemy_bullets()

    @property
    def has_boss(self) -> bool:
        """检查当前是否有活跃的 Boss

        Returns:
            bool: True 表示有 Boss
        """
        return self._spawn_controller.boss is not None

    @property
    def boss(self):
        """获取当前 Boss 实例

        Returns:
            Boss 实例或 None
        """
        return self._spawn_controller.boss
