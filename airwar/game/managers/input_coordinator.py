from typing import Protocol
import pygame
from airwar.game.constants import GAME_CONSTANTS


class PlayerProtocol(Protocol):
    def fire(self) -> None: ...
    def get_bullets(self): ...
    def render(self, surface) -> None: ...


class RewardSelectorProtocol(Protocol):
    def handle_input(self, event) -> None: ...
    @property
    def visible(self) -> bool: ...


class GameControllerProtocol(Protocol):
    @property
    def state(self): ...
    def is_playing(self) -> bool: ...


class GiveUpDetectorProtocol:
    def update(self, delta: float) -> None: ...
    def is_active(self) -> bool: ...
    def get_progress(self) -> float: ...


class GiveUpUIProtocol:
    def show(self) -> None: ...
    def hide(self) -> None: ...
    def update_progress(self, progress: float) -> None: ...
    def render(self, surface) -> None: ...


class InputCoordinator:
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
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self._can_fire():
                    self._player.fire()
        self._reward_selector.handle_input(event)

    def _can_fire(self) -> bool:
        return (
            not self._game_controller.state.paused
            and not self._reward_selector.visible
        )

    def update_give_up(self) -> None:
        if not self._can_use_give_up():
            self._give_up_ui.hide()
            return

        self._give_up_detector.update(GAME_CONSTANTS.TIMING.FIXED_DELTA_TIME)

        if self._give_up_detector.is_active():
            self._give_up_ui.show()
            self._give_up_ui.update_progress(self._give_up_detector.get_progress())
        else:
            self._give_up_ui.hide()

    def _can_use_give_up(self) -> bool:
        return (
            self._game_controller.is_playing()
            and not self._game_controller.state.paused
            and not self._reward_selector.visible
        )

    def render_give_up(self, surface: pygame.Surface) -> None:
        if self._give_up_detector.is_active():
            self._give_up_ui.render(surface)
