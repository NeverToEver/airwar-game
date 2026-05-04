"""Homecoming detector -- hold B to request a safe return sequence."""

from collections.abc import Callable

import pygame


class HomecomingDetector:
    """Detects the hold-B return-home input pattern."""

    B_KEY = pygame.K_b
    HOLD_DURATION = 2.4

    def __init__(self, on_complete_callback: Callable[[], None]):
        self._progress = 0.0
        self._b_was_pressed = False
        self._on_complete_callback = on_complete_callback
        self._is_complete = False
        self._enabled = True

    def update(self, delta_time: float, enabled: bool = True) -> None:
        self._enabled = enabled
        if not enabled:
            self.reset()
            return

        is_b_pressed = pygame.key.get_pressed()[self.B_KEY]

        if is_b_pressed and not self._b_was_pressed:
            self._on_b_pressed()
        elif not is_b_pressed and self._b_was_pressed:
            self._on_b_released()
        elif is_b_pressed:
            self._on_b_held(delta_time)

        self._b_was_pressed = is_b_pressed

    def get_progress(self) -> float:
        return self._progress

    def is_active(self) -> bool:
        return self._enabled and self._progress > 0 and not self._is_complete

    def reset(self) -> None:
        self._progress = 0.0
        self._b_was_pressed = False
        self._is_complete = False

    def _on_b_pressed(self) -> None:
        self._progress = 0.0
        self._is_complete = False

    def _on_b_released(self) -> None:
        self._progress = 0.0
        self._is_complete = False

    def _on_b_held(self, delta_time: float) -> None:
        if self._is_complete:
            return

        self._progress = min(1.0, self._progress + delta_time / self.HOLD_DURATION)
        if self._progress >= 1.0 and not self._is_complete:
            self._is_complete = True
            if self._on_complete_callback:
                self._on_complete_callback()
