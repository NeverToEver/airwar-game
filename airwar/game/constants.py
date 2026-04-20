"""游戏常量定义模块

集中管理所有游戏相关的常量值，避免魔法数字散落在代码各处。
遵循架构标准:
- 单一职责: 仅定义游戏常量
- 可扩展性: 使用dataclass支持继承扩展
- 可维护性: 集中管理，易于修改

Usage:
    from airwar.game.constants import GAME_CONSTANTS, PlayerConstants
    
    # Access player constants
    player_y = PlayerConstants.INITIAL_Y
    
    # Access damage constants
    boss_damage = GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE
    
    # Calculate threshold
    threshold = GAME_CONSTANTS.get_next_threshold(0, 'medium')
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class PlayerConstants:
    """玩家相关常量
    
    Attributes:
        INITIAL_X_OFFSET: 玩家初始X偏移量
        INITIAL_Y: 玩家初始Y位置
        FINAL_Y: 玩家最终Y位置
        SCREEN_BOTTOM_OFFSET: 屏幕底部偏移量
        INVINCIBILITY_DURATION: 无敌持续时间（帧）
        MOTHERSHIP_Y_POSITION: 母舰状态时玩家Y位置
        DEFAULT_SCREEN_WIDTH: 默认屏幕宽度
    """
    INITIAL_X_OFFSET: int = 25
    INITIAL_Y: int = -80
    FINAL_Y: int = -100
    SCREEN_BOTTOM_OFFSET: int = 100
    INVINCIBILITY_DURATION: int = 90
    MOTHERSHIP_Y_POSITION: int = 200
    DEFAULT_SCREEN_WIDTH: int = 800


@dataclass(frozen=True)
class DamageConstants:
    """伤害相关常量
    
    Attributes:
        BOSS_COLLISION_DAMAGE: Boss碰撞伤害值
        ENEMY_COLLISION_DAMAGE: 敌人碰撞伤害值
        EXPLOSIVE_DAMAGE: 爆炸基础伤害值
        DEFAULT_REGEN_RATE: 默认生命恢复速率
        REGEN_THRESHOLD: 生命恢复阈值
    """
    BOSS_COLLISION_DAMAGE: int = 30
    ENEMY_COLLISION_DAMAGE: int = 20
    EXPLOSIVE_DAMAGE: int = 30
    DEFAULT_REGEN_RATE: int = 2
    REGEN_THRESHOLD: int = 60


@dataclass(frozen=True)
class AnimationConstants:
    """动画相关常量
    
    Attributes:
        ENTRANCE_DURATION: 入场动画持续时间（帧）
        RIPPLE_INITIAL_RADIUS: 波动效果初始半径
        RIPPLE_INITIAL_ALPHA: 波动效果初始透明度
        NOTIFICATION_DECAY_RATE: 通知衰减速率
    """
    ENTRANCE_DURATION: int = 60
    RIPPLE_INITIAL_RADIUS: int = 15
    RIPPLE_INITIAL_ALPHA: int = 350
    NOTIFICATION_DECAY_RATE: int = 1


@dataclass(frozen=True)
class GameBalanceConstants:
    """游戏平衡相关常量
    
    Attributes:
        MAX_CYCLES: 最大周期数
        BASE_THRESHOLDS: 基础阈值列表
        CYCLE_MULTIPLIER: 周期倍率
        DIFFICULTY_MULTIPLIERS: 难度倍率元组 (easy, medium, hard)
    """
    MAX_CYCLES: int = 10
    BASE_THRESHOLDS: Tuple[int, ...] = (1000, 2500, 5000, 10000, 20000)
    CYCLE_MULTIPLIER: float = 1.5
    DIFFICULTY_MULTIPLIERS: Tuple[float, float, float] = (1.0, 1.5, 2.0)


@dataclass
class GameConstants:
    """游戏全局常量聚合类
    
    使用组合模式聚合各类常量，提供统一的访问入口。
    
    Attributes:
        PLAYER: 玩家相关常量
        DAMAGE: 伤害相关常量
        ANIMATION: 动画相关常量
        BALANCE: 游戏平衡相关常量
    
    Methods:
        get_difficulty_multiplier(difficulty: str) -> float:
            获取难度对应的分数倍率
        get_next_threshold(milestone_index: int, difficulty: str) -> float:
            计算下一个里程碑阈值
    """
    PLAYER: PlayerConstants = field(default_factory=PlayerConstants)
    DAMAGE: DamageConstants = field(default_factory=DamageConstants)
    ANIMATION: AnimationConstants = field(default_factory=AnimationConstants)
    BALANCE: GameBalanceConstants = field(default_factory=GameBalanceConstants)
    
    def get_difficulty_multiplier(self, difficulty: str) -> float:
        """获取难度对应的分数倍率
        
        Args:
            difficulty: 难度等级 ('easy', 'medium', 'hard')
        
        Returns:
            分数倍率 (easy=1.0, medium=1.5, hard=2.0)
        """
        multipliers = {
            'easy': self.BALANCE.DIFFICULTY_MULTIPLIERS[0],
            'medium': self.BALANCE.DIFFICULTY_MULTIPLIERS[1],
            'hard': self.BALANCE.DIFFICULTY_MULTIPLIERS[2],
        }
        return multipliers.get(difficulty, 1.0)
    
    def get_next_threshold(self, milestone_index: int, difficulty: str) -> float:
        """计算下一个里程碑阈值
        
        Args:
            milestone_index: 里程碑索引
            difficulty: 难度等级
        
        Returns:
            下一个里程碑的分数阈值
        """
        base_idx = milestone_index % len(self.BALANCE.BASE_THRESHOLDS)
        cycle_bonus = milestone_index // len(self.BALANCE.BASE_THRESHOLDS)
        base = self.BALANCE.BASE_THRESHOLDS[base_idx]
        multiplier = self.BALANCE.CYCLE_MULTIPLIER ** cycle_bonus
        difficulty_mult = self.get_difficulty_multiplier(difficulty)
        return base * multiplier * difficulty_mult


GAME_CONSTANTS = GameConstants()
