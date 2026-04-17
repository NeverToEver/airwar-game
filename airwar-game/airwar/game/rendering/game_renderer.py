import pygame
from dataclasses import dataclass
from typing import List
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.controllers.game_controller import GameState
from airwar.game.rendering.background_renderer import BackgroundRenderer
from airwar.utils.render_cache import SurfaceCache


@dataclass
class GameEntities:
    player: any
    enemies: List
    boss: any


class GameRenderer:
    def __init__(self, hud_renderer: HUDRenderer = None):
        self.hud_renderer = hud_renderer or HUDRenderer()
        self.background_renderer: BackgroundRenderer = None
        self._entrance_buffer: pygame.Surface | None = None
        self._entrance_buffer_size: tuple[int, int] | None = None

    def init_background(self, screen_width: int, screen_height: int) -> None:
        self.background_renderer = BackgroundRenderer(screen_width, screen_height)

    def _get_entrance_buffer(self, size: tuple[int, int]) -> pygame.Surface:
        if self._entrance_buffer is None or self._entrance_buffer_size != size:
            self._entrance_buffer = pygame.Surface(size, pygame.SRCALPHA)
            self._entrance_buffer_size = size
        return self._entrance_buffer

    def render(self, surface: pygame.Surface, state: GameState, entities: GameEntities) -> None:
        if self.background_renderer:
            self.background_renderer.update()
            self.background_renderer.draw(surface)
        else:
            surface.fill((10, 10, 30))

        if state.entrance_animation:
            self._render_entrance(surface, state, entities)
        else:
            self._render_game(surface, state, entities)

    def _render_entrance(self, surface, state, entities):
        progress = state.entrance_timer / state.entrance_duration
        zoom_scale = 1.0 + (1.5 - 1.0) * (1 - progress)
        width, height = surface.get_size()
        entrance_buffer = self._get_entrance_buffer((width, height))
        entrance_buffer.blit(surface, (0, 0))

        if not state.player_invincible or (state.invincibility_timer // 5) % 2 == 0:
            if entities.player:
                entities.player.render(entrance_buffer)

        for enemy in entities.enemies:
            enemy.render(entrance_buffer)

        if entities.boss:
            entities.boss.render(entrance_buffer)

        scaled_width = int(width * zoom_scale)
        scaled_height = int(height * zoom_scale)
        scaled_surface = pygame.transform.smoothscale(entrance_buffer, (scaled_width, scaled_height))

        x_offset = (scaled_width - width) // 2
        y_offset = (scaled_height - height) // 2
        surface.fill((0, 0, 0))
        surface.blit(scaled_surface, (-x_offset, -y_offset))
        surface.blit(SurfaceCache.get_fade_overlay(width, height, int(80 * (1 - progress))), (0, 0))

    def _render_game(self, surface, state, entities):
        if not state.player_invincible or (state.invincibility_timer // 5) % 2 == 0:
            if entities.player:
                entities.player.render(surface)

        for enemy in entities.enemies:
            enemy.render(surface)

        if entities.boss:
            entities.boss.render(surface)
            self.hud_renderer.render_boss_health_bar(surface, entities.boss)

        self.hud_renderer.render_ripples(surface, state.ripple_effects)

    def render_hud(
        self,
        surface,
        score: int,
        difficulty: str,
        player_health: int,
        player_max_health: int,
        kills: int,
        next_threshold: float,
        cycle_count: int,
        max_cycles: int,
        boss_kills: int = 0
    ) -> None:
        self.hud_renderer.render_hud(
            surface, score, difficulty,
            player_health, player_max_health, kills,
            next_threshold, cycle_count, max_cycles,
            boss_kills=boss_kills
        )

    def render_notification(self, surface, notification: str, timer: int) -> None:
        self.hud_renderer.render_notification(surface, notification, timer)

    def render_buffs(self, surface, unlocked_buffs: list, get_buff_color) -> None:
        self.hud_renderer.render_buffs(surface, unlocked_buffs, get_buff_color)

    def render_buff_stats_panel(self, surface, reward_system, player) -> None:
        self.hud_renderer.render_buff_stats_panel(surface, reward_system, player)
