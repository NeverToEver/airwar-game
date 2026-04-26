"""Mothership interfaces — protocols for input, UI, events, persistence."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
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
    def transition(self, event: str, **kwargs) -> None:
        pass

    @abstractmethod
    def update(self) -> None:
        pass
