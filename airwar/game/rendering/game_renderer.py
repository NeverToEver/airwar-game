"""Game renderer — entity rendering, background, and death animation."""

from dataclasses import dataclass
from typing import Any

import pygame

from ..death_animation import DeathAnimation
from ..managers.game_controller import GameplayState, GameState
from .entity_renderer import EntityRenderer
from .game_rendering_background import SpaceBackground
from .hud_renderer import HUDRenderer
from .integrated_hud import IntegratedHUD


@dataclass
class GameEntities:
    """Game entities container dataclass — player, enemies, boss."""

    player: Any
    enemies: list
    boss: Any


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
        self.entity_renderer = EntityRenderer()
        self.background_renderer: SpaceBackground = None
        self._death_animation = None
        self._screen_diagonal = 0
        self._was_in_dying_state = False
        self._invincibility_aura_cache = None
        self._invincibility_aura_key = None

    def init_background(self, screen_width: int, screen_height: int) -> None:
        self.background_renderer = SpaceBackground(screen_width, screen_height)
        self._screen_diagonal = int((screen_width**2 + screen_height**2) ** 0.5)

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

        if state.is_entrance_playing:
            self._render_entrance(surface, state, entities)
        else:
            self._render_game(surface, state, entities)

    def _render_entrance(self, surface, state, entities):
        progress = state.entrance_timer / state.entrance_duration

        self._render_player(surface, state, entities.player)

        for enemy in entities.enemies:
            self.entity_renderer.render_enemy(surface, enemy)

        if entities.boss:
            self.entity_renderer.render_boss(surface, entities.boss)

        fade_alpha = int(160 * (1 - progress))
        if fade_alpha > 0:
            if not hasattr(self, "_entrance_fade") or self._entrance_fade.get_size() != surface.get_size():
                self._entrance_fade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                self._entrance_fade.fill((0, 0, 0))
            self._entrance_fade.set_alpha(fade_alpha)
            surface.blit(self._entrance_fade, (0, 0))

    def _render_game(self, surface, state, entities):
        is_dying = state.gameplay_state == GameplayState.DYING

        if is_dying:
            if entities.player:
                entities.player.render(surface)

            for enemy in entities.enemies:
                self.entity_renderer.render_enemy(surface, enemy)

            if entities.boss:
                self.entity_renderer.render_boss(surface, entities.boss)

            self.hud_renderer.render_ripples(surface, state.ripple_effects)

            self._render_death_animation(surface, state, entities)
        else:
            self._render_player(surface, state, entities.player)

            for enemy in entities.enemies:
                self.entity_renderer.render_enemy(surface, enemy)

            if entities.boss:
                self.entity_renderer.render_boss(surface, entities.boss)
                self.hud_renderer.render_boss_health_bar(surface, entities.boss)

            self.hud_renderer.render_ripples(surface, state.ripple_effects)

    def _render_player(self, surface, state, player) -> None:
        if not player:
            return
        player.render(surface)
        if state.is_player_invincible and not state.is_silent_invincible:
            self._render_invincibility_aura(surface, player)

    def _render_invincibility_aura(self, surface, player) -> None:
        width = max(1, int(player.rect.width * 1.45))
        height = max(1, int(player.rect.height * 1.35))
        cache_key = (width, height)
        if self._invincibility_aura_key != cache_key:
            aura = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.ellipse(aura, (96, 214, 224, 38), aura.get_rect(), 2)
            inner = aura.get_rect().inflate(-max(4, width // 4), -max(4, height // 4))
            pygame.draw.ellipse(aura, (140, 232, 238, 24), inner, 1)
            self._invincibility_aura_cache = aura
            self._invincibility_aura_key = cache_key
        surface.blit(self._invincibility_aura_cache, self._invincibility_aura_cache.get_rect(center=player.rect.center))

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
        unlocked_buffs: list | None = None,
        get_buff_color=None,
        current_coefficient: float | None = None,
        initial_coefficient: float | None = None,
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
                initial_coefficient,
            )
        else:
            self.hud_renderer.render_hud(
                surface,
                score,
                difficulty,
                player_health,
                player_max_health,
                kills,
                next_progress,
                boss_kills=boss_kills,
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
                    entities.player.rect.centerx, entities.player.rect.centery, self._screen_diagonal
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
