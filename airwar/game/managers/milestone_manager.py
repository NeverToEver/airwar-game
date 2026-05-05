"""Milestone manager module.

Unified management of milestone triggers and reward selection flow.
Separates milestone-related operations from GameScene.

Design principles:
- Single responsibility: Milestone checking and reward selection only.
- Dependency injection: Dependencies received via constructor.
- Facade pattern: Unified milestone operation entry point.

Usage:
    from airwar.game.managers import MilestoneManager

    milestone_manager = MilestoneManager(game_controller, reward_system)
    milestone_manager.set_reward_selector(reward_selector)
    milestone_manager.check_and_trigger(player)
"""

from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from .game_controller import GameController
    from ..systems.reward_system import RewardSystem
    from ...ui.reward_selector import RewardSelector

from .game_controller import GameplayState


class MilestoneManager:
    """Milestone trigger and reward selection flow manager.

    Manages milestone checking and reward selection callbacks.

    Responsibilities:
    - Milestone check logic.
    - Reward selection callback handling.
    - Does not handle reward generation (handled by RewardSystem).
    - Does not handle reward rendering (handled by RewardSelector).

    Attributes:
        _game_controller: Game controller (provides state access and game logic).
        _reward_system: Reward system (provides reward option generation).
        _reward_selector: Reward selector (for display and selection).
        _on_reward_selected_callback: Callback for reward selection completion.
    """

    def __init__(
        self,
        game_controller: 'GameController',
        reward_system: 'RewardSystem'
    ) -> None:
        """Initialize the milestone manager.

        Args:
            game_controller: Game controller.
            reward_system: Reward system.
        """
        self._game_controller = game_controller
        self._reward_system = reward_system
        self._reward_selector: Optional['RewardSelector'] = None
        self._on_reward_selected_callback: Optional[Callable] = None

    def set_reward_selector(self, reward_selector: 'RewardSelector') -> None:
        """Set the reward selector.

        Args:
            reward_selector: Reward selector instance.
        """
        self._reward_selector = reward_selector

    def check_and_trigger(self, player) -> bool:
        """Check milestone and trigger reward selection.

        Checks if the current score has reached the next milestone threshold.
        If so, displays the reward selection UI.

        Args:
            player: Player object (for reward application).

        Returns:
            bool: True if a milestone was triggered, False otherwise.
        """
        if self._game_controller.state.gameplay_state != GameplayState.PLAYING:
            return False
        if not self._game_controller.has_next_reward_milestone():
            return False

        threshold = self._game_controller.get_next_threshold()
        if self._game_controller.state.score >= threshold:
            self._trigger_reward_selection(player)
            return True
        return False

    def _trigger_reward_selection(self, player) -> None:
        """Trigger the reward selection flow.

        Args:
            player: Player object.
        """
        boss_kill_count = self._game_controller.difficulty_manager.get_boss_kill_count()
        options = self._reward_system.generate_options(
            boss_kill_count,
            self._reward_system.unlocked_buffs
        )
        self._show_reward_selection(options, player)
        self._game_controller.state.paused = True

    def _show_reward_selection(self, options: list, player) -> None:
        """Show the reward selector.

        Args:
            options: List of reward options.
            player: Player object (for callback).
        """
        if not self._reward_selector:
            return
        if hasattr(self._reward_selector, "show"):
            self._reward_selector.show(
                options,
                lambda reward: self._on_reward_selected(reward, player),
                buff_levels=dict(getattr(self._reward_system, "buff_levels", {})),
                unlocked_buffs=list(getattr(self._reward_system, "unlocked_buffs", [])),
            )
            return
        self._reward_selector.visible = True
        self._reward_selector.options = options
        self._reward_selector.selected_index = 0
        self._reward_selector.buff_levels = dict(getattr(self._reward_system, "buff_levels", {}))
        self._reward_selector.unlocked_buffs = list(getattr(self._reward_system, "unlocked_buffs", []))
        self._reward_selector.on_select = lambda reward: self._on_reward_selected(reward, player)

    def _on_reward_selected(self, reward: dict, player) -> None:
        """Handle reward selection callback.

        Args:
            reward: Selected reward config dict.
            player: Player object.
        """
        self._game_controller.on_reward_selected(reward, player)
        if self._reward_selector:
            self._reward_selector.visible = False
        if self._on_reward_selected_callback:
            self._on_reward_selected_callback(reward)

    def set_on_reward_selected_callback(self, callback: Callable) -> None:
        """Set the callback for reward selection completion.

        Args:
            callback: Callback function.
        """
        self._on_reward_selected_callback = callback

    @property
    def is_reward_visible(self) -> bool:
        """Check if the reward selector is visible.

        Returns:
            bool: True if the reward selector is visible.
        """
        return self._reward_selector.visible if self._reward_selector else False
