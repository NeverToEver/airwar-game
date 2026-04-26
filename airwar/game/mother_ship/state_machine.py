"""Mothership state machine — docking flow and state transitions."""
from typing import Optional
import pygame
from .interfaces import IMotherShipStateMachine
from .mother_ship_state import MotherShipState, DockingProgress, MotherShipCooldown, DockedStayProgress
from .event_bus import EventBus


class MotherShipStateMachine(IMotherShipStateMachine):
    """Mothership state machine — manages docking flow and state transitions.
    
        Handles the full docking lifecycle: approaching → docking → saving →
        completion, with support for cancellation and error states.
        """
    VALID_TRANSITIONS = {
        MotherShipState.IDLE: [MotherShipState.COOLDOWN, MotherShipState.PRESSING],
        MotherShipState.COOLDOWN: [MotherShipState.PRESSING],
        MotherShipState.PRESSING: [MotherShipState.IDLE, MotherShipState.DOCKING],
        MotherShipState.DOCKING: [MotherShipState.DOCKED],
        MotherShipState.DOCKED: [MotherShipState.UNDOCKING],
        MotherShipState.UNDOCKING: [MotherShipState.COOLDOWN],
    }

    def __init__(self, event_bus: EventBus):
        self._current_state = MotherShipState.IDLE
        self._event_bus = event_bus
        self._animation_timer = 0
        self._cooldown = MotherShipCooldown()
        self._stay_progress = DockedStayProgress()
        self._exit_in_progress = False
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._event_bus.subscribe('H_PRESSED', self._on_h_pressed)
        self._event_bus.subscribe('H_RELEASED', self._on_h_released)
        self._event_bus.subscribe('H_RELEASED_EARLY', self._on_h_released_early)
        self._event_bus.subscribe('PROGRESS_COMPLETE', self._on_progress_complete)
        self._event_bus.subscribe('DOCKING_ANIMATION_COMPLETE', self._on_docking_animation_complete)
        self._event_bus.subscribe('UNDOCKING_ANIMATION_COMPLETE', self._on_undocking_animation_complete)
        self._event_bus.subscribe('STAY_EXPIRED', self._on_stay_expired)
        self._event_bus.subscribe('UNDOCK_REQUESTED', self._on_undock_requested)
        self._event_bus.subscribe('EXIT_COMPLETE', self._on_exit_complete)
        self._event_bus.subscribe('EXIT_PROGRESS_UPDATE', self._on_exit_progress_update)

    @property
    def current_state(self) -> MotherShipState:
        return self._current_state

    @property
    def cooldown(self) -> MotherShipCooldown:
        return self._cooldown

    @property
    def stay_progress(self) -> DockedStayProgress:
        return self._stay_progress

    def _on_h_pressed(self, **kwargs) -> None:
        if self._current_state == MotherShipState.DOCKED:
            if self._can_transition_to(MotherShipState.UNDOCKING):
                self._change_state(MotherShipState.UNDOCKING)
                self._exit_in_progress = False
                self._event_bus.publish('STATE_CHANGED', state=self._current_state)
                self._event_bus.publish('START_UNDOCKING_ANIMATION')
            return

        if self._current_state == MotherShipState.COOLDOWN:
            return

        if self._current_state == MotherShipState.IDLE:
            if self._cooldown.can_activate() and self._can_transition_to(MotherShipState.PRESSING):
                self._change_state(MotherShipState.PRESSING)
                self._event_bus.publish('STATE_CHANGED', state=self._current_state)

    def _on_h_released(self, **kwargs) -> None:
        if self._current_state == MotherShipState.COOLDOWN:
            return
        if self._can_transition_to(MotherShipState.IDLE):
            self._change_state(MotherShipState.IDLE)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('UNDOCK_CANCELLED')

    def _on_h_released_early(self, **kwargs) -> None:
        self._exit_in_progress = False

    def _on_progress_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKING):
            self._change_state(MotherShipState.DOCKING)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_DOCKING_ANIMATION')

    def _on_docking_animation_complete(self, **kwargs) -> None:
        if self._can_transition_to(MotherShipState.DOCKED):
            self._change_state(MotherShipState.DOCKED)
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._stay_progress.start_stay(pygame.time.get_ticks() / 1000.0)
            self._event_bus.publish('STAY_STARTED')

    def _on_undocking_animation_complete(self, **kwargs) -> None:
        if self._current_state == MotherShipState.UNDOCKING:
            self._change_state(MotherShipState.COOLDOWN)
            self._cooldown.start_cooldown(pygame.time.get_ticks() / 1000.0)
            self._stay_progress.reset()
            self._exit_in_progress = False
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('COOLDOWN_STARTED')
            self._event_bus.publish('GAME_RESUME')

    def _on_stay_expired(self, **kwargs) -> None:
        if self._current_state == MotherShipState.DOCKED:
            self._change_state(MotherShipState.UNDOCKING)
            self._exit_in_progress = False
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_UNDOCKING_ANIMATION')

    def _on_undock_requested(self, **kwargs) -> None:
        if self._current_state == MotherShipState.DOCKED:
            self._change_state(MotherShipState.UNDOCKING)
            self._exit_in_progress = False
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_UNDOCKING_ANIMATION')

    def _on_exit_complete(self, **kwargs) -> None:
        if self._current_state == MotherShipState.DOCKED and self._exit_in_progress:
            self._change_state(MotherShipState.UNDOCKING)
            self._exit_in_progress = False
            self._event_bus.publish('STATE_CHANGED', state=self._current_state)
            self._event_bus.publish('START_UNDOCKING_ANIMATION')

    def _on_exit_progress_update(self, **kwargs) -> None:
        pass

    def _can_transition_to(self, target_state: MotherShipState) -> bool:
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])

    def _change_state(self, new_state: MotherShipState) -> None:
        self._current_state = new_state

    def update(self, current_time: float) -> None:
        if self._current_state == MotherShipState.COOLDOWN:
            self._cooldown.update_cooldown(current_time)
        elif self._current_state == MotherShipState.DOCKED:
            self._stay_progress.update_stay(current_time)
            if self._stay_progress.is_expired():
                self._event_bus.publish('STAY_EXPIRED')

    def is_in_cooldown(self) -> bool:
        return self._current_state == MotherShipState.COOLDOWN

    def is_docked(self) -> bool:
        return self._current_state == MotherShipState.DOCKED

    def is_exit_in_progress(self) -> bool:
        return self._exit_in_progress
