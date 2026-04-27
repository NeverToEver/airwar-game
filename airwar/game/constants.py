"""Game constants definition module.

Centralizes all game-related constant values to avoid magic numbers scattered
throughout the codebase. Follows architectural standards:
- Single Responsibility: Only defines game constants
- Extensibility: Uses dataclass to support inheritance extension
- Maintainability: Centralized management for easy modification

Usage:
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
    """Player-related constants.

    Attributes:
        INITIAL_X_OFFSET: Initial X offset for player spawn.
        INITIAL_Y: Initial Y position for player.
        FINAL_Y: Final Y position for player.
        SCREEN_BOTTOM_OFFSET: Offset from screen bottom.
        INVINCIBILITY_DURATION: Invincibility duration in frames.
        MOTHERSHIP_Y_POSITION: Player Y position when docked with mothership.
        DEFAULT_SCREEN_WIDTH: Default screen width.
        MAX_HEALTH: Maximum player health.
        SPEED: Player movement speed.
        BULLET_DAMAGE: Player bullet damage.
        FIRE_COOLDOWN: Fire cooldown in frames.
    """
    INITIAL_X_OFFSET: int = 25
    INITIAL_Y: int = -80
    FINAL_Y: int = -100
    SCREEN_BOTTOM_OFFSET: int = 100
    INVINCIBILITY_DURATION: int = 90
    MOTHERSHIP_Y_POSITION: int = 200
    DEFAULT_SCREEN_WIDTH: int = 800
    MAX_HEALTH: int = 100
    SPEED: int = 7
    BULLET_SPEED: int = 14
    BULLET_DAMAGE: int = 10
    FIRE_COOLDOWN: int = 8


@dataclass(frozen=True)
class DamageConstants:
    """Damage-related constants.

    Attributes:
        BOSS_COLLISION_DAMAGE: Damage from boss collision.
        ENEMY_COLLISION_DAMAGE: Damage from enemy collision.
        EXPLOSIVE_DAMAGE: Base explosive damage.
        DEFAULT_REGEN_RATE: Default health regeneration rate.
        REGEN_THRESHOLD: Health threshold for regeneration.
        INSTANT_KILL: Instant kill damage value (used for surrender).
    """
    BOSS_COLLISION_DAMAGE: int = 30
    ENEMY_COLLISION_DAMAGE: int = 20
    EXPLOSIVE_DAMAGE: int = 30
    DEFAULT_REGEN_RATE: int = 2
    REGEN_THRESHOLD: int = 60
    INSTANT_KILL: int = 9999


@dataclass(frozen=True)
class TimingConstants:
    """Timing-related constants.

    Attributes:
        FIXED_DELTA_TIME: Fixed frame time step (~16.67ms @60fps).
        NOTIFICATION_DURATION: Notification display duration in frames.
        NOTIFICATION_ALPHA_THRESHOLD: Alpha threshold for notification color change.
    """
    FIXED_DELTA_TIME: float = 1 / 60
    NOTIFICATION_DURATION: int = 90
    NOTIFICATION_ALPHA_THRESHOLD: int = 150


@dataclass(frozen=True)
class AnimationConstants:
    """Animation-related constants.

    Attributes:
        ENTRANCE_DURATION: Entrance animation duration in frames.
        RIPPLE_INITIAL_RADIUS: Ripple effect initial radius.
        RIPPLE_INITIAL_ALPHA: Ripple effect initial alpha.
        NOTIFICATION_DECAY_RATE: Notification decay rate.
        PARTICLE_ALPHA_VISIBILITY_THRESHOLD: Minimum alpha for particle visibility.
        PARTICLE_SIZE_THRESHOLD_LARGE: Large particle size threshold.
        PARTICLE_SIZE_THRESHOLD_MEDIUM: Medium particle size threshold.
        PARTICLE_SIZE_THRESHOLD_SMALL: Small particle size threshold.
        PARTICLE_BASE_SIZE_LARGE: Base texture size for large particles.
        PARTICLE_BASE_SIZE_MEDIUM: Base texture size for medium particles.
        PARTICLE_BASE_SIZE_SMALL: Base texture size for small particles.
        PARTICLE_BASE_SIZE_TINY: Base texture size for tiny particles.
    """
    ENTRANCE_DURATION: int = 60
    RIPPLE_INITIAL_RADIUS: int = 15
    RIPPLE_INITIAL_ALPHA: int = 350
    NOTIFICATION_DECAY_RATE: int = 1
    PARTICLE_ALPHA_VISIBILITY_THRESHOLD: int = 10
    PARTICLE_SIZE_THRESHOLD_LARGE: int = 18
    PARTICLE_SIZE_THRESHOLD_MEDIUM: int = 14
    PARTICLE_SIZE_THRESHOLD_SMALL: int = 10
    PARTICLE_BASE_SIZE_LARGE: int = 20
    PARTICLE_BASE_SIZE_MEDIUM: int = 16
    PARTICLE_BASE_SIZE_SMALL: int = 12
    PARTICLE_BASE_SIZE_TINY: int = 8


@dataclass(frozen=True)
class GameBalanceConstants:
    """Game balance-related constants.

    Attributes:
        MAX_CYCLES: Maximum number of cycles.
        BASE_THRESHOLDS: Base milestone threshold list.
        CYCLE_MULTIPLIER: Cycle multiplier for scaling.
        DIFFICULTY_MULTIPLIERS: Difficulty multipliers tuple (easy, medium, hard).
        WAVE_SIZE: Number of enemies per wave.
        EXPLOSION_RADIUS: Explosion radius.
    """
    MAX_CYCLES: int = 10
    BASE_THRESHOLDS: Tuple[int, ...] = (3000, 6000, 10000, 16000, 25000, 38000, 55000, 80000)
    CYCLE_MULTIPLIER: float = 1.35
    DIFFICULTY_MULTIPLIERS: Tuple[float, float, float] = (1.0, 1.5, 2.0)
    WAVE_SIZE: int = 11
    EXPLOSION_RADIUS: int = 50


@dataclass(frozen=True)
class BossConstants:
    """Boss battle-related constants.

    Attributes:
        BULLET_DAMAGE_BASE: Base bullet damage.
        AIM_BULLET_DAMAGE_BASE: Base aimed bullet damage.
        WAVE_BULLET_DAMAGE: Wave attack bullet damage.
        SPREAD_SPEED: Spread attack bullet speed.
        AIM_SPEED: Aimed bullet speed.
        WAVE_SPEED: Wave attack bullet speed.
        SPREAD_ANGLE_RANGE: Spread attack angle range.
        WAVE_ANGLE_INTERVAL: Wave attack angle interval.
        SIDE_ANGLE_RANGE: Side attack angle range.
        SIDE_ANGLE_OFFSET: Side attack angle offset.
        ATTACK_DISTANCE: Attack distance for aimed shots.
        BULLET_OFFSET_X: Horizontal bullet offset for multi-shot.
        FIRE_RATE_BASE: Base fire rate.
        PHASE_INTERVAL: Frames between phase transitions.
        SPREAD_BULLET_COUNT_BASE: Base number of spread bullets.
        BULLET_DAMAGE_MAP: Damage map by bullet type.
    """
    BULLET_DAMAGE_BASE: int = 12
    AIM_BULLET_DAMAGE_BASE: int = 18
    WAVE_BULLET_DAMAGE: int = 12
    SPREAD_SPEED: float = 5.0
    AIM_SPEED: float = 7.0
    WAVE_SPEED: float = 4.0
    SPREAD_ANGLE_RANGE: float = 180.0
    WAVE_ANGLE_INTERVAL: float = 22.5
    SIDE_ANGLE_RANGE: float = 45.0
    SIDE_ANGLE_OFFSET: float = 22.5
    ATTACK_DISTANCE: int = 500
    BULLET_OFFSET_X: int = 30
    FIRE_RATE_BASE: int = 60
    PHASE_INTERVAL: int = 300
    SPREAD_BULLET_COUNT_BASE: int = 5
    BULLET_DAMAGE_MAP: dict = field(default_factory=lambda: {
        'spread': 12,
        'laser': 35,
        'single': 20,
    })


@dataclass
class BoostConstants:
    """Boost system constants.

    Attributes:
        CONSUMPTION_RATE: Boost consumed per frame while active and moving.
        BASE_RECOVERY_RATE: Default recovery rate per frame.
        SPEED_MULTIPLIER: Player speed multiplier during boost.
    """
    CONSUMPTION_RATE: int = 1
    BASE_RECOVERY_RATE: float = 1.0
    SPEED_MULTIPLIER: float = 1.7


@dataclass(frozen=True)
class EnemyConstants:
    """Enemy-related constants.

    Attributes:
        LIFETIME: Enemy lifetime in frames (15 seconds = 900 frames @ 60fps).
        MOVE_TIMER: Enemy movement pattern timer threshold.
        ESCAPE_WARNING: Escape warning time before boss escapes.
    """
    LIFETIME: int = 900  # 15 seconds * 60 fps
    MOVE_TIMER: int = 60
    ESCAPE_WARNING: int = 180


@dataclass(frozen=True)
class RewardConstants:
    """Reward-related constants.

    Attributes:
        LASER_DURATION: Laser buff duration in frames.
        EXPLOSION_RADIUS: Explosion effect radius.
    """
    LASER_DURATION: int = 180
    EXPLOSION_RADIUS: int = 60


@dataclass
class GameConstants:
    """Aggregates all game constants with unified access.

    Uses composition pattern to aggregate various constant classes,
    providing a unified access entry point.

    Attributes:
        PLAYER: Player-related constants.
        DAMAGE: Damage-related constants.
        ANIMATION: Animation-related constants.
        BALANCE: Game balance-related constants.
        TIMING: Timing-related constants.
        BOSS: Boss battle-related constants.
        ENEMY: Enemy-related constants.
        REWARD: Reward-related constants.

    Methods:
        get_difficulty_multiplier(difficulty: str) -> float:
            Returns the score multiplier for the given difficulty.
        get_next_threshold(milestone_index: int, difficulty: str) -> float:
            Calculates the next milestone threshold.
    """
    PLAYER: PlayerConstants = field(default_factory=PlayerConstants)
    DAMAGE: DamageConstants = field(default_factory=DamageConstants)
    ANIMATION: AnimationConstants = field(default_factory=AnimationConstants)
    BALANCE: GameBalanceConstants = field(default_factory=GameBalanceConstants)
    TIMING: TimingConstants = field(default_factory=TimingConstants)
    BOSS: BossConstants = field(default_factory=BossConstants)
    ENEMY: EnemyConstants = field(default_factory=EnemyConstants)
    BOOST: BoostConstants = field(default_factory=BoostConstants)
    REWARD: RewardConstants = field(default_factory=RewardConstants)
    
    def get_difficulty_multiplier(self, difficulty: str) -> float:
        """Returns the score multiplier for the given difficulty.

        Args:
            difficulty: Difficulty level ('easy', 'medium', 'hard').

        Returns:
            Score multiplier (easy=1.0, medium=1.5, hard=2.0).
        """
        multipliers = {
            'easy': self.BALANCE.DIFFICULTY_MULTIPLIERS[0],
            'medium': self.BALANCE.DIFFICULTY_MULTIPLIERS[1],
            'hard': self.BALANCE.DIFFICULTY_MULTIPLIERS[2],
        }
        return multipliers.get(difficulty, 1.0)
    
    def get_next_threshold(self, milestone_index: int, difficulty: str) -> float:
        """Calculates the next milestone threshold.

        Args:
            milestone_index: Milestone index.
            difficulty: Difficulty level.

        Returns:
            Next milestone score threshold.
        """
        base_idx = milestone_index % len(self.BALANCE.BASE_THRESHOLDS)
        cycle_bonus = milestone_index // len(self.BALANCE.BASE_THRESHOLDS)
        base = self.BALANCE.BASE_THRESHOLDS[base_idx]
        multiplier = self.BALANCE.CYCLE_MULTIPLIER ** cycle_bonus
        difficulty_mult = self.get_difficulty_multiplier(difficulty)
        return base * multiplier * difficulty_mult


GAME_CONSTANTS = GameConstants()
