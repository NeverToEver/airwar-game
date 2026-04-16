import pygame
from .interfaces import IInputDetector
from .mother_ship_state import DockingProgress


class InputDetector(IInputDetector):
    H_KEY = pygame.K_h

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._progress = DockingProgress()
        self._h_was_pressed = False
        self._last_update_time = 0.0

    def update(self) -> None:
        current_time = pygame.time.get_ticks() / 1000.0
        self._last_update_time = current_time

        is_h_currently_pressed = pygame.key.get_pressed()[self.H_KEY]

        if is_h_currently_pressed and not self._h_was_pressed:
            self._on_h_pressed(current_time)
        elif not is_h_currently_pressed and self._h_was_pressed:
            self._on_h_released()
        elif is_h_currently_pressed and self._progress.is_pressing:
            self._on_h_held(current_time)

        self._h_was_pressed = is_h_currently_pressed



    def _on_h_pressed(self, current_time: float) -> None:
        self._progress.is_pressing = True
        self._progress.press_start_time = current_time
        self._event_bus.publish('H_PRESSED', timestamp=current_time)

    def _on_h_released(self) -> None:
        was_complete = self._progress.current_progress >= 1.0
        self._progress.reset()

        if was_complete:
            self._event_bus.publish('DOCKING_COMPLETE')
        else:
            self._event_bus.publish('H_RELEASED')

    def _on_h_held(self, current_time: float) -> None:
        old_progress = self._progress.current_progress
        self._progress.update_progress(current_time)

        if old_progress < 1.0 and self._progress.current_progress >= 1.0:
            self._event_bus.publish('PROGRESS_COMPLETE')

    def is_h_pressed(self) -> bool:
        return pygame.key.get_pressed()[self.H_KEY]

    def get_progress(self) -> DockingProgress:
        return self._progress
