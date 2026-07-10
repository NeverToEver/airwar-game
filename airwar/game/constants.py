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


def normalize_score(value) -> int:
    """Return a non-negative integer score from numeric game state values."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float) and value.is_integer():
        return max(0, int(value))
    return max(0, round(value))


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
    """

    ENTRANCE_DURATION: int = 60
    RIPPLE_INITIAL_RADIUS: int = 15
    RIPPLE_INITIAL_ALPHA: int = 350
    RIPPLE_EXPANSION_SPEED: float = 2.5
    NOTIFICATION_DECAY_RATE: int = 1
    PARTICLE_ALPHA_VISIBILITY_THRESHOLD: int = 10


@dataclass(frozen=True)
class GameBalanceConstants:
    """Game balance-related constants.

    Attributes:
        BASE_THRESHOLDS: Base milestone threshold list.
        CYCLE_MULTIPLIER: Cycle multiplier for scaling.
        DIFFICULTY_MULTIPLIERS: Difficulty multipliers tuple (easy, medium, hard).
        WAVE_SIZE: Number of enemies per wave.
        EXPLOSION_RADIUS: Explosion radius.
    """

    BASE_THRESHOLDS: tuple[int, ...] = (3000, 6000, 10000, 16000, 25000, 38000, 55000, 80000)
    CYCLE_MULTIPLIER: float = 1.35
    DIFFICULTY_MULTIPLIERS: tuple[float, float, float] = (1.0, 2.0, 3.0)
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
    BULLET_DAMAGE_MAP: dict = field(
        default_factory=lambda: {
            "spread": 12,
            "laser": 35,
            "single": 20,
        }
    )


@dataclass(frozen=True)
class EnrageConstants:
    """F04 M9: Boss enrage tuning constants.

    Previously scattered as module-level constants in
    ``airwar.entities.enemy.boss.boss_state``. They are re-exported
    there as backward-compat aliases so existing callers keep working.
    """

    TRIGGER_RATIO: float = 0.30
    DURATION: int = 360
    TRANSITION_DURATION: int = 54
    SLOW_FACTOR: float = 0.24
    BULLET_SPEED: float = 3.2
    LASER_SPEED: float = 3.7
    RELEASE_BULLET_SPEED: float = 1.55
    RELEASE_LASER_SPEED: float = 1.35
    ATTACK_INTERVAL: int = 42
    ATTACK_WINDUP: int = 24
    RELEASE_INTERVAL: int = 6
    SNAPSHOT_LASER_COUNT: int = 4
    SNAPSHOT_RING_COUNT: int = 8
    PATH_RADIUS_SCALE: float = 1.50
    SQUARE_PATH_RATIO: float = 0.48
    TRAIL_LENGTH: int = 42
    TRAIL_RENDER_MAX: int = 16
    TRAIL_FINAL_SCALE: float = 3.0
    TRAIL_SCALE: float = 0.5
    TRAIL_BLUR_PASSES: int = 2
    EXIT_BACK_OFFSET: int = 118
    MUZZLE_FLASH_DURATION: int = 12
    MUZZLE_FLASH_PULSES: int = 2
    MUZZLE_FORWARD_SCALE: float = 0.58
    MUZZLE_SIDE_SCALE: float = 0.34
    RELEASE_HOLD_DURATION: int = 42
    RETURN_DURATION: int = 48
    CORE_COLOR: tuple = (126, 220, 255)
    DANGER_COLOR: tuple = (230, 72, 68)
    TRAIL_TINT: tuple = (96, 154, 220)


@dataclass(frozen=True)
class HomecomingPhaseConstants:
    """F04 M10: Homecoming sequence phase frame counts.

    Previously scattered as class-level constants on HomecomingSequence.
    """

    FTL_ESCAPE: int = 54
    BLACKOUT: int = 34
    STATION_REVEAL: int = 70
    APPROACH: int = 96
    LANDING: int = 72
    HANDOFF: int = 64
    BASE_LAUNCH: int = 76
    RETURN_BLACKOUT: int = 34
    ORBITAL_STRIKE: int = 86
    ORBITAL_STRIKE_IMPACT_PROGRESS: float = 0.56


