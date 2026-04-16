from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time


class MotherShipState(Enum):
    IDLE = "idle"
    PRESSING = "pressing"
    DOCKING = "docking"
    DOCKED = "docked"
    UNDOCKING = "undocking"


@dataclass
class DockingProgress:
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
class GameSaveData:
    score: int = 0
    cycle_count: int = 0
    kill_count: int = 0
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
            'score': self.score,
            'cycle_count': self.cycle_count,
            'kill_count': self.kill_count,
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
        return cls(**data)
