"""Game controller — state management, scoring, and milestone progression."""

import logging
from dataclasses import dataclass, field
from enum import Enum

from airwar.config import RIPPLE_FADE_SPEED, VALID_DIFFICULTIES

from ..constants import GAME_CONSTANTS, normalize_score
from ..death_animation import DeathAnimation
from ..systems.difficulty_manager import DifficultyManager
from ..systems.health_system import HealthSystem
from ..systems.notification_manager import NotificationManager
from ..systems.reward_system import RewardSystem


class GameplayState(Enum):
    """Gameplay state enum — PLAYING, DYING, GAME_OVER."""

    PLAYING = "playing"
    DYING = "dying"
    GAME_OVER = "game_over"


@dataclass
class GameState:
    """Game state dataclass — all mutable game session data."""

    difficulty: str = "medium"
    username: str = "Player"
    score: int = 0
    score_multiplier: float = 1.0
    is_paused: bool = False
    running: bool = True
    is_player_invincible: bool = False
    invincibility_timer: int = 0
    is_silent_invincible: bool = False
    ripple_effects: list[dict] = field(default_factory=list)
    # Juice-layer state (added 2026-06-09 — see STRUCTURE.md §6.6).
    damage_intensity: float = 0.0
    """0..1, set to 1.0 on player hit, decays at ~0.033/frame. Drives
    chromatic aberration and damage flash overlays."""
    hit_stop_timer: int = 0
    """Frames remaining of hit-stop. Set to 4 on player hit; gameplay tick
    is short-circuited while > 0 (~67ms at 60fps)."""
    notification: str | None = None
    notification_timer: int = 0
    requisition_points: int = 0
    is_entrance_playing: bool = True
    entrance_timer: int = 0
    entrance_duration: int = GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION
    kill_count: int = 0
    boss_kill_count: int = 0
    cycle_count: int = 0
    milestone_index: int = 0
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

    # 1. Special methods

    def __init__(self, difficulty: str, username: str):
        self._logger = logging.getLogger(self.__class__.__name__)
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}")

        self.state = GameState()
        self.state.difficulty = difficulty
        self.state.username = username
        self.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(difficulty)

        self.health_system = HealthSystem(difficulty)
        self.reward_system = RewardSystem(difficulty)
        self.notification_manager = NotificationManager()
        self.difficulty_manager = DifficultyManager(difficulty)

        self._lock_manager = None

    def set_lock_manager(self, lock_manager) -> None:
        """Set the LockManager for centralized state arbitration."""
        self._lock_manager = lock_manager

    def set_invincible(self, invincible: bool, timer: int = 0, silent: bool = False) -> None:
        """Set player invincibility via the centralized LockManager.

        F02 D1: single-path routing. The LockManager is the single
        source of truth for invincibility / lock state. Production
        always wires the LockManager during scene setup; calling this
        method without one is a programming error.
        """
        from ..systems.lock_manager import LockLayer, LockRequest

        assert self._lock_manager is not None, (
            "GameController.set_invincible requires a LockManager. Call set_lock_manager() during scene initialization."
        )
        if invincible:
            self._lock_manager.acquire(
                LockLayer.PLAYER_HIT,
                LockRequest(invincible=True, is_silent_invincible=silent, invincibility_duration=timer),
            )
        else:
            self._lock_manager.release(LockLayer.PLAYER_HIT)

    def set_paused(self, paused: bool) -> None:
        """Set game paused state via the centralized LockManager.

        F02 D2: single-path routing.
        """
        from ..systems.lock_manager import LockLayer, LockRequest

        assert self._lock_manager is not None, (
            "GameController.set_paused requires a LockManager. Call set_lock_manager() during scene initialization."
        )
        if paused:
            self._lock_manager.acquire(
                LockLayer.GAME_PAUSE,
                LockRequest(is_paused=True),
            )
        else:
            self._lock_manager.release(LockLayer.GAME_PAUSE)

    # 3. Public lifecycle methods

    def set_score(self, value: int) -> None:
        """F1: encapsulate direct state mutation of score.

        Replaces scene-layer direct writes to ``state.score``.
        """
        from ..constants import normalize_score

        self.state.score = normalize_score(value)

    def set_cycle_count(self, value: int) -> None:
        """F2: encapsulate direct state mutation of cycle_count."""
        self.state.cycle_count = max(0, int(value))
        self.state.milestone_index = self.state.cycle_count

    def set_difficulty(self, difficulty: str) -> None:
        """F3: encapsulate direct state mutation of difficulty and propagate."""
        from airwar.config import VALID_DIFFICULTIES

        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}")
        self.state.difficulty = difficulty
        self.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(difficulty)

    def add_score(self, amount: int) -> None:
        """F4: encapsulate score accumulation from scene layer."""
        from ..constants import normalize_score

        self.state.score = normalize_score(self.state.score + amount)

    def add_kill_count(self) -> None:
        """F5: encapsulate kill_count++ from scene layer."""
        self.state.kill_count += 1

    def add_boss_kill_count(self) -> None:
        """F6: encapsulate boss_kill_count++ from scene layer."""
        self.state.boss_kill_count += 1

    def clear_ripples(self) -> None:
        """F8: encapsulate ripple_effects clearing from scene layer."""
        self.state.ripple_effects.clear()

    def start_entrance_animation(self) -> None:
        """F9: encapsulate entrance animation restart from coordinator.

        Used by HomecomingCoordinator to reset the entrance animation
        when the player returns from the home base.
        """
        self.state.is_entrance_playing = True
        self.state.entrance_timer = 0

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

        # Cache the player ref so _update_invincibility can mirror state
        # to the entity (for alpha-blink rendering) without a controller→
        # entity back-reference in the constructor — see player.sync_invincibility_blink.
        self._player_ref = player
        self._update_invincibility()

    # 4. Public behavior methods

    def is_playing(self) -> bool:
        """Return whether the player is currently in the active PLAYING state.

        Returns:
            bool: True if `state.gameplay_state` is PLAYING.
        """
        return self.state.gameplay_state == GameplayState.PLAYING

    def is_game_over(self) -> bool:
        """Return whether the death animation has finished and run is over.

        Returns:
            bool: True if `state.gameplay_state` is GAME_OVER.
        """
        return self.state.gameplay_state == GameplayState.GAME_OVER

    def get_current_threshold(self, index: int) -> float:
        """Return the score threshold for an arbitrary milestone index.

        Args:
            index: Milestone index to look up (0-based).

        Returns:
            float: Score value at which the requested milestone triggers.
        """
        return self._get_threshold_for_index(index)

    def get_previous_threshold(self) -> float:
        """Return the score threshold for the last completed milestone.

        Returns:
            float: Threshold score for `milestone_index - 1`, or 0.0 if
            no milestone has been completed yet.
        """
        if self.state.milestone_index > 0:
            return self._get_threshold_for_index(self.state.milestone_index - 1)
        return 0.0

    def get_next_progress(self) -> int:
        """Return progress toward the next reward milestone as a percentage.

        Computes the fraction of the way from the previous threshold to
        the next threshold that the current score represents, clamped
        to the [0, 100] integer range. Returns 0 if there is no upcoming
        milestone.

        Returns:
            int: Progress percentage in the range [0, 100].
        """
        previous = self.get_previous_threshold()
        next_threshold = self._get_threshold_for_index(self.state.milestone_index)
        if next_threshold == previous:
            return 0
        progress = (self.state.score - previous) / (next_threshold - previous) * 100
        return max(0, min(100, int(progress)))

    def get_next_threshold(self) -> float:
        """Return the score threshold for the next reward milestone.

        Returns:
            float: Threshold score at which the next reward will fire.
        """
        return self._get_threshold_for_index(self.state.milestone_index)

    def has_next_reward_milestone(self) -> bool:
        """Return whether another reward milestone is still pending.

        Returns:
            bool: True if a higher threshold exists beyond the most
            recent completed milestone.
        """
        return self.get_next_threshold() > self.get_previous_threshold()

    def on_player_hit(self, damage: int, player) -> None:
        """Handle player being hit by enemy fire.

        Applies damage, spawns a ripple effect at the hit position,
        and transitions to DYING state if health reaches 0.
        If player is shielded, damage is blocked and no ripple/invincibility is triggered.

        Args:
        damage: Raw damage amount before armor calculation.
        player: Player entity to apply damage to.
        """
        pre_health = player.health
        player.take_damage(damage)
        if player.health == pre_health:
            return  # Shield absorbed the hit — no ripple, no invincibility

        center_x = player.rect.centerx
        center_y = player.rect.centery
        self.state.ripple_effects.append({"x": center_x, "y": center_y, "radius": 15, "alpha": 350, "pulse": 0})

        # Juice: trigger damage intensity (drives chromatic aberration flash)
        # and the 4-frame hit-stop (set to the current value to avoid clobbering
        # a longer freeze from another hit). Play the player-hit SFX as well —
        # this is the audio hook the rest of the juice layer piggybacks on.
        self.state.damage_intensity = 1.0
        if self.state.hit_stop_timer < 4:
            self.state.hit_stop_timer = 4
        # Audio is failure-tolerant: get_sound_manager() returns a no-op
        # singleton when pygame.mixer.init() failed (headless CI / sandbox).
        try:
            from airwar.audio.sound_manager import get_sound_manager
            get_sound_manager().play_sfx("player_hit")
        except Exception:  # noqa: BLE001 — audio is best-effort
            pass

        if player.health <= 0:
            self.state.gameplay_state = GameplayState.DYING
            self.state.death_timer = self.state.death_duration
            self.set_invincible(True, timer=0)
            self._logger.warning(f"Player died: damage={damage}, health=0")
        else:
            self.set_invincible(True, timer=GAME_CONSTANTS.PLAYER.INVINCIBILITY_DURATION)
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
        self.state.requisition_points += GAME_CONSTANTS.REQUISITION.BOSS_KILL_POINTS
        self.difficulty_manager.on_boss_killed()
        self._logger.info(f"Boss killed: score_gained={score_gained}, boss_kills={self.state.boss_kill_count}")

    def update_ripples(self) -> None:
        """Advance the per-frame state of every active hit ripple effect.

        Expands each ripple's radius, fades its alpha, increments the
        pulse counter, and prunes any ripple whose alpha has reached
        zero. Called once per frame from `update`.
        """
        for ripple in self.state.ripple_effects:
            ripple["radius"] += GAME_CONSTANTS.ANIMATION.RIPPLE_EXPANSION_SPEED
            ripple["alpha"] -= RIPPLE_FADE_SPEED
            ripple["pulse"] += 1
        self.state.ripple_effects = [r for r in self.state.ripple_effects if r["alpha"] > 0]

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
        self.state.milestone_index += 1
        self.state.cycle_count = self.state.milestone_index

        self.state.notification = notification
        self.state.notification_timer = GAME_CONSTANTS.TIMING.NOTIFICATION_DURATION
        self.set_paused(False)

    # 5. Private lifecycle methods

    def _update_invincibility(self) -> None:
        if self.state.gameplay_state == GameplayState.DYING:
            return

        if self.state.is_player_invincible:
            self.state.invincibility_timer -= 1
            if self.state.invincibility_timer <= 0:
                self.set_invincible(False)

        # Juice: decay damage_intensity and tick hit-stop. Both fields are
        # additive state — see STRUCTURE.md §6.6.
        if self.state.damage_intensity > 0.0:
            self.state.damage_intensity = max(
                0.0, self.state.damage_intensity - 0.033
            )
        if self.state.hit_stop_timer > 0:
            self.state.hit_stop_timer -= 1

        # Mirror invincibility state to the player for alpha-blink rendering.
        # Cheap (two attribute writes); the blink is a pure render-time effect.
        player = getattr(self, "_player_ref", None)
        if player is not None and hasattr(player, "sync_invincibility_blink"):
            player.sync_invincibility_blink(
                self.state.is_player_invincible,
                self.state.invincibility_timer,
            )

    # 6. Private behavior methods

    def _get_threshold_for_index(self, index: int) -> float:
        return GAME_CONSTANTS.get_next_threshold(index, self.state.difficulty)
