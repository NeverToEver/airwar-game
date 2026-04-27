"""Game renderer — entity rendering, background, and death animation."""
import pygame
from dataclasses import dataclass
from typing import List
from .hud_renderer import HUDRenderer
from .integrated_hud import IntegratedHUD
from ..managers.game_controller import GameState, GameplayState
from .game_rendering_background import SpaceBackground
from ..death_animation import DeathAnimation


@dataclass
class GameEntities:
    """Game entities container dataclass — player, enemies, boss."""
    player: any
    enemies: List
    boss: any


class GameRenderer:
    """Game renderer — entity rendering, background, and death animation.
    
        Handles the main game rendering pipeline: background → entities →
        effects → HUD. Supports entrance animation zoom effect and death
        animation transitions.
    
        Attributes:
            hud_renderer: HUDRenderer for heads-up display.
            background_renderer: SpaceBackground for parallax starfield.
            _death_animation: DeathAnimation instance during player death.
        """
    def __init__(self, hud_renderer: HUDRenderer = None, use_integrated_hud: bool = True):
        self.hud_renderer = hud_renderer or HUDRenderer()
        self.integrated_hud = IntegratedHUD() if use_integrated_hud else None
        self.background_renderer: SpaceBackground = None
        self._death_animation = None
        self._screen_diagonal = 0
        self._was_in_dying_state = False

    def init_background(self, screen_width: int, screen_height: int) -> None:
        self.background_renderer = SpaceBackground(screen_width, screen_height)
        self._screen_diagonal = int((screen_width ** 2 + screen_height ** 2) ** 0.5)

    def render(self, surface: pygame.Surface, state: GameState, entities: GameEntities) -> None:
        is_dying = state.gameplay_state == GameplayState.DYING
        is_game_over = state.gameplay_state == GameplayState.GAME_OVER

        if not is_dying and not is_game_over:
            if self.background_renderer:
                self.background_renderer.update()
                self.background_renderer.draw(surface)
            else:
                surface.fill((10, 10, 30))
        else:
            if self.background_renderer:
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

        if not state.player_invincible or state.silent_invincible or (state.invincibility_timer // 5) % 2 == 0:
            if entities.player:
                entities.player.render(surface)

        for enemy in entities.enemies:
            enemy.render(surface)

        if entities.boss:
            entities.boss.render(surface)

        scaled_width = int(surface.get_width() * zoom_scale)
        scaled_height = int(surface.get_height() * zoom_scale)
        
        cached_key = (scaled_width, scaled_height)
        if not hasattr(self, '_entrance_cache') or self._entrance_cache_key != cached_key:
            self._entrance_scaled_surface = pygame.transform.scale(surface, (scaled_width, scaled_height))
            self._entrance_cache_key = cached_key

        x_offset = (scaled_width - surface.get_width()) // 2
        y_offset = (scaled_height - surface.get_height()) // 2
        surface.fill((0, 0, 0))
        surface.blit(self._entrance_scaled_surface, (-x_offset, -y_offset))

        if not hasattr(self, '_fade_surface') or self._fade_surface.get_size() != surface.get_size():
            self._fade_surface = pygame.Surface(surface.get_size())
        self._fade_surface.set_alpha(int(80 * (1 - progress)))
        surface.blit(self._fade_surface, (0, 0))

    def _render_game(self, surface, state, entities):
        is_dying = state.gameplay_state == GameplayState.DYING

        if is_dying:
            if entities.player:
                entities.player.render(surface)

            for enemy in entities.enemies:
                enemy.render(surface)

            if entities.boss:
                entities.boss.render(surface)

            self.hud_renderer.render_ripples(surface, state.ripple_effects)

            self._render_death_animation(surface, state, entities)
        else:
            if not state.player_invincible or state.silent_invincible or (state.invincibility_timer // 5) % 2 == 0:
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
        next_progress: int,
        boss_kills: int = 0,
        unlocked_buffs: list = None,
        get_buff_color=None,
        current_coefficient: float = None,
        initial_coefficient: float = None
    ) -> None:
        if self.integrated_hud:
            self.integrated_hud.render(
                surface,
                score,
                difficulty,
                player_health,
                player_max_health,
                kills,
                next_progress,
                boss_kills,
                unlocked_buffs,
                get_buff_color,
                current_coefficient,
                initial_coefficient
            )
        else:
            self.hud_renderer.render_hud(
                surface, score, difficulty,
                player_health, player_max_health, kills,
                next_progress,
                boss_kills=boss_kills
            )

    def render_notification(self, surface, notification: str, timer: int) -> None:
        self.hud_renderer.render_notification(surface, notification, timer)

    def render_buffs(self, surface, unlocked_buffs: list, get_buff_color) -> None:
        if not self.integrated_hud:
            self.hud_renderer.render_buffs(surface, unlocked_buffs, get_buff_color)

    def render_buff_stats_panel(self, surface, reward_system, player) -> None:
        if not self.integrated_hud:
            self.hud_renderer.render_buff_stats_panel(surface, reward_system, player)

    def render_attack_mode_panel(self, surface, reward_system) -> None:
        self.hud_renderer.render_attack_mode_panel(surface, reward_system)

    def _render_death_animation(self, surface, state, entities):
        is_dying = state.gameplay_state == GameplayState.DYING

        if is_dying and not self._was_in_dying_state:
            self._death_animation = DeathAnimation()
            if entities.player:
                self._death_animation.trigger(
                    entities.player.rect.centerx,
                    entities.player.rect.centery,
                    self._screen_diagonal
                )
            self._was_in_dying_state = True

        if self._death_animation is not None and self._death_animation.is_active():
            self._death_animation.render(surface)
        elif not is_dying:
            self._death_animation = None
            self._was_in_dying_state = False

    def update_death_animation(self) -> bool:
        if self._death_animation is not None:
            return self._death_animation.update()
        return False
