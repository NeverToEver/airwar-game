"""UI coordination — manages rendering delegation and overlay display."""

import pygame

from ..buffs.buff_registry import get_buff_color
from ..protocols import GameControllerProtocol, GameRendererProtocol, RewardSystemProtocol
from ..rendering.entity_renderer import EntityRenderer
from ..rendering.game_renderer import GameEntities


class UIManager:
    """UI manager — coordinates rendering delegation and overlay display.

    Routes rendering calls to the appropriate renderer (GameRenderer,
    HUDRenderer) and manages UI overlay state (reward selector, pause).

    Attributes:
        _game_renderer: GameRenderer for entity and background rendering.
        _reward_system: RewardSystem for buff stats display.
        _game_controller: GameController for state access.
    """

    def __init__(
        self,
        game_renderer: GameRendererProtocol,
        game_controller: GameControllerProtocol,
        reward_system: RewardSystemProtocol,
    ):
        self._game_renderer = game_renderer
        self._game_controller = game_controller
        self._reward_system = reward_system
        self._entity_renderer = EntityRenderer()

    def set_player_docked(self, docked: bool) -> None:
        """Set the player-docked visual state for entity rendering."""
        self._entity_renderer.player_docked = docked

    def render_game(
        self,
        surface: pygame.Surface,
        player,
        enemies,
        boss,
    ) -> None:
        entities = GameEntities(player, enemies, boss)
        self._game_renderer.render(surface, self._game_controller.state, entities)

    def render_bullets(self, surface: pygame.Surface, player, enemy_bullets) -> None:
        for bullet in player.get_bullets():
            self._entity_renderer.render_bullet(surface, bullet)
        for bullet in enemy_bullets:
            self._entity_renderer.render_bullet(surface, bullet)

    def render_hud(self, surface: pygame.Surface, player) -> None:
        state = self._game_controller.state

        unlocked_buffs = getattr(self._reward_system, "unlocked_buffs", [])

        difficulty_manager = self._game_controller.difficulty_manager
        current_coefficient = difficulty_manager.get_current_multiplier()
        initial_coefficient = difficulty_manager.initial_multiplier

        self._game_renderer.render_hud(
            surface,
            state.score,
            state.difficulty,
            player.health,
            player.max_health,
            state.kill_count,
            self._game_controller.get_next_progress(),
            boss_kills=getattr(state, "boss_kill_count", 0),
            unlocked_buffs=unlocked_buffs,
            get_buff_color=get_buff_color,
            current_coefficient=current_coefficient,
            initial_coefficient=initial_coefficient,
        )

    def render_notification(self, surface: pygame.Surface) -> None:
        state = self._game_controller.state
        self._game_renderer.render_notification(surface, state.notification, state.notification_timer)

    def render_buff_stats_panel(self, surface: pygame.Surface, player) -> None:
        self._game_renderer.render_buff_stats_panel(surface, self._reward_system, player)
        self._game_renderer.render_attack_mode_panel(surface, self._reward_system)
