from typing import List, Dict, Optional
import logging

from airwar.game.systems.difficulty_strategies import (
    DifficultyStrategy,
    DifficultyStrategyFactory,
)


class DifficultyListener:
    def on_difficulty_changed(self, params: Dict) -> None:
        raise NotImplementedError


class DifficultyManager:
    MAX_COMPLEXITY: int = 5
    MAX_MULTIPLIER_GLOBAL: float = 8.0
    MAX_BOSS_COUNT: int = 20

    def __init__(self, difficulty: str = 'medium') -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._strategy = DifficultyStrategyFactory.create(difficulty)
        self._boss_kill_count: int = 0
        self._current_multiplier: float = self._strategy.base_multiplier
        self._cache_dirty: bool = True
        self._cached_params: Optional[Dict] = None
        self._listeners: List[DifficultyListener] = []

        self._logger.info(f"DifficultyManager initialized with difficulty: {difficulty}")

    def set_boss_kill_count(self, count: int) -> None:
        if count < 0:
            raise ValueError("boss_kill_count cannot be negative")

        if count != self._boss_kill_count:
            self._boss_kill_count = min(count, self.MAX_BOSS_COUNT)
            self._update_multiplier()
            self._logger.debug(
                f"Boss kill count updated: {self._boss_kill_count}, "
                f"multiplier: {self._current_multiplier:.2f}"
            )

    def get_boss_kill_count(self) -> int:
        return self._boss_kill_count

    def on_boss_killed(self) -> None:
        self._boss_kill_count += 1
        self._boss_kill_count = min(self._boss_kill_count, self.MAX_BOSS_COUNT)

        old_multiplier = self._current_multiplier
        self._update_multiplier()

        self._logger.info(
            f"Boss #{self._boss_kill_count} killed - "
            f"multiplier: {old_multiplier:.2f} -> {self._current_multiplier:.2f}"
        )

        self._notify_listeners()

    def _update_multiplier(self) -> None:
        raw_multiplier = self._strategy.base_multiplier

        if self._boss_kill_count > 0:
            exponential_bonus = (2 ** self._boss_kill_count - 1)
            raw_multiplier += exponential_bonus * self._strategy.growth_rate

        self._current_multiplier = min(
            raw_multiplier,
            self._strategy.max_multiplier
        )
        self._cache_dirty = True

    def get_current_multiplier(self) -> float:
        return self._current_multiplier

    def get_speed_multiplier(self) -> float:
        return 1.0 + (self._current_multiplier - 1) * self._strategy.speed_bonus

    def get_fire_rate_multiplier(self) -> float:
        return 1.0 + (self._current_multiplier - 1) * self._strategy.fire_rate_bonus

    def get_aggression_multiplier(self) -> float:
        return 1.0 + (self._current_multiplier - 1) * self._strategy.aggression_bonus

    def get_movement_complexity(self) -> int:
        return min(self.MAX_COMPLEXITY, 1 + self._boss_kill_count // 2)

    def get_current_params(self) -> Dict:
        if self._cache_dirty or self._cached_params is None:
            self._cached_params = self._calculate_params()
            self._cache_dirty = False

        return self._cached_params.copy()

    def _calculate_params(self) -> Dict:
        self._logger.debug(
            f"Calculating difficulty params: "
            f"boss_kills={self._boss_kill_count}, "
            f"multiplier={self._current_multiplier:.2f}"
        )

        from airwar.config.difficulty_config import BASE_ENEMY_PARAMS

        speed_mult = self.get_speed_multiplier()
        fire_mult = self.get_fire_rate_multiplier()
        aggro_mult = self.get_aggression_multiplier()

        params = {
            'speed': BASE_ENEMY_PARAMS['speed'] * speed_mult,
            'fire_rate': max(30, int(BASE_ENEMY_PARAMS['fire_rate'] / fire_mult)),
            'aggression': min(1.0, BASE_ENEMY_PARAMS['aggression'] * aggro_mult),
            'spawn_rate': max(10, int(BASE_ENEMY_PARAMS['spawn_rate'] / (1 + speed_mult * 0.1))),
            'multiplier': self._current_multiplier,
            'boss_kills': self._boss_kill_count,
            'complexity': self.get_movement_complexity(),
        }

        self._logger.debug(f"Difficulty params calculated: {params}")
        return params

    def _invalidate_cache(self) -> None:
        self._cache_dirty = True

    def add_listener(self, listener: DifficultyListener) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)
            self._logger.debug(f"Listener added: {listener.__class__.__name__}")

    def remove_listener(self, listener: DifficultyListener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)
            self._logger.debug(f"Listener removed: {listener.__class__.__name__}")

    def _notify_listeners(self) -> None:
        params = self.get_current_params()
        for listener in self._listeners:
            try:
                listener.on_difficulty_changed(params)
            except Exception as e:
                self._logger.error(
                    f"Error notifying listener {listener.__class__.__name__}: {e}"
                )
