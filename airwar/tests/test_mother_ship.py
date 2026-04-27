import pytest
import pygame


class TestEventBus:
    """Tests for EventBus class"""

    def test_event_bus_creation(self):
        from airwar.game.mother_ship.event_bus import EventBus
        bus = EventBus()
        assert bus._subscribers == {}

    def test_event_bus_subscribe(self):
        from airwar.game.mother_ship.event_bus import EventBus
        bus = EventBus()
        callback = lambda: None
        bus.subscribe('TEST_EVENT', callback)
        assert 'TEST_EVENT' in bus._subscribers
        assert callback in bus._subscribers['TEST_EVENT']

    def test_event_bus_unsubscribe(self):
        from airwar.game.mother_ship.event_bus import EventBus
        bus = EventBus()
        callback = lambda: None
        bus.subscribe('TEST_EVENT', callback)
        bus.unsubscribe('TEST_EVENT', callback)
        assert callback not in bus._subscribers.get('TEST_EVENT', [])

    def test_event_bus_publish(self):
        from airwar.game.mother_ship.event_bus import EventBus
        bus = EventBus()
        results = []
        callback = lambda **kwargs: results.append(kwargs)
        bus.subscribe('TEST_EVENT', callback)
        bus.publish('TEST_EVENT', value=42)
        assert len(results) == 1
        assert results[0]['value'] == 42

    def test_event_bus_publish_multiple_callbacks(self):
        from airwar.game.mother_ship.event_bus import EventBus
        bus = EventBus()
        results = []
        bus.subscribe('TEST_EVENT', lambda **kwargs: results.append(1))
        bus.subscribe('TEST_EVENT', lambda **kwargs: results.append(2))
        bus.publish('TEST_EVENT')
        assert len(results) == 2
        assert results == [1, 2]


class TestMotherShipStateMachine:
    """Tests for MotherShipStateMachine class"""

    def test_state_machine_initial_state(self):
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        
        bus = EventBus()
        sm = MotherShipStateMachine(bus)
        assert sm.current_state == MotherShipState.IDLE

    def test_state_machine_h_pressed_from_idle(self):
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        
        bus = EventBus()
        sm = MotherShipStateMachine(bus)
        bus.publish('H_PRESSED')
        assert sm.current_state == MotherShipState.PRESSING

    def test_state_machine_h_released_from_pressing(self):
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        
        bus = EventBus()
        sm = MotherShipStateMachine(bus)
        bus.publish('H_PRESSED')
        bus.publish('H_RELEASED')
        assert sm.current_state == MotherShipState.IDLE

    def test_state_machine_progress_complete_from_pressing(self):
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        
        bus = EventBus()
        sm = MotherShipStateMachine(bus)
        bus.publish('H_PRESSED')
        bus.publish('PROGRESS_COMPLETE')
        assert sm.current_state == MotherShipState.DOCKING

    def test_state_machine_docking_animation_complete(self):
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        
        bus = EventBus()
        sm = MotherShipStateMachine(bus)
        bus.publish('H_PRESSED')
        bus.publish('PROGRESS_COMPLETE')
        bus.publish('DOCKING_ANIMATION_COMPLETE')
        assert sm.current_state == MotherShipState.DOCKED


class TestMotherShip:
    """Tests for MotherShip class"""

    def test_mother_ship_creation(self):
        from airwar.game.mother_ship.mother_ship import MotherShip
        ship = MotherShip(800, 600)
        assert ship._screen_width == 800
        assert ship._screen_height == 600
        assert ship._visible is False

    def test_mother_ship_show_hide(self):
        from airwar.game.mother_ship.mother_ship import MotherShip
        ship = MotherShip(800, 600)
        ship.show()
        assert ship.is_visible() is True
        ship.hide()
        assert ship.is_visible() is False

    def test_mother_ship_docking_position(self):
        from airwar.game.mother_ship.mother_ship import MotherShip
        ship = MotherShip(800, 600)
        pos = ship.get_docking_position()
        # Docking position: _initial_y = screen_height * 0.35 = 210, + DOCKING_BAY_Y_OFFSET = 85
        assert pos[0] == 400
        assert pos[1] == 295


class TestGameIntegrator:
    """Tests for GameIntegrator class"""

    def test_game_integrator_creation(self):
        from airwar.game.mother_ship.game_integrator import GameIntegrator
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.input_detector import InputDetector
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.persistence_manager import PersistenceManager
        from airwar.game.mother_ship.progress_bar_ui import ProgressBarUI
        from airwar.game.mother_ship.mother_ship import MotherShip
        
        bus = EventBus()
        integrator = GameIntegrator(
            event_bus=bus,
            input_detector=InputDetector(bus),
            state_machine=MotherShipStateMachine(bus),
            persistence_manager=PersistenceManager(),
            progress_bar_ui=ProgressBarUI(800, 600),
            mother_ship=MotherShip(800, 600)
        )
        assert integrator._docking_animation_active is False
        assert integrator._undocking_animation_active is False

    def test_game_integrator_attach_game_scene(self):
        from airwar.game.mother_ship.game_integrator import GameIntegrator
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.input_detector import InputDetector
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.persistence_manager import PersistenceManager
        from airwar.game.mother_ship.progress_bar_ui import ProgressBarUI
        from airwar.game.mother_ship.mother_ship import MotherShip
        
        bus = EventBus()
        integrator = GameIntegrator(
            event_bus=bus,
            input_detector=InputDetector(bus),
            state_machine=MotherShipStateMachine(bus),
            persistence_manager=PersistenceManager(),
            progress_bar_ui=ProgressBarUI(800, 600),
            mother_ship=MotherShip(800, 600)
        )
        
        mock_scene = type('MockScene', (), {'game_controller': type('MockGC', (), {'state': type('MockState', (), {})()})()})()
        integrator.attach_game_scene(mock_scene)
        assert integrator._game_scene == mock_scene

    def test_game_integrator_is_docked(self):
        from airwar.game.mother_ship.game_integrator import GameIntegrator
        from airwar.game.mother_ship.event_bus import EventBus
        from airwar.game.mother_ship.input_detector import InputDetector
        from airwar.game.mother_ship.state_machine import MotherShipStateMachine
        from airwar.game.mother_ship.persistence_manager import PersistenceManager
        from airwar.game.mother_ship.progress_bar_ui import ProgressBarUI
        from airwar.game.mother_ship.mother_ship import MotherShip
        
        bus = EventBus()
        integrator = GameIntegrator(
            event_bus=bus,
            input_detector=InputDetector(bus),
            state_machine=MotherShipStateMachine(bus),
            persistence_manager=PersistenceManager(),
            progress_bar_ui=ProgressBarUI(800, 600),
            mother_ship=MotherShip(800, 600)
        )
        assert integrator.is_docked() is False
