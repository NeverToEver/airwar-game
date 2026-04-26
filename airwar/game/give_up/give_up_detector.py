"""Give-up detector — hold-key-to-surrender input detection."""
import pygame
from typing import Callable


class GiveUpDetector:
    """Give-up detector — detects hold-key-to-surrender input pattern.
    
        Monitors a specific key (K) for sustained press duration to trigger
        the voluntary surrender flow.
        """
    K_KEY = pygame.K_k
    HOLD_DURATION = 3.0

    def __init__(self, on_complete_callback: Callable[[], None]):
        self._progress = 0.0
        self._k_was_pressed = False
        self._on_complete_callback = on_complete_callback
        self._is_complete = False

    def update(self, delta_time: float) -> None:
        is_k_pressed = pygame.key.get_pressed()[self.K_KEY]

        if is_k_pressed and not self._k_was_pressed:
            self._on_k_pressed()
        elif not is_k_pressed and self._k_was_pressed:
            self._on_k_released()
        elif is_k_pressed:
            self._on_k_held(delta_time)

        self._k_was_pressed = is_k_pressed

    def _on_k_pressed(self) -> None:
        self._progress = 0.0
        self._is_complete = False

    def _on_k_released(self) -> None:
        self._progress = 0.0
        self._is_complete = False

    def _on_k_held(self, delta_time: float) -> None:
        if self._is_complete:
            return

        self._progress += delta_time / self.HOLD_DURATION
        self._progress = min(self._progress, 1.0)

        if self._progress >= 1.0 and not self._is_complete:
            self._is_complete = True
            if self._on_complete_callback:
                self._on_complete_callback()

    def get_progress(self) -> float:
        return self._progress

    def is_active(self) -> bool:
        return self._progress > 0 and not self._is_complete

    def reset(self) -> None:
        self._progress = 0.0
        self._k_was_pressed = False
        self._is_complete = False
