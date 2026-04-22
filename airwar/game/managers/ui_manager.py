from typing import Protocol, List
import pygame


class GameRendererProtocol(Protocol):
    def render(self, surface, state, entities) -> None: ...
    def render_hud(
        self, surface, score, difficulty, health, max_health, kill_count,
        threshold, cycle_count, milestone_index, boss_kills=0
    ) -> None: ...
    def render_notification(self, surface, notification, timer) -> None: ...
    def render_buff_stats_panel(self, surface, reward_system, player) -> None: ...
    def update_death_animation(self) -> None: ...


class RewardSystemProtocol(Protocol):
    @property
    def unlocked_buffs(self) -> List[str]: ...


class GameControllerProtocol(Protocol):
    @property
    def state(self): ...
    def get_next_threshold(self) -> float: ...
    @property
    def cycle_count(self) -> int: ...
    @property
    def milestone_index(self) -> int: ...
    @property
    def max_cycles(self) -> int: ...


class PlayerProtocol(Protocol):
    @property
    def health(self) -> int: ...
    @property
    def max_health(self) -> int: ...
    def get_bullets(self): ...


class GameEntities:
    def __init__(self, player, enemies, boss):
        self.player = player
        self.enemies = enemies
        self.boss = boss


class UIManager:
    def __init__(
        self,
        game_renderer: GameRendererProtocol,
        game_controller: GameControllerProtocol,
        reward_system: RewardSystemProtocol,
    ):
        self._game_renderer = game_renderer
        self._game_controller = game_controller
        self._reward_system = reward_system

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
            bullet.render(surface)
        for bullet in enemy_bullets:
            bullet.render(surface)

    def render_hud(self, surface: pygame.Surface, player) -> None:
        state = self._game_controller.state
        self._game_renderer.render_hud(
            surface,
            state.score,
            state.difficulty,
            player.health,
            player.max_health,
            state.kill_count,
            self._game_controller.get_next_progress(),
            boss_kills=getattr(state, 'boss_kill_count', 0),
        )

    def render_notification(self, surface: pygame.Surface) -> None:
        state = self._game_controller.state
        self._game_renderer.render_notification(
            surface,
            state.notification,
            state.notification_timer
        )

    def render_buff_stats_panel(self, surface: pygame.Surface, player) -> None:
        self._game_renderer.render_buff_stats_panel(
            surface,
            self._reward_system,
            player
        )
