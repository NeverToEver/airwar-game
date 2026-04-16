from typing import Optional
from .interfaces import IMotherShipStateMachine
from .mother_ship_state import MotherShipState, DockingProgress
from .event_bus import EventBus


class MotherShipStateMachine(IMotherShipStateMachine):
    VALID_TRANSITIONS = {
        MotherShipState.IDLE: [MotherShipState.PRESSING],
        MotherShipState.PRESSING: [MotherShipState.IDLE, MotherShipState.DOCKING],
        MotherShipState.DOCKING: [MotherShipState.DOCKED],
        MotherShipState.DOCKED: [MotherShipState.UNDOCKING],
        MotherShipState.UNDOCKING: [MotherShipState.IDLE],
    }

    def __init__(self, event_bus: EventBus):
        self._current_state = MotherShipState.IDLE
        self._event_bus = event_bus
        self._animation_timer = 0
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._event_bus.subscribe('H_PRESSED', self._on_h_pressed)
        self._event_bus.subscribe('H_RELEASED', self._on_h_released)
        self._event_bus.subscribe('PROGRESS_COMPLETE', self._on_progress_complete)
        self._event_bus.subscribe('DOCKING_ANIMATION_COMPLETE', self._on_docking_animation_complete)
        self._event_bus.subscribe('UNDOCKING_ANIMATION_COMPLETE', self._on_undocking_animation_complete)

    @property
    def current_state(self) -> MotherShipState:
        return self._current_state

    def transition(self, event: str, **kwargs) -> None:
        pass

    def _on_h_pressed(self, **kwargs) -> None:
        if self._current_state == MotherShipState.DOCKED:
            if self._can_transition_to(MotherShipState.UNDOCKING):
                self._change_state(MotherShipState.UNDOCKING)
                self._event_bus.publish('STATE_CHANGED', state=self._current_state)
                self._event_bus.publish('START_UNDOCKING_ANIMATION')
        elif self._can_transition_to(MotherShipState.PRESSING):
            self._change_state(MotherShipState.PRESSING)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)

    def _on_h_released(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.IDLE):
            self._change_state(MotherShipState.IDLE)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('UNDOCK_CANCELLED')

    def _on_progress_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKING):
            self._change_state(MotherShipState.DOCKING)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_DOCKING_ANIMATION')

    def _on_docking_animation_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKED):
            self._change_state(MotherShipState.DOCKED)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('SAVE_GAME_REQUEST')

    def _on_undocking_animation_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.IDLE):
            self._change_state(MotherShipState.IDLE)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('GAME_RESUME')

    def _can_transition_to(self, target_state: MotherShipState) -> bool:
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])

    def _change_state(self, new_state: MotherShipState) -> None:
        self._current_state = new_state

    def update(self) -> None:
        pass