@dataclass(frozen=True)
class EnemyConstants:
    """Enemy-related constants.

    Attributes:
        LIFETIME: Enemy lifetime in frames (15 seconds = 900 frames @ 60fps).
        MOVE_RANGE_X: Horizontal movement range around active position.
        MOVE_RANGE_Y: Vertical movement range around active position.
        MOVE_TIMER: Enemy movement pattern timer threshold.
        ESCAPE_WARNING: Escape warning time before boss escapes.
    """

    LIFETIME: int = 900  # 15 seconds * 60 fps
    MOVE_RANGE_X: int = 80
    MOVE_RANGE_Y: int = 50
    MOVE_TIMER: int = 60
    ESCAPE_WARNING: int = 180


@dataclass(frozen=True)
class EnemyTuningConstants:
    """Tuning values shared by enemy-related gameplay systems.

    They were previously scattered as class-body constants on
    :class:`airwar.entities.enemy.Enemy`, :class:`EnemySpawner`, and
    :class:`EliteEnemy`. Consolidated here for single-source-of-truth.

    Sub-groups:
        Entry/Exit: ENTRY_START_Y, EXIT_X_OFFSETS, EXIT_END_Y,
                    EXIT_ACTIVE_END_Y, TRANSITION_DURATION,
                    ENTRY_SPEED, EXIT_SPEED, ENEMY_BULLET_SPEED
        Combat:     FIRE_RATE_MIN, SPREAD_FIRE_OFFSETS,
                    LASER_FIRE_RATE, NORMAL_FIRE_RATE, ELITE_FIRE_RATE
        Spawn:      ENEMIES_PER_FRAME, DEFAULT_SPEED, DEFAULT_SPAWN_RATE,
                    MAX_CONCURRENT_ENEMIES, ELITES_PER_WAVE,
                    MIN_SPAWN_Y, MAX_SPAWN_Y_FRACTION, ENTRY_SPAWN_Y,
                    DEFAULT_SPREAD_ENEMY_CAP
        Movement ranges: SINE_*, ZIGZAG_*, DIVE_*, HOVER_*, SPIRAL_*,
                    NOISE_*, AGGR_*, HOVER_TIMER_RUST_SCALE
        Movement defaults: DEFAULT_MOVE_*, DEFAULT_NOISE_*,
                    DEFAULT_AGGRESSIVE_*, DEFAULT_ZIGZAG_*,
                    DEFAULT_SPIRAL_*
        Elite:      VISUAL_SCALE, COLLISION_SCALE, ELITE_ENTRY_SPEED,
                    SPAWN_START_Y
    """

    # --- Entry/Exit ---
    ENTRY_START_Y: int = 150
    EXIT_X_OFFSETS: tuple = (-300, 300, 0, -150, 150)
    EXIT_END_Y: int = -150
    EXIT_ACTIVE_END_Y: int = -100
    TRANSITION_DURATION: int = 15
    ENTRY_SPEED: float = 0.04
    EXIT_SPEED: float = 0.03
    ENEMY_BULLET_SPEED: float = 5.0

    # --- Combat ---
    FIRE_RATE_MIN: int = 10
    SPREAD_FIRE_OFFSETS: tuple = (-28, -14, 0, 14, 28)
    LASER_FIRE_RATE: int = 60
    NORMAL_FIRE_RATE: int = 80
    ELITE_FIRE_RATE: int = 30

    # --- Spawn ---
    ENEMIES_PER_FRAME: int = 2
    DEFAULT_SPEED: float = 3.0
    DEFAULT_SPAWN_RATE: int = 30
    MAX_CONCURRENT_ENEMIES: int = 5
    ELITES_PER_WAVE: int = 2
    MIN_SPAWN_Y: int = -30
    MAX_SPAWN_Y_FRACTION: float = 0.70
    ENTRY_SPAWN_Y: int = -50
    DEFAULT_SPREAD_ENEMY_CAP: int = 2

    # --- Movement ranges ---
    SINE_AMP_RANGE: tuple = (1.5, 3.0)
    SINE_FREQ_RANGE: tuple = (0.03, 0.06)
    ZIGZAG_INTERVAL_RANGE: tuple = (30, 60)
    ZIGZAG_SPEED_RANGE: tuple = (1.5, 2.5)
    DIVE_DELAY_RANGE: tuple = (20, 50)
    HOVER_SPEED_RANGE: tuple = (1.0, 1.8)
    HOVER_AMP_RANGE: tuple = (20, 40)
    SPIRAL_SPEED_RANGE: tuple = (1.0, 2.0)
    SPIRAL_RADIUS_RANGE: tuple = (30, 50)
    SPIRAL_FREQ_RANGE: tuple = (0.05, 0.08)
    NOISE_SPEED_RANGE: tuple = (0.02, 0.04)
    NOISE_SCALE_X_RANGE: tuple = (0.5, 1.0)
    NOISE_SCALE_Y_RANGE: tuple = (0.3, 0.6)
    NOISE_AMP_X_RANGE: tuple = (0.6, 0.9)
    NOISE_AMP_Y_RANGE: tuple = (0.3, 0.6)
    AGGR_SPEED_RANGE: tuple = (0.025, 0.045)
    AGGR_SCALE_X_RANGE: tuple = (0.6, 1.0)
    AGGR_SCALE_Y_RANGE: tuple = (0.5, 0.8)
    AGGR_AMP_X_RANGE: tuple = (0.5, 0.8)
    AGGR_AMP_Y_RANGE: tuple = (0.4, 0.7)
    HOVER_TIMER_RUST_SCALE: float = 0.08

    # --- Movement defaults (fallbacks when an attribute is missing) ---
    DEFAULT_MOVE_AMPLITUDE: float = 2.0
    DEFAULT_MOVE_FREQUENCY: float = 0.05
    DEFAULT_MOVE_SPEED: float = 2.0
    DEFAULT_NOISE_SPEED: float = 0.03
    DEFAULT_AGGRESSIVE_SPEED: float = 0.035
    DEFAULT_ZIGZAG_INTERVAL: float = 45.0
    DEFAULT_SPIRAL_RADIUS: float = 40.0
    DEFAULT_NOISE_SCALE_X: float = 0.04
    DEFAULT_NOISE_SCALE_Y: float = 0.02
    DEFAULT_NOISE_AMPLITUDE_X: float = 0.7
    DEFAULT_NOISE_AMPLITUDE_Y: float = 0.4
    DEFAULT_AGGRESSIVE_AMPLITUDE_X: float = 0.6
    DEFAULT_AGGRESSIVE_AMPLITUDE_Y: float = 0.5

    # --- Elite enemy ---
    VISUAL_SCALE: float = 1.3
    COLLISION_SCALE: float = 1.18
    ELITE_ENTRY_SPEED: float = 0.03
    SPAWN_START_Y: int = -80


