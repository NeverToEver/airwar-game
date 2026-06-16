"""Mothership package — docking system for saving game progress."""

from importlib import import_module

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

_LAZY_EXPORTS = {
    "DockingProgress": ".mother_ship_state",
    "EventBus": ".event_bus",
    "GameIntegrator": ".game_integrator",
    "GameSaveData": ".mother_ship_state",
    "IEventBus": ".interfaces",
    "IInputDetector": ".interfaces",
    "IMotherShipStateMachine": ".interfaces",
    "IMotherShipUI": ".interfaces",
    "IPersistenceManager": ".interfaces",
    "ISaveData": ".save_data_protocol",
    "InputDetector": ".input_detector",
    "MotherShip": ".mother_ship",
    "MotherShipMotion": ".mother_ship_motion",
    "MotherShipRenderer": ".mother_ship_renderer",
    "MotherShipState": ".mother_ship_state",
    "MotherShipStateMachine": ".state_machine",
    "PersistenceManager": ".persistence_manager",
    "ProgressBarUI": ".progress_bar_ui",
    "SaveDataCorruptedError": ".mother_ship_state",
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
