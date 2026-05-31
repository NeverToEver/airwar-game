"""Mothership package — docking system for saving game progress."""
from .event_bus import EventBus
from .game_integrator import GameIntegrator
from .input_detector import InputDetector
from .interfaces import (
    IEventBus,
    IInputDetector,
    IMotherShipStateMachine,
    IMotherShipUI,
    IPersistenceManager,
)
from .mother_ship import MotherShip
from .mother_ship_state import DockingProgress, GameSaveData, MotherShipState, SaveDataCorruptedError
from .persistence_manager import PersistenceManager
from .progress_bar_ui import ProgressBarUI
from .state_machine import MotherShipStateMachine

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
