"""Entity rendering for the tutorial scene.

Draws the simulated world entities onto the surface: player bullets,
enemy bullets, enemies, the boss, the crosshair, and the player ship.
Also owns the per-entity health-bar helpers used in the world layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.i18n import t
from airwar.utils.sprites import (
    draw_boss_ship,
    draw_bullet,
    draw_enemy_ship,
    draw_player_ship,
)

if TYPE_CHECKING:
    from airwar.scenes.tutorial.renderers.effect_renderer import EffectRenderer
    from airwar.scenes.tutorial_scene import TutorialScene


class EntityRenderer:
    """Draw world entities (bullets, enemies, boss, player).

    The actual boss enrage aura / warning are visual effects and live
    on :class:`EffectRenderer`; this class delegates to it so callers
    can still pass ``self`` to the original ``_render_world`` flow.
    """

    def __init__(
        self,
        scene: TutorialScene,
        effect_renderer: EffectRenderer,
    ) -> None:
        self._scene = scene
        self._effects = effect_renderer

    def render_world(self, surface: pygame.Surface) -> None:
        """Render the world layer: bullets, enemies, boss, crosshair, player."""
        s = self._scene
        render_hostiles = not (s._stage.id == "mothership_docking" and s._dock_sub_phase == "eject_player")
        if render_hostiles:
            self.render_bullets(surface)
            self.render_enemies(surface)

        if s._boss is not None:
            self.render_boss(surface, s._boss)

        s._aim_crosshair.render(surface, s._aim_pos)
        self.render_player(surface)

    def render_bullets(self, surface: pygame.Surface) -> None:
        """Draw every active player and enemy bullet."""
        s = self._scene
        for bullet in s._bullets:
            draw_bullet(
                surface,
                bullet.rect.x,
                bullet.rect.y,
                bullet.rect.width,
                bullet.rect.height,
                "single",
                "player",
            )
        for bullet in s._enemy_bullets:
            draw_bullet(
                surface,
                bullet.rect.x,
                bullet.rect.y,
                bullet.rect.width,
                bullet.rect.height,
                bullet.bullet_type,
                "enemy",
            )

    def render_enemies(self, surface: pygame.Surface) -> None:
        """Draw every active enemy plus its floating health bar."""
        s = self._scene
        for enemy in s._enemies:
            health_ratio = max(0.0, enemy.health / enemy.max_health)
            draw_enemy_ship(
                surface,
                enemy.rect.centerx,
                enemy.rect.centery,
                enemy.rect.width,
                enemy.rect.height,
                health_ratio,
            )
            self._draw_entity_health_bar(surface, enemy.rect, health_ratio)

    def render_boss(self, surface: pygame.Surface, boss) -> None:
        """Draw the boss with its enrage aura/warning and armor bar."""
        health_ratio = max(0.0, boss.health / boss.max_health)
        if boss.enraged:
            self._effects.render_boss_enrage_aura(surface, boss)
        draw_boss_ship(
            surface,
            boss.rect.centerx,
            boss.rect.centery,
            boss.rect.width,
            boss.rect.height,
            health_ratio,
        )
        self._draw_boss_health(surface, boss)
        if boss.enraged:
            self._effects.render_boss_enrage_warning(surface, boss)

    def render_player(self, surface: pygame.Surface) -> None:
        """Draw the simulated player ship (skip frames when in hit cooldown)."""
        s = self._scene
        if s._player_hit_cooldown > 0 and (s._animation_time // 4) % 2 == 0:
            return
        if s._dash_frames > 0:
            dash_glow = pygame.Surface((96, 96), pygame.SRCALPHA)
            pygame.draw.circle(
                dash_glow,
                (*SceneColors.ACCENT_TEAL_BRIGHT, 55),
                (48, 48),
                42,
            )
            surface.blit(dash_glow, dash_glow.get_rect(center=s._player.center))
        draw_player_ship(surface, s._player.centerx, s._player.centery, s.PLAYER_W, s.PLAYER_H)

    # -- Health bar helpers ----------------------------------------------

    def _draw_entity_health_bar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
    ) -> None:
        """Draw a small health bar above an enemy entity."""
        bar = pygame.Rect(rect.x, rect.y - 13, rect.width, 5)
        pygame.draw.rect(surface, SceneColors.BOSS_BAR_EMPTY, bar)
        fill = bar.copy()
        fill.width = int(bar.width * ratio)
        pygame.draw.rect(surface, SceneColors.HEALTH_LOW, fill)

    def _draw_boss_health(self, surface: pygame.Surface, boss) -> None:
        """Draw the centred boss armor bar with enraged/calm label."""
        s = self._scene
        sw = surface.get_width()
        bar = pygame.Rect(sw // 2 - 230, 196, 460, 16)
        ratio = max(0.0, boss.health / boss.max_health)
        pygame.draw.rect(surface, SceneColors.BOSS_BAR_EMPTY, bar, border_radius=4)
        color = SceneColors.DANGER_RED if boss.enraged else SceneColors.BOSS_BAR_FULL
        fill = bar.copy()
        fill.width = int(bar.width * ratio)
        pygame.draw.rect(surface, color, fill, border_radius=4)
        pygame.draw.rect(surface, SceneColors.BORDER_DIM, bar, 1, border_radius=4)
        label = t("tutorial.boss_armor_enrage") if boss.enraged else t("tutorial.boss_armor")
        text = s._small_font.render(label, True, color)
        surface.blit(text, text.get_rect(midbottom=(bar.centerx, bar.y - 3)))
