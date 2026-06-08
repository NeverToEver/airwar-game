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
from .mother_ship_motion import MotherShipMotion
from .mother_ship_renderer import MotherShipRenderer
from .mother_ship_state import DockingProgress, GameSaveData, MotherShipState, SaveDataCorruptedError
from .persistence_manager import PersistenceManager
from .progress_bar_ui import ProgressBarUI
from .save_data_protocol import ISaveData
from .state_machine import MotherShipStateMachine

__all__ = [
    "DockingProgress",
    "EventBus",
    "GameIntegrator",
    "GameSaveData",
    "IEventBus",
    "IInputDetector",
    "IMotherShipStateMachine",
    "IMotherShipUI",
    "IPersistenceManager",
    "ISaveData",
    "InputDetector",
    "MotherShip",
    "MotherShipMotion",
    "MotherShipRenderer",
    "MotherShipState",
    "MotherShipStateMachine",
    "PersistenceManager",
    "ProgressBarUI",
    "SaveDataCorruptedError",
]
