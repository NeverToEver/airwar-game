from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.player import Player


class HealthSystem:
    def __init__(self, difficulty: str = 'medium'):
        self._difficulty = difficulty
        self._regen_timer = 0
        self._regen_interval_timer = 0
        self._regen_active = False
        self._difficulty_settings = {
            'easy': {'delay': 180, 'rate': 3, 'interval': 45},
            'medium': {'delay': 240, 'rate': 2, 'interval': 60},
            'hard': {'delay': 300, 'rate': 1, 'interval': 90},
        }

    def update(self, player: 'Player', has_regen_buff: bool = False) -> None:
        settings = self._difficulty_settings[self._difficulty]

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
        if self._regen_timer >= 60:
            self._regen_timer = 0
            player.health = min(player.health + 2, player.max_health)

    def reset(self) -> None:
        self._regen_timer = 0
        self._regen_interval_timer = 0
        self._regen_active = False

    def set_difficulty(self, difficulty: str) -> None:
        self._difficulty = difficulty
        self.reset()
