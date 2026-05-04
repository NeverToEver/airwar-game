"""Input detector — detects docking key combination from player."""
import pygame
from .interfaces import IInputDetector
from .mother_ship_state import DockingProgress
from .event_bus import (
    EVENT_H_PRESSED,
    EVENT_H_RELEASED,
    EVENT_PROGRESS_COMPLETE,
    EVENT_EXIT_PROGRESS_UPDATE,
    EVENT_EXIT_COMPLETE,
    EVENT_EXIT_CANCELLED,
    EVENT_DOCKING_COMPLETE,
)


class InputDetector(IInputDetector):
    """Input detector — detects docking key combination from player input."""
    H_KEY = pygame.K_h

    def __init__(self, event_bus):
        self._event_bus = event_bus
        self._progress = DockingProgress()
        self._h_was_pressed = False
        self._last_update_time = 0.0
        self._exit_progress = 0.0
        self._is_exiting = False
        self._exit_start_time = 0.0
        self._exit_required_duration = 2.0

    def update(self) -> None:
        current_time = pygame.time.get_ticks() / 1000.0
        self._last_update_time = current_time

        is_h_currently_pressed = pygame.key.get_pressed()[self.H_KEY]

        if is_h_currently_pressed and not self._h_was_pressed:
            self._on_h_pressed(current_time)
        elif not is_h_currently_pressed and self._h_was_pressed:
            self._on_h_released()
        elif is_h_currently_pressed:
            if self._is_exiting:
                self._on_exit_held(current_time)
            elif self._progress.is_pressing:
                self._on_h_held(current_time)

        self._h_was_pressed = is_h_currently_pressed

    def _on_h_pressed(self, current_time: float) -> None:
        self._event_bus.publish(EVENT_H_PRESSED, timestamp=current_time)
        if self._is_exiting:
            return
        self._progress.is_pressing = True
        self._progress.press_start_time = current_time

    def _on_h_released(self) -> None:
        if self._is_exiting:
            self._is_exiting = False
            self._exit_progress = 0.0
            self._event_bus.publish(EVENT_EXIT_CANCELLED)
        else:
            was_complete = self._progress.current_progress >= 1.0
            self._progress.reset()

            if was_complete:
                self._event_bus.publish(EVENT_DOCKING_COMPLETE)
            else:
                self._event_bus.publish(EVENT_H_RELEASED)

    def _on_h_held(self, current_time: float) -> None:
        old_progress = self._progress.current_progress
        self._progress.update_progress(current_time)

        if old_progress < 1.0 and self._progress.current_progress >= 1.0:
            self._event_bus.publish(EVENT_PROGRESS_COMPLETE)

    def _on_exit_held(self, current_time: float) -> None:
        if self._exit_progress == 0.0:
            self._exit_start_time = current_time

        elapsed = current_time - self._exit_start_time
        old_progress = self._exit_progress
        self._exit_progress = min(elapsed / self._exit_required_duration, 1.0)

        self._event_bus.publish(EVENT_EXIT_PROGRESS_UPDATE, progress=self._exit_progress)

        if old_progress < 1.0 and self._exit_progress >= 1.0:
            self._is_exiting = False
            self._exit_progress = 0.0
            self._event_bus.publish(EVENT_EXIT_COMPLETE)

    def is_h_pressed(self) -> bool:
        return pygame.key.get_pressed()[self.H_KEY]

    def get_progress(self) -> DockingProgress:
        return self._progress

    def get_exit_progress(self) -> float:
        return self._exit_progress

    def reset_progress(self) -> None:
        """Reset docking progress — 供存档恢复场景使用。"""
        self._progress.reset()

    def is_exiting(self) -> bool:
        return self._is_exiting

    def start_exit_hold(self, current_time: float | None = None) -> None:
        self._progress.reset()
        self._is_exiting = True
        self._exit_progress = 0.0
        self._exit_start_time = self._last_update_time if current_time is None else current_time
