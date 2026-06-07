"""Visual effects rendering for the tutorial scene.

Handles additive overlay effects: fading alpha rectangles, explosion
particles, and boss enrage aura/warning flashes. These are drawn on
top of entities and have no game-state meaning of their own.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.i18n import t

if TYPE_CHECKING:
    from airwar.scenes.tutorial_scene import TutorialScene


class EffectRenderer:
    """Draws fading overlays, tutorial explosions, and enrage FX.

    All methods here are pure visual effects — alpha-blended overlays
    that sit on top of the regular entity/UI layers. They do not read
    bullet / enemy lists directly; the caller (slim renderer) routes
    the right objects in.
    """

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    def render_tutorial_explosions(self, surface: pygame.Surface) -> None:
        """Draw each active tutorial explosion as a fading circle."""
        for explosion in self._scene._tutorial_explosions:
            age = explosion.duration - explosion.timer
            ratio = max(0.0, min(1.0, age / explosion.duration))
            alpha = int(210 * (1.0 - ratio))
            radius = int(12 + ratio * 34)
            layer = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            center = (layer.get_width() // 2, layer.get_height() // 2)
            pygame.draw.circle(layer, (*SceneColors.WARNING_ACCENT, alpha), center, radius)
            pygame.draw.circle(
                layer,
                (*SceneColors.DANGER_RED, max(0, alpha - 50)),
                center,
                max(3, radius // 2),
                2,
            )
            surface.blit(
                layer,
                layer.get_rect(center=explosion.center),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def render_fade(self, surface: pygame.Surface) -> None:
        """Apply the scene-level fade alpha as a full-screen black overlay."""
        if self._scene._fade_alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self._scene._fade_alpha))
        surface.blit(overlay, (0, 0))

    def render_boss_enrage_aura(self, surface: pygame.Surface, boss) -> None:
        """Draw the pulsing enrage aura around the boss sprite."""
        s = self._scene
        pulse = 0.5 + 0.5 * math.sin(s._animation_time * 0.16)
        aura_size = (
            int(boss.rect.width * (1.22 + 0.08 * pulse)),
            int(boss.rect.height * (1.20 + 0.08 * pulse)),
        )
        aura = pygame.Surface(aura_size, pygame.SRCALPHA)
        rect = aura.get_rect()
        pygame.draw.ellipse(
            aura,
            (*SceneColors.ACCENT_TEAL_BRIGHT, int(58 + 52 * pulse)),
            rect,
            4,
        )
        inner = rect.inflate(-max(8, aura_size[0] // 5), -max(8, aura_size[1] // 5))
        pygame.draw.ellipse(
            aura,
            (*SceneColors.DANGER_RED, int(42 + 38 * pulse)),
            inner,
            2,
        )
        surface.blit(
            aura,
            aura.get_rect(center=boss.rect.center),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def render_boss_enrage_warning(self, surface: pygame.Surface, boss) -> None:
        """Draw the 'CORE OVERLOAD' pulsing text above an enraged boss."""
        s = self._scene
        pulse = 0.55 + 0.45 * math.sin(s._animation_time * 0.13)
        text = s._heading_font.render(
            t("tutorial.core_overload"),
            True,
            SceneColors.ACCENT_TEAL_BRIGHT,
        )
        text.set_alpha(int(150 + 80 * pulse))
        surface.blit(text, text.get_rect(center=(boss.rect.centerx, boss.rect.y - 34)))
