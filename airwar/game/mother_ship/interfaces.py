"""Mothership interfaces — protocols for input, UI, events, persistence."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from .mother_ship_state import MotherShipState, DockingProgress, GameSaveData


class IInputDetector(ABC):
    """Interface for docking input detection."""
    @abstractmethod
    def update(self) -> None:
        pass

    @abstractmethod
    def is_h_pressed(self) -> bool:
        pass

    @abstractmethod
    def get_progress(self) -> DockingProgress:
        pass


class IMotherShipUI(ABC):
    """Interface for mothership UI rendering and state display."""
    @abstractmethod
    def show(self) -> None:
        pass

    @abstractmethod
    def hide(self) -> None:
        pass

    @abstractmethod
    def update_progress(self, progress: float) -> None:
        pass

    @abstractmethod
    def play_complete_animation(self) -> None:
        pass

    @abstractmethod
    def render(self, surface: Any) -> None:
        pass


class IEventBus(ABC):
    """Interface for mothership event publish/subscribe."""
    @abstractmethod
    def subscribe(self, event: str, callback: Callable) -> None:
        pass

    @abstractmethod
    def unsubscribe(self, event: str, callback: Callable) -> None:
        pass

    @abstractmethod
    def publish(self, event: str, **kwargs) -> None:
        pass


class IPersistenceManager(ABC):
    """Interface for game state save/load operations."""
    @abstractmethod
    def save_game(self, data: GameSaveData) -> bool:
        pass

    @abstractmethod
    def load_game(self) -> Optional[GameSaveData]:
        pass

    @abstractmethod
    def has_saved_game(self) -> bool:
        pass

    @abstractmethod
    def delete_save(self) -> bool:
        pass


class IMotherShipStateMachine(ABC):
    """Interface for mothership docking state machine."""
    @property
    @abstractmethod
    def current_state(self) -> MotherShipState:
        pass

    @abstractmethod
    def update(self) -> None:
        pass


class IGameScene(ABC):
    """Interface for game scene access from GameIntegrator.

    Defines the contract for GameIntegrator to access GameScene
    without violating layer boundaries.
    """

    @abstractmethod
    def set_player_position(self, x: float, y: float) -> None:
        """Set player rect center position."""
        pass

    @abstractmethod
    def set_player_position_topleft(self, x: float, y: float) -> None:
        """Set player rect top-left position."""
        pass

    @abstractmethod
    def add_score(self, amount: int) -> None:
        """Add to score."""
        pass

    @abstractmethod
    def add_kill(self) -> None:
        """Increment kill count and update score."""
        pass

    @abstractmethod
    def add_boss_kill(self) -> None:
        """Increment boss kill count."""
        pass

    @abstractmethod
    def show_notification(self, message: str) -> None:
        """Show a notification message."""
        pass

    @abstractmethod
    def get_enemies(self) -> List:
        """Get current enemy list."""
        pass

    @abstractmethod
    def get_boss(self):
        """Get current boss or None."""
        pass

    @abstractmethod
    def clear_boss(self) -> None:
        """Clear the current boss."""
        pass

    @abstractmethod
    def set_player_invincible(self, invincible: bool, timer: int) -> None:
        """Set player invincibility state."""
        pass

    @abstractmethod
    def get_score(self) -> int:
        """Get current score."""
        pass

    @abstractmethod
    def get_cycle_count(self) -> int:
        """Get current cycle count."""
        pass

    @abstractmethod
    def get_kill_count(self) -> int:
        """Get total kill count."""
        pass

    @abstractmethod
    def get_boss_kill_count(self) -> int:
        """Get boss kill count."""
        pass

    @abstractmethod
    def get_unlocked_buffs(self) -> List:
        """Get list of unlocked buff names."""
        pass

    @abstractmethod
    def get_buff_levels(self) -> Dict[str, int]:
        """Get buff levels dictionary."""
        pass

    @abstractmethod
    def get_player_health(self) -> int:
        """Get player current health."""
        pass

    @abstractmethod
    def get_player_max_health(self) -> int:
        """Get player max health."""
        pass

    @abstractmethod
    def get_difficulty(self) -> str:
        """Get game difficulty setting."""
        pass

    @abstractmethod
    def get_username(self) -> str:
        """Get player username."""
        pass

    @abstractmethod
    def set_paused(self, paused: bool) -> None:
        """Set game paused state."""
        pass

    @abstractmethod
    def clear_ripple_effects(self) -> None:
        """Clear all ripple effects."""
        pass
