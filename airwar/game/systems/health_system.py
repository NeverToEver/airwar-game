"""Health and regeneration system for player entities."""
from typing import TYPE_CHECKING
from ...config import HEALTH_REGEN
from ..constants import GAME_CONSTANTS

if TYPE_CHECKING:
    from ...entities.player import Player


class HealthSystem:
    """Health system — manages player health regeneration and invincibility.
    
        Handles periodic health regen ticks and invincibility timer management
        after the player takes damage.
    
        Attributes:
            _regen_timer: Frames since last regen tick.
            _regen_active: Whether regen is currently enabled.
        """
    def __init__(self, difficulty: str = 'medium'):
        self._difficulty = difficulty
        self._regen_timer = 0
        self._regen_interval_timer = 0
        self._regen_active = False

    def update(self, player: 'Player', has_regen_buff: bool = False) -> None:
        if player.health <= 0:
            return

        settings = HEALTH_REGEN[self._difficulty]

        if has_regen_buff:
            self._update_buff_regen(player)
        else:
            self._update_normal_regen(player, settings)

    def _update_normal_regen(self, player: 'Player', settings: dict) -> None:
        self._regen_timer += 1
        if self._regen_timer >= settings['delay']:
            self._regen_timer = settings['delay']
            self._regen_active = True

        if self._regen_active:
            self._regen_interval_timer += 1
            if self._regen_interval_timer >= settings['interval']:
                self._regen_interval_timer = 0
                player.health = min(player.health + settings['rate'], player.max_health)

    def _update_buff_regen(self, player: 'Player') -> None:
        self._regen_timer += 1
        if self._regen_timer >= GAME_CONSTANTS.DAMAGE.REGEN_THRESHOLD:
            self._regen_timer = 0
            player.health = min(player.health + GAME_CONSTANTS.DAMAGE.DEFAULT_REGEN_RATE, player.max_health)

    def reset(self) -> None:
        self._regen_timer = 0
        self._regen_interval_timer = 0
        self._regen_active = False

    def set_difficulty(self, difficulty: str) -> None:
        self._difficulty = difficulty
        self.reset()
