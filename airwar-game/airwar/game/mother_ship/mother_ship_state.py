from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time


VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}
VALID_SHOT_MODES = {'normal', 'shotgun', 'laser'}


def _safe_int(value, default: int = 0, minimum: Optional[int] = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default

    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _safe_float(value, default: float = 0.0, minimum: Optional[float] = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default

    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _safe_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {'true', '1', 'yes'}:
            return True
        if lowered in {'false', '0', 'no'}:
            return False
    return default


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
    milestone_index: int = 0
    kill_count: int = 0
    boss_kill_count: int = 0
    unlocked_buffs: List[str] = field(default_factory=list)
    buff_levels: Dict[str, int] = field(default_factory=dict)
    player_health: int = 100
    player_max_health: int = 100
    player_x: int = 0
    player_y: int = 0
    player_bullet_damage: int = 50
    player_fire_interval: int = 8
    player_shot_mode: str = "normal"
    player_speed: float = 5.0
    difficulty: str = "medium"
    timestamp: float = field(default_factory=time.time)
    is_in_mothership: bool = False
    username: str = ""

    def to_dict(self) -> Dict:
        return {
            'score': self.score,
            'cycle_count': self.cycle_count,
            'milestone_index': self.milestone_index,
            'kill_count': self.kill_count,
            'boss_kill_count': self.boss_kill_count,
            'unlocked_buffs': self.unlocked_buffs,
            'buff_levels': self.buff_levels,
            'player_health': self.player_health,
            'player_max_health': self.player_max_health,
            'player_x': self.player_x,
            'player_y': self.player_y,
            'player_bullet_damage': self.player_bullet_damage,
            'player_fire_interval': self.player_fire_interval,
            'player_shot_mode': self.player_shot_mode,
            'player_speed': self.player_speed,
            'difficulty': self.difficulty,
            'timestamp': self.timestamp,
            'is_in_mothership': self.is_in_mothership,
            'username': self.username,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GameSaveData':
        if not isinstance(data, dict):
            return cls()

        difficulty = _safe_str(data.get('difficulty'), 'medium')
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = 'medium'

        player_max_health = _safe_int(data.get('player_max_health'), 100, minimum=1)
        player_health = min(
            player_max_health,
            _safe_int(data.get('player_health'), player_max_health, minimum=0)
        )

        player_shot_mode = _safe_str(data.get('player_shot_mode'), 'normal')
        if player_shot_mode not in VALID_SHOT_MODES:
            player_shot_mode = 'normal'

        raw_unlocked_buffs = data.get('unlocked_buffs')
        unlocked_buffs = [str(buff) for buff in raw_unlocked_buffs] if isinstance(raw_unlocked_buffs, list) else []

        raw_buff_levels = data.get('buff_levels')
        buff_levels = {
            str(key): _safe_int(value, 0, minimum=0)
            for key, value in raw_buff_levels.items()
        } if isinstance(raw_buff_levels, dict) else {}

        return cls(
            score=_safe_int(data.get('score'), 0, minimum=0),
            cycle_count=_safe_int(data.get('cycle_count'), 0, minimum=0),
            milestone_index=_safe_int(data.get('milestone_index'), 0, minimum=0),
            kill_count=_safe_int(data.get('kill_count'), 0, minimum=0),
            boss_kill_count=_safe_int(data.get('boss_kill_count'), 0, minimum=0),
            unlocked_buffs=unlocked_buffs,
            buff_levels=buff_levels,
            player_health=player_health,
            player_max_health=player_max_health,
            player_x=_safe_int(data.get('player_x'), 0),
            player_y=_safe_int(data.get('player_y'), 0),
            player_bullet_damage=_safe_int(data.get('player_bullet_damage'), 50, minimum=1),
            player_fire_interval=_safe_int(data.get('player_fire_interval'), 8, minimum=1),
            player_shot_mode=player_shot_mode,
            player_speed=_safe_float(data.get('player_speed'), 5.0, minimum=1.0),
            difficulty=difficulty,
            timestamp=_safe_float(data.get('timestamp'), time.time(), minimum=0.0),
            is_in_mothership=_safe_bool(data.get('is_in_mothership'), False),
            username=_safe_str(data.get('username'), '')[:64],
        )
