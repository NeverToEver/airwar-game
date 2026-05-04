"""Game controller — state management, scoring, and milestone progression."""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import logging
from ...config import DIFFICULTY_SETTINGS, VALID_DIFFICULTIES, RIPPLE_FADE_SPEED
from ..constants import GAME_CONSTANTS
from ..death_animation import DeathAnimation
from ..systems.health_system import HealthSystem
from ..systems.reward_system import RewardSystem
from ..systems.notification_manager import NotificationManager
from ..systems.difficulty_manager import DifficultyManager


def normalize_score(value) -> int:
    """Return a non-negative integer score from numeric game state values."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float) and value.is_integer():
        return max(0, int(value))
    return max(0, int(round(value)))


class GameplayState(Enum):
    """Gameplay state enum — PLAYING, DYING, GAME_OVER."""
    PLAYING = "playing"
    DYING = "dying"
    GAME_OVER = "game_over"


@dataclass
class GameState:
    """Game state dataclass — all mutable game session data."""
    difficulty: str = 'medium'
    username: str = 'Player'
    score: int = 0
    score_multiplier: float = 1.0
    paused: bool = False
    running: bool = True
    player_invincible: bool = False
    invincibility_timer: int = 0
    silent_invincible: bool = False
    ripple_effects: List[dict] = field(default_factory=list)
    notification: Optional[str] = None
    notification_timer: int = 0
    entrance_animation: bool = True
    entrance_timer: int = 0
    entrance_duration: int = GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION
    kill_count: int = 0
    boss_kill_count: int = 0
    gameplay_state: GameplayState = GameplayState.PLAYING
    death_timer: int = 0
    death_duration: int = DeathAnimation.ANIMATION_DURATION


class GameController:
    """Game controller — manages game state, scoring, and milestone progression.
    
        Coordinates player health, enemy kill scoring, difficulty thresholds,
        and delegates reward selection to RewardSystem. Acts as the central
        game logic hub during gameplay.
    
        Attributes:
            state: Current GameState snapshot.
            health_system: HealthSystem for player health and regen.
            reward_system: RewardSystem for buff selection and application.
            difficulty_manager: DifficultyManager for progressive scaling.
            milestone_index: Current milestone level (0-based).
        """
    INITIAL_DELTA = 2000
    MAX_THRESHOLD = 100000

    # 1. Special methods

    def __init__(self, difficulty: str, username: str):
        self._logger = logging.getLogger(self.__class__.__name__)
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}")

        settings = DIFFICULTY_SETTINGS[difficulty]
        self.state = GameState()
        self.state.difficulty = difficulty
        self.state.username = username
        self.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(difficulty)

        self.health_system = HealthSystem(difficulty)
        self.reward_system = RewardSystem(difficulty)
        self.notification_manager = NotificationManager()
        self.difficulty_manager = DifficultyManager(difficulty)

        self.cycle_count = 0
        self.milestone_index = 0
        self.max_cycles = GAME_CONSTANTS.BALANCE.MAX_CYCLES
        self.initial_delta = self.INITIAL_DELTA
        self.max_delta = settings['max_delta']
        self.max_threshold = self.MAX_THRESHOLD
        self.difficulty_multiplier = settings['difficulty_multiplier']

    # 3. Public lifecycle methods

    def update(self, player, has_regen: bool = False) -> None:

        """Update game controller state each frame.

        Updates health system, notification timers, ripple effects,
        death state transitions, and invincibility timer.

        Args:
        player: Player entity for health context.
        has_regen: Whether regeneration buff is active.
        """
        self.health_system.update(player, has_regen)
        self.notification_manager.update()
        self.update_ripples()

        if self.state.notification_timer > 0:
            self.state.notification_timer -= 1

        if self.state.gameplay_state == GameplayState.DYING:
            self.state.death_timer -= 1
            if self.state.death_timer <= 0:
                self.state.gameplay_state = GameplayState.GAME_OVER
                self.state.running = False
                player.active = False

        self._update_invincibility()

    # 4. Public behavior methods

    def is_playing(self) -> bool:
        return self.state.gameplay_state == GameplayState.PLAYING

    def is_game_over(self) -> bool:
        return self.state.gameplay_state == GameplayState.GAME_OVER

    def get_current_threshold(self, index: int) -> float:
        return self._get_threshold_for_index(index)

    def get_previous_threshold(self) -> float:
        if self.milestone_index > 0:
            return self._get_threshold_for_index(self.milestone_index - 1)
        return 0.0

    def get_next_progress(self) -> int:
        previous = self.get_previous_threshold()
        next_threshold = self._get_threshold_for_index(self.milestone_index)
        if next_threshold == previous:
            return 0
        progress = (self.state.score - previous) / (next_threshold - previous) * 100
        return max(0, min(100, int(progress)))

    def get_next_threshold(self) -> float:
        return self._get_threshold_for_index(self.milestone_index)

    def has_next_reward_milestone(self) -> bool:
        return self.get_next_threshold() > self.get_previous_threshold()

    def on_player_hit(self, damage: int, player) -> None:

        """Handle player being hit by enemy fire.

        Applies damage, spawns a ripple effect at the hit position,
        and transitions to DYING state if health reaches 0.

        Args:
        damage: Raw damage amount before armor calculation.
        player: Player entity to apply damage to.
        """
        player.take_damage(damage)
        center_x = player.rect.centerx
        center_y = player.rect.centery
        self.state.ripple_effects.append({
            'x': center_x,
            'y': center_y,
            'radius': 15,
            'alpha': 350,
            'pulse': 0
        })

        if player.health <= 0:
            self.state.gameplay_state = GameplayState.DYING
            self.state.death_timer = self.state.death_duration
            self.state.player_invincible = True
            self.state.invincibility_timer = 0
            self._logger.warning(f"Player died: damage={damage}, health=0")
        else:
            self.state.player_invincible = True
            self.state.invincibility_timer = GAME_CONSTANTS.PLAYER.INVINCIBILITY_DURATION
            self._logger.info(f"Player hit: damage={damage}, health={player.health}")

    def on_enemy_killed(self, score_gained: int) -> None:

        """Handle an enemy being killed.

        Increments kill count and adds score.

        Args:
        score_gained: Score value of the killed enemy.
        """
        self.state.kill_count += 1
        self.state.score = normalize_score(self.state.score + score_gained)
        self._logger.debug(f"Enemy killed: score_gained={score_gained}, total_kills={self.state.kill_count}")

    def on_boss_killed(self, score_gained: int) -> None:

        """Handle a boss being killed.

        Increments kill and boss kill counts, adds score, and notifies
        the difficulty manager of the boss kill.

        Args:
        score_gained: Score value of the killed boss.
        """
        self.state.kill_count += 1
        self.state.boss_kill_count += 1
        self.state.score = normalize_score(self.state.score + score_gained)
        self.difficulty_manager.on_boss_killed()
        self._logger.info(f"Boss killed: score_gained={score_gained}, boss_kills={self.state.boss_kill_count}")

    def update_ripples(self) -> None:
        for ripple in self.state.ripple_effects:
            ripple['radius'] += GAME_CONSTANTS.ANIMATION.RIPPLE_EXPANSION_SPEED
            ripple['alpha'] -= RIPPLE_FADE_SPEED
            ripple['pulse'] += 1
        self.state.ripple_effects = [r for r in self.state.ripple_effects if r['alpha'] > 0]

    def show_notification(self, message: str, duration: int = 90) -> None:

        """Display a timed on-screen notification.

        Args:
        message: Notification text to display.
        duration: Number of frames to show the notification.
        """
        self.state.notification = message
        self.state.notification_timer = duration
        self.notification_manager.show(message, duration)

    def on_reward_selected(self, reward: dict, player) -> None:

        """Apply the selected milestone reward to the player.

        Delegates to RewardSystem to apply the buff, then advances
        the milestone index and shows a notification.

        Args:
        reward: Reward configuration dictionary.
        player: Player entity to apply the reward to.
        """
        notification = self.reward_system.apply_reward(reward, player)
        self.milestone_index += 1
        self.cycle_count = self.milestone_index

        self.state.notification = notification
        self.state.notification_timer = GAME_CONSTANTS.TIMING.NOTIFICATION_DURATION
        self.state.paused = False

    # 5. Private lifecycle methods

    def _update_invincibility(self) -> None:
        if self.state.gameplay_state == GameplayState.DYING:
            return

        if self.state.player_invincible:
            self.state.invincibility_timer -= 1
            if self.state.invincibility_timer <= 0:
                self.state.player_invincible = False

    # 6. Private behavior methods

    def _get_threshold_for_index(self, index: int) -> float:
        threshold = self._calculate_threshold(index)
        return min(threshold, self.max_threshold * self.difficulty_multiplier)

    def _calculate_threshold(self, milestone_index: int) -> float:
        threshold = 0.0
        for i in range(milestone_index + 1):
            delta = min(self.initial_delta * (i + 1), self.max_delta)
            threshold += delta
        capped = threshold * self.difficulty_multiplier
        return min(capped, self.max_threshold * self.difficulty_multiplier)
