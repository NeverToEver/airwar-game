"""Top-level cross-layer Protocol contracts.

These protocols are imported by **lower** layers (entities, ui,
config) without dragging the whole ``airwar.game`` package into scope.
Putting them at the package root (instead of under
``airwar.game.protocols``) avoids the circular import that would
otherwise be triggered by ``airwar.ui`` -> ``airwar.game`` ->
``airwar.ui``.

Contracts defined here:
    * :class:`InputSourceProtocol` -- duck-typed input source for the
      player
    * :class:`BuffFactoryProtocol` / :class:`BuffFactory` -- UI
      buff-creation callable
    * :class:`GameConstantsProtocol` / :class:`RequisitionConstantsProtocol`
      -- view into the game constants used by the UI
    * :class:`DifficultyManagerProtocol` -- view into the difficulty
      manager used by the UI

Manager / scene contracts (``PlayerProtocol``, ``GameControllerProtocol``,
``GameRendererProtocol``, etc.) live in :mod:`airwar.game.protocols`
because they are only used by game-internal code and are allowed to
import the full ``airwar.game`` namespace.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class InputSourceProtocol(Protocol):
    """Duck-typed input source for the player.

    The :class:`airwar.entities.player.Player` only needs to read input
    state; it should not need to know whether the source is the live
    Pygame handler, a recording, or a unit-test stub. The real
    :class:`airwar.input.input_handler.PygameInputHandler` already
    matches this protocol structurally.
    """

    def get_movement_direction(self): ...
    def is_pause_pressed(self) -> bool: ...
    def is_boost_pressed(self) -> bool: ...
    def is_boost_just_pressed(self) -> bool: ...
    def is_precision_pressed(self) -> bool: ...
    def is_precision_just_pressed(self) -> bool: ...


@runtime_checkable
class BuffFactoryProtocol(Protocol):
    """Single-method protocol — the UI only needs ``create_buff(name)``."""

    def __call__(self, name: str) -> object: ...


# Convenience callable alias for the common case.
BuffFactory = Callable[[str], object]


@runtime_checkable
class RequisitionConstantsProtocol(Protocol):
    """Subset of ``GAME_CONSTANTS.REQUISITION`` accessed by the UI."""

    REPAIR_COST: int
    RECHARGE_COST: int


# Real class attribute so ``hasattr(Protocol, 'REPAIR_COST')`` returns True
# on the bare Protocol class itself (Protocol annotations alone do not
# materialise as attributes; runtime_checkable only checks instances).
RequisitionConstantsProtocol.REPAIR_COST = 0
RequisitionConstantsProtocol.RECHARGE_COST = 0


@runtime_checkable
class GameConstantsProtocol(Protocol):
    """Subset of ``GAME_CONSTANTS`` accessed by the UI."""

    REQUISITION: RequisitionConstantsProtocol


# Real class attribute so ``hasattr(Protocol, 'REQUISITION')`` returns True
# on the bare Protocol class itself.
GameConstantsProtocol.REQUISITION = object()  # placeholder, type-erased


@runtime_checkable
class DifficultyManagerProtocol(Protocol):
    """Subset of ``DifficultyManager`` accessed by the UI panel."""

    def get_current_difficulty(self) -> object: ...


__all__ = [
    "BuffFactory",
    "BuffFactoryProtocol",
    "DifficultyManagerProtocol",
    "GameConstantsProtocol",
    "InputSourceProtocol",
    "RequisitionConstantsProtocol",
]
