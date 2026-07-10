"""Input routing — coordinates player input with current game state."""

from typing import Protocol

import pygame

from ..protocols import (
    GameControllerProtocol,
    GiveUpDetectorProtocol,
    GiveUpUIProtocol,
    RewardSelectorProtocol,
)


class PlayerProtocol(Protocol):
    """Protocol for player input methods."""

    def fire(self) -> None: ...
    def get_bullets(self): ...
    def render(self, surface) -> None: ...


class InputCoordinator:
    """Input coordinator — routes player input to the active game subsystem.

    Disambiguates input between gameplay, reward selection, and give-up
    states. Uses protocol-based dependency injection for all subsystems.

    Attributes:
        _player: Player instance for movement/fire input.
        _game_controller: GameController for state queries.
        _give_up_detector: GiveUpDetector for surrender key handling.
    """

    def __init__(
        self,
        player: PlayerProtocol,
        game_controller: GameControllerProtocol,
        reward_selector: RewardSelectorProtocol,
        give_up_detector: GiveUpDetectorProtocol,
        give_up_ui: GiveUpUIProtocol,
    ):
        self._player = player
        self._game_controller = game_controller
        self._reward_selector = reward_selector
        self._give_up_detector = give_up_detector
        self._give_up_ui = give_up_ui

    def handle_events(self, event: pygame.event.Event) -> None:
        self._reward_selector.handle_input(event)

    def _can_fire(self) -> bool:
        return not self._game_controller.state.is_paused and not self._reward_selector.visible

    def update_give_up(self, delta_seconds: float) -> None:
        if not self._can_use_give_up():
            self._give_up_ui.hide()
            return

        self._give_up_detector.update(delta_seconds)

        if self._give_up_detector.is_active():
            self._give_up_ui.show()
            self._give_up_ui.update_progress(self._give_up_detector.get_progress())
        else:
            self._give_up_ui.hide()

    def _can_use_give_up(self) -> bool:
        return (
            self._game_controller.is_playing()
            and not self._game_controller.state.is_paused
            and not self._reward_selector.visible
        )

    def render_give_up(self, surface: pygame.Surface) -> None:
        if self._give_up_detector.is_active():
            self._give_up_ui.render(surface)
