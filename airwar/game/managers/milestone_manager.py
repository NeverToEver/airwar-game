"""里程碑管理器模块

统一管理里程碑触发和奖励选择流程。
遵循单一职责原则，将里程碑相关操作从 GameScene 中分离。

设计原则:
- 单一职责: 仅负责里程碑检查和奖励选择流程
- 依赖注入: 通过构造函数接收依赖
- 门面模式: 提供统一的里程碑操作入口

Usage:
    from airwar.game.managers import MilestoneManager

    milestone_manager = MilestoneManager(game_controller, reward_system)
    milestone_manager.set_reward_selector(reward_selector)
    milestone_manager.check_and_trigger(player)
"""

from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from airwar.game.managers.game_controller import GameController
    from airwar.game.systems.reward_system import RewardSystem
    from airwar.ui.reward_selector import RewardSelector

from .game_controller import GameplayState


class MilestoneManager:
    """里程碑触发和奖励选择流程管理器

    统一管理里程碑的:
    - 检查 (check_and_trigger)
    - 奖励选择回调 (on_reward_selected)

    职责边界:
    - 管理里程碑检查逻辑
    - 处理奖励选择回调
    - 不负责奖励生成 (由 RewardSystem 负责)
    - 不负责奖励渲染 (由 RewardSelector 负责)

    Attributes:
        _game_controller: 游戏控制器 (提供状态访问和游戏逻辑)
        _reward_system: 奖励系统 (提供奖励选项生成)
        _reward_selector: 奖励选择器 (用于显示和选择奖励)
        _on_reward_selected_callback: 奖励选择完成后的回调
    """

    def __init__(
        self,
        game_controller: 'GameController',
        reward_system: 'RewardSystem'
    ) -> None:
        """初始化里程碑管理器

        Args:
            game_controller: 游戏控制器
            reward_system: 奖励系统
        """
        self._game_controller = game_controller
        self._reward_system = reward_system
        self._reward_selector: Optional['RewardSelector'] = None
        self._on_reward_selected_callback: Optional[Callable] = None

    def set_reward_selector(self, reward_selector: 'RewardSelector') -> None:
        """设置奖励选择器

        Args:
            reward_selector: 奖励选择器实例
        """
        self._reward_selector = reward_selector

    def check_and_trigger(self, player) -> bool:
        """检查里程碑并触发奖励选择

        检查当前分数是否达到下一个里程碑阈值，
        如果达到则显示奖励选择界面。

        Args:
            player: 玩家对象 (用于奖励应用)

        Returns:
            bool: True 表示触发了里程碑，False 表示未触发
        """
        if self._game_controller.state.gameplay_state != GameplayState.PLAYING:
            return False

        threshold = self._game_controller.get_next_threshold()
        if self._game_controller.state.score >= threshold:
            self._trigger_reward_selection(player)
            return True
        return False

    def _trigger_reward_selection(self, player) -> None:
        """触发奖励选择流程

        Args:
            player: 玩家对象
        """
        boss_kill_count = self._game_controller.difficulty_manager.get_boss_kill_count()
        options = self._reward_system.generate_options(
            boss_kill_count,
            self._reward_system.unlocked_buffs
        )
        self._show_reward_selection(options, player)
        self._game_controller.state.paused = True

    def _show_reward_selection(self, options: list, player) -> None:
        """显示奖励选择器

        Args:
            options: 奖励选项列表
            player: 玩家对象 (用于回调)
        """
        if not self._reward_selector:
            return
        self._reward_selector.visible = True
        self._reward_selector.options = options
        self._reward_selector.selected_index = 0
        self._reward_selector.on_select = lambda reward: self._on_reward_selected(reward, player)

    def _on_reward_selected(self, reward: dict, player) -> None:
        """处理奖励选择回调

        Args:
            reward: 选择的奖励配置字典
            player: 玩家对象
        """
        self._game_controller.on_reward_selected(reward, player)
        if self._reward_selector:
            self._reward_selector.visible = False
        if self._on_reward_selected_callback:
            self._on_reward_selected_callback(reward)

    def set_on_reward_selected_callback(self, callback: Callable) -> None:
        """设置奖励选择完成后的回调

        Args:
            callback: 回调函数
        """
        self._on_reward_selected_callback = callback

    @property
    def is_reward_visible(self) -> bool:
        """检查奖励选择器是否可见

        Returns:
            bool: True 表示奖励选择器可见
        """
        return self._reward_selector.visible if self._reward_selector else False