@dataclass(frozen=True)
class BossTuningConstants:
    """Boss movement and attack tuning previously scattered as
    module-level constants in :mod:`airwar.entities.enemy.boss.boss_movement`
    and :mod:`.boss_attack`, plus the two hitbox scales on the ``Boss``
    class. Consolidated here for single-source-of-truth.

    The 27 enrage-related constants continue to live in
    :class:`EnrageConstants` and are re-exported from ``Boss`` for gameplay
    systems that use them.
    """

    # --- Movement (from boss_movement.py) ---
    DEFAULT_PHASE_DURATION: int = 120
    ENTRY_SPEED: float = 2.0
    ESCAPE_DRIFT: float = 0.5
    LERP_FACTOR: float = 0.025
    MIN_Y: int = 50
    CENTER_OFFSET: int = 60
    AIM_DASH_DISTANCE: int = 220
    AIM_DASH_PHASE_BONUS: int = 35
    AIM_DASH_MAX_DISTANCE_RATIO: float = 0.58
    AIM_DASH_DURATION: int = 10

    # --- Attack (from boss_attack.py) ---
    ATTACK_DIRECTIONS: tuple = ("down", "left", "right", "up")
    SPREAD_DAMAGE_INCREMENT: int = 2
    AIM_DAMAGE_INCREMENT: int = 3
    AIM_BULLET_COUNT: int = 3
    WAVE_BULLET_COUNT: int = 8

    # --- Hitbox scales (previously on Boss class) ---
    HITBOX_WIDTH_SCALE: float = 1.78
    HITBOX_HEIGHT_SCALE: float = 1.22


@dataclass(frozen=True)
class RewardConstants:
    """Reward-related constants.

    Attributes:
        LASER_DURATION: Laser buff duration in frames.
        EXPLOSION_RADIUS: Explosion effect radius.
    """

    LASER_DURATION: int = 180
    EXPLOSION_RADIUS: int = 60


