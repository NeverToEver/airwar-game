"""Mothership state — docking progress, player save data structures."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time
import pygame


CURRENT_SAVE_VERSION = 1


class SaveDataCorruptedError(Exception):
    """存档数据损坏异常"""
    pass


class MotherShipState(Enum):
    """Mothership state enum — docking lifecycle states."""
    IDLE = "idle"
    COOLDOWN = "cooldown"
    PRESSING = "pressing"
    ENTERING = "entering"
    DOCKING = "docking"
    DOCKED = "docked"
    UNDOCKING = "undocking"


@dataclass
class DockingProgress:
    """Docking progress dataclass — tracks current docking advancement."""
    is_pressing: bool = False
    press_start_time: float = 0.0
    current_progress: float = 0.0
    required_duration: float = 3.0

    def update_progress(self, current_time: float) -> None:
        if self.is_pressing:
            elapsed = current_time - self.press_start_time
            self.current_progress = min(elapsed / self.required_duration, 1.0)

    def reset(self) -> None:
        self.is_pressing = False
        self.press_start_time = 0.0
        self.current_progress = 0.0


@dataclass
class MotherShipCooldown:
    """Tracks the 1-minute cooldown between MotherShip activations."""
    is_in_cooldown: bool = False
    cooldown_start_time: float = 0.0
    cooldown_progress: float = 0.0
    cooldown_duration: float = 60.0  # 1 minute

    def start_cooldown(self, current_time: float) -> None:
        self.is_in_cooldown = True
        self.cooldown_start_time = current_time
        self.cooldown_progress = 0.0

    def update_cooldown(self, current_time: float) -> None:
        if self.is_in_cooldown:
            elapsed = current_time - self.cooldown_start_time
            self.cooldown_progress = min(elapsed / self.cooldown_duration, 1.0)
            if self.cooldown_progress >= 1.0:
                self.is_in_cooldown = False
                self.cooldown_progress = 1.0

    def can_activate(self) -> bool:
        return not self.is_in_cooldown

    def get_remaining_time(self) -> float:
        if not self.is_in_cooldown:
            return 0.0
        return max(0.0, self.cooldown_duration - (pygame.time.get_ticks() / 1000.0 - self.cooldown_start_time))


@dataclass
class DockedStayProgress:
    """Tracks the 20-second stay duration inside MotherShip."""
    is_staying: bool = False
    stay_start_time: float = 0.0
    stay_progress: float = 0.0
    stay_duration: float = 20.0  # 20 seconds

    def start_stay(self, current_time: float) -> None:
        self.is_staying = True
        self.stay_start_time = current_time
        self.stay_progress = 0.0

    def update_stay(self, current_time: float) -> None:
        if self.is_staying:
            elapsed = current_time - self.stay_start_time
            self.stay_progress = min(elapsed / self.stay_duration, 1.0)

    def is_expired(self) -> bool:
        return self.is_staying and self.stay_progress >= 1.0

    def reset(self) -> None:
        self.is_staying = False
        self.stay_start_time = 0.0
        self.stay_progress = 0.0


@dataclass
class GameSaveData:
    """Game save data dataclass — serializable game state for persistence."""
    version: int = CURRENT_SAVE_VERSION
    score: int = 0
    cycle_count: int = 0
    kill_count: int = 0
    boss_kill_count: int = 0
    unlocked_buffs: List[str] = field(default_factory=list)
    buff_levels: Dict[str, int] = field(default_factory=dict)
    player_health: int = 100
    player_max_health: int = 100
    difficulty: str = "medium"
    timestamp: float = field(default_factory=time.time)
    is_in_mothership: bool = False
    username: str = ""

    def to_dict(self) -> Dict:
        return {
            'version': self.version,
            'score': self.score,
            'cycle_count': self.cycle_count,
            'kill_count': self.kill_count,
            'boss_kill_count': self.boss_kill_count,
            'unlocked_buffs': self.unlocked_buffs,
            'buff_levels': self.buff_levels,
            'player_health': self.player_health,
            'player_max_health': self.player_max_health,
            'difficulty': self.difficulty,
            'timestamp': self.timestamp,
            'is_in_mothership': self.is_in_mothership,
            'username': self.username,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GameSaveData':
        if 'version' not in data:
            data = cls._migrate_legacy_save(data)

        if data.get('version', 0) > CURRENT_SAVE_VERSION:
            raise SaveDataCorruptedError(
                f"Save file version {data['version']} is newer than "
                f"supported version {CURRENT_SAVE_VERSION}"
            )

        required_fields = ['score', 'username']
        for field_name in required_fields:
            if field_name not in data:
                raise SaveDataCorruptedError(f"Missing required field: {field_name}")

        return cls(**data)

    @classmethod
    def _migrate_legacy_save(cls, data: Dict) -> Dict:
        data['version'] = 1
        return data
