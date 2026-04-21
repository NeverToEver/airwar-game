from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from airwar.config import DIFFICULTY_SETTINGS


class GameplayState(Enum):
    PLAYING = "playing"
    DYING = "dying"
    GAME_OVER = "game_over"


@dataclass
class GameState:
    difficulty: str = 'medium'
    username: str = 'Player'
    score: int = 0
    score_multiplier: int = 1
    paused: bool = False
    running: bool = True
    player_invincible: bool = False
    invincibility_timer: int = 0
    ripple_effects: List[dict] = field(default_factory=list)
    notification: Optional[str] = None
    notification_timer: int = 0
    entrance_animation: bool = True
    entrance_timer: int = 0
    entrance_duration: int = 60
    kill_count: int = 0
    boss_kill_count: int = 0
    gameplay_state: GameplayState = GameplayState.PLAYING
    death_timer: int = 0
    death_duration: int = 200


class GameController:
    def __init__(self, difficulty: str, username: str):
        settings = DIFFICULTY_SETTINGS[difficulty]
        self.state = GameState()
        self.state.difficulty = difficulty
        self.state.username = username
        self.state.score_multiplier = {'easy': 1, 'medium': 2, 'hard': 3}[difficulty]

        from airwar.game.systems.health_system import HealthSystem
        from airwar.game.systems.reward_system import RewardSystem
        from airwar.game.systems.notification_manager import NotificationManager

        self.health_system = HealthSystem(difficulty)
        self.reward_system = RewardSystem(difficulty)
        self.notification_manager = NotificationManager()

        self.cycle_count = 0
        self.milestone_index = 0
        self.max_cycles = 10
        self.base_thresholds = [1000, 2500, 5000, 10000, 20000]
        self.cycle_multiplier = 1.5
        self.difficulty_threshold_multiplier = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0}[difficulty]

    def update(self, player, has_regen: bool = False) -> None:
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

    def is_playing(self) -> bool:
        return self.state.gameplay_state == GameplayState.PLAYING

    def is_game_over(self) -> bool:
        return self.state.gameplay_state == GameplayState.GAME_OVER

    def _update_invincibility(self) -> None:
        if self.state.gameplay_state == GameplayState.DYING:
            return
        
        if self.state.player_invincible:
            self.state.invincibility_timer -= 1
            if self.state.invincibility_timer <= 0:
                self.state.player_invincible = False

    def _check_milestones(self) -> Optional[float]:
        if self.cycle_count >= self.max_cycles:
            return None

        threshold = self._get_next_threshold()
        if self.state.score >= threshold:
            return threshold
        return None

    def _get_next_threshold(self) -> float:
        base = self.base_thresholds[self.milestone_index % len(self.base_thresholds)]
        cycle_bonus = self.milestone_index // len(self.base_thresholds)
        return base * (self.cycle_multiplier ** cycle_bonus) * self.difficulty_threshold_multiplier

    def get_current_threshold(self, index: int) -> float:
        base = self.base_thresholds[index % len(self.base_thresholds)]
        cycle_bonus = index // len(self.base_thresholds)
        return base * (self.cycle_multiplier ** cycle_bonus) * self.difficulty_threshold_multiplier

    def on_player_hit(self, damage: int, player) -> None:
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
        else:
            self.state.player_invincible = True
            self.state.invincibility_timer = 90

    def on_enemy_killed(self, score_gained: int) -> None:
        self.state.kill_count += 1
        self.state.score += score_gained

    def on_boss_killed(self, score_gained: int) -> None:
        self.state.kill_count += 1
        self.state.boss_kill_count += 1
        self.state.score += score_gained

    def update_ripples(self) -> None:
        from airwar.config import RIPPLE_FADE_SPEED
        
        for ripple in self.state.ripple_effects:
            ripple['radius'] += 2.5
            ripple['alpha'] -= RIPPLE_FADE_SPEED
            ripple['pulse'] += 1
        self.state.ripple_effects = [r for r in self.state.ripple_effects if r['alpha'] > 0]

    def show_notification(self, message: str, duration: int = 90) -> None:
        self.state.notification = message
        self.state.notification_timer = duration
        self.notification_manager.show(message, duration)

    def get_next_threshold(self) -> float:
        return self._get_next_threshold()

    def on_reward_selected(self, reward: dict, player) -> None:
        notification = self.reward_system.apply_reward(reward, player)
        self.milestone_index += 1
        if self.milestone_index % len(self.base_thresholds) == 0:
            self.cycle_count += 1

        self.state.notification = notification
        self.state.notification_timer = 90
        self.state.paused = False