class RequisitionConstants:
    """Requisition point costs and rewards for base operations."""

    BOSS_KILL_POINTS = 5
    REPAIR_COST = 2
    RECHARGE_COST = 2
    MISSION_REWARD = 3


# Sentinel value: a finite-but-very-large frame count to express
# "effectively infinite" invincibility. Using a real upper bound keeps
# counters from underflowing and lets timers tick without special-casing.
PERMANENT_INVINCIBILITY_FRAMES: int = 999_999


class PersistenceConstants:
    """Persistence- and auto-save-related constants.

    Centralizes frame counts that were previously scattered as
    magic numbers in scene/coordinator modules (Phase 3 logic-clarity
    refactor — F04 M1/M2/M3/M7).
    """

    PERMANENT_INVINCIBILITY_FRAMES: int = PERMANENT_INVINCIBILITY_FRAMES
    DOCKING_INVINCIBILITY_FRAMES: int = 1200  # 20 seconds at 60 FPS
    AUTO_SAVE_INTERVAL: int = 1800  # 30 seconds at 60 FPS
    BULLET_CLEAR_DEDUP_FRAMES: int = 1
    BULLET_CLEAR_RADIUS: int = 250


class EventConstants:
    """Event-bus-related constants.

    Centralizes limits that were previously hardcoded in the event_bus
    module (Phase 3 logic-clarity refactor — F04 M11).
    """

    MAX_SUBSCRIBERS: int = 1000
    MAX_CALLBACK_FAILURES: int = 3


class GameplayConstants:
    """Per-frame gameplay constants previously inline in scenes/systems.

    Phase 3 logic-clarity refactor — F04 M2/M3/M4/M5.
    """

    @staticmethod
    def bullet_clear_dedup_initial_frame() -> int:
        """Initial frame offset for the bullet-clear dedup sentinel.

        Used as a far-past timestamp so the first real hit is never
        suppressed by the dedup logic.
        """
        return -1_000_000_000


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
    BOSS_ENRAGE: EnrageConstants = field(default_factory=EnrageConstants)
    BOSS_TUNING: BossTuningConstants = field(default_factory=BossTuningConstants)
    HOMECOMING_PHASES: HomecomingPhaseConstants = field(default_factory=HomecomingPhaseConstants)
    ENEMY: EnemyConstants = field(default_factory=EnemyConstants)
    ENEMY_TUNING: EnemyTuningConstants = field(default_factory=EnemyTuningConstants)
    REWARD: RewardConstants = field(default_factory=RewardConstants)
    REQUISITION: RequisitionConstants = field(default_factory=RequisitionConstants)
    PERSISTENCE: PersistenceConstants = field(default_factory=PersistenceConstants)
    EVENTS: EventConstants = field(default_factory=EventConstants)
    GAMEPLAY: GameplayConstants = field(default_factory=GameplayConstants)

    def get_difficulty_multiplier(self, difficulty: str) -> float:
        """Returns the score multiplier for the given difficulty.

        Args:
            difficulty: Difficulty level ('easy', 'medium', 'hard').

        Returns:
            Score multiplier (easy=1.0, medium=2.0, hard=3.0).
        """
        multipliers = {
            "easy": self.BALANCE.DIFFICULTY_MULTIPLIERS[0],
            "medium": self.BALANCE.DIFFICULTY_MULTIPLIERS[1],
            "hard": self.BALANCE.DIFFICULTY_MULTIPLIERS[2],
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
        base_thresholds = self.BALANCE.BASE_THRESHOLDS
        milestone_index = max(0, int(milestone_index))
        cycle_length = len(base_thresholds)
        cycle_index = milestone_index // cycle_length
        step_index = milestone_index % cycle_length
        difficulty_mult = self.get_difficulty_multiplier(difficulty)

        threshold = 0.0
        base_deltas = []
        previous_base = 0
        for base in base_thresholds:
            base_deltas.append(base - previous_base)
            previous_base = base

        # BASE_THRESHOLDS describes the first cycle as absolute milestones.
        # Later cycles scale the interval deltas so thresholds never reset.
        for cycle in range(cycle_index + 1):
            cycle_multiplier = self.BALANCE.CYCLE_MULTIPLIER**cycle
            last_step = step_index if cycle == cycle_index else cycle_length - 1
            for delta in base_deltas[: last_step + 1]:
                threshold += delta * cycle_multiplier

        return threshold * difficulty_mult


GAME_CONSTANTS = GameConstants()
