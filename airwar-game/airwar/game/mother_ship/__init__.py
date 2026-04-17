__all__ = [
    'IInputDetector',
    'IMotherShipUI',
    'IEventBus',
    'IPersistenceManager',
    'IMotherShipStateMachine',
    'MotherShipState',
    'DockingProgress',
    'GameSaveData',
    'EventBus',
    'InputDetector',
    'MotherShipStateMachine',
    'ProgressBarUI',
    'PersistenceManager',
    'MotherShip',
    'GameIntegrator',
]


_EXPORT_MAP = {
    'IInputDetector': ('airwar.game.mother_ship.interfaces', 'IInputDetector'),
    'IMotherShipUI': ('airwar.game.mother_ship.interfaces', 'IMotherShipUI'),
    'IEventBus': ('airwar.game.mother_ship.interfaces', 'IEventBus'),
    'IPersistenceManager': ('airwar.game.mother_ship.interfaces', 'IPersistenceManager'),
    'IMotherShipStateMachine': ('airwar.game.mother_ship.interfaces', 'IMotherShipStateMachine'),
    'MotherShipState': ('airwar.game.mother_ship.mother_ship_state', 'MotherShipState'),
    'DockingProgress': ('airwar.game.mother_ship.mother_ship_state', 'DockingProgress'),
    'GameSaveData': ('airwar.game.mother_ship.mother_ship_state', 'GameSaveData'),
    'EventBus': ('airwar.game.mother_ship.event_bus', 'EventBus'),
    'InputDetector': ('airwar.game.mother_ship.input_detector', 'InputDetector'),
    'MotherShipStateMachine': ('airwar.game.mother_ship.state_machine', 'MotherShipStateMachine'),
    'ProgressBarUI': ('airwar.game.mother_ship.progress_bar_ui', 'ProgressBarUI'),
    'PersistenceManager': ('airwar.game.mother_ship.persistence_manager', 'PersistenceManager'),
    'MotherShip': ('airwar.game.mother_ship.mother_ship', 'MotherShip'),
    'GameIntegrator': ('airwar.game.mother_ship.game_integrator', 'GameIntegrator'),
}


def __getattr__(name):
    module_path, attr_name = _EXPORT_MAP.get(name, (None, None))
    if not module_path:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = __import__(module_path, fromlist=[attr_name])
    return getattr(module, attr_name)


def __dir__():
    return sorted(__all__)
