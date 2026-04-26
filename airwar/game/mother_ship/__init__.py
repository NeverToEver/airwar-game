"""Mothership package — docking system for saving game progress."""
from .interfaces import (
    IInputDetector,
    IMotherShipUI,
    IEventBus,
    IPersistenceManager,
    IMotherShipStateMachine,
)
from .mother_ship_state import MotherShipState, DockingProgress, GameSaveData, SaveDataCorruptedError
from .event_bus import EventBus
from .input_detector import InputDetector
from .state_machine import MotherShipStateMachine
from .progress_bar_ui import ProgressBarUI
from .persistence_manager import PersistenceManager
from .mother_ship import MotherShip
from .game_integrator import GameIntegrator

__all__ = [
    'IInputDetector',
    'IMotherShipUI',
    'IEventBus',
    'IPersistenceManager',
    'IMotherShipStateMachine',
    'MotherShipState',
    'DockingProgress',
    'GameSaveData',
    'SaveDataCorruptedError',
    'EventBus',
    'InputDetector',
    'MotherShipStateMachine',
    'ProgressBarUI',
    'PersistenceManager',
    'MotherShip',
    'GameIntegrator',
]
