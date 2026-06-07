"""Player hitbox component.

Owns: hitbox dimensions, the diamond hitbox indicator, alpha pulse,
and the cached glow surface.

Extracted from the original 755-line Player god class (Phase 4 W-delta).
The hitbox rect is read by :class:`Player.get_hitbox` and by all
collision strategies.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config import (
    HITBOX_INDICATOR_ALPHA_MAX,
    HITBOX_INDICATOR_ALPHA_MIN,
    HITBOX_INDICATOR_FREQUENCY,
    HITBOX_INDICATOR_PADDING,
)

if TYPE_CHECKING:
    from airwar.entities.player import Player


class PlayerHitbox:
    """Hitbox rect, glow surface, and pulse animation.

    Args:
        owner: The Player instance (reads ``rect`` for hitbox centering).
    """

    DEFAULT_WIDTH = 10
    DEFAULT_HEIGHT = 14

    def __init__(self, owner: Player) -> None:
        self._owner = owner
        self.hitbox_width: int = self.DEFAULT_WIDTH
        self.hitbox_height: int = self.DEFAULT_HEIGHT
        self._render_hitbox: bool = False
        self._glow_surf: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_hitbox(self) -> pygame.Rect:
        owner = self._owner
        hb_x = owner.rect.x + (owner.rect.width - self.hitbox_width) // 2
        hb_y = owner.rect.y + (owner.rect.height - self.hitbox_height) // 2
        return pygame.Rect(hb_x, hb_y, self.hitbox_width, self.hitbox_height)

    def is_colliding_with(self, other) -> bool:
        return self.get_hitbox().colliderect(other.rect)

    def set_render_hitbox(self, value: bool) -> None:
        self._render_hitbox = value

    def render_indicator(self, surface: pygame.Surface, hitbox_timer: int) -> None:
        if not self._render_hitbox:
            return
        hb = self.get_hitbox()
        padding = HITBOX_INDICATOR_PADDING
        cx = hb.width / 2 + padding
        cy = hb.height / 2 + padding
        pulse = abs(math.sin(hitbox_timer * HITBOX_INDICATOR_FREQUENCY))

        half_w = hb.width / 2
        half_h = hb.height / 2

        diamond_points = [
            (cx, cy - half_h),
            (cx + half_w, cy),
            (cx, cy + half_h),
            (cx - half_w, cy),
        ]

        alpha_range = HITBOX_INDICATOR_ALPHA_MAX - HITBOX_INDICATOR_ALPHA_MIN
        alpha = int(HITBOX_INDICATOR_ALPHA_MIN + pulse * alpha_range)

        # Reuse cached surface to avoid per-frame SRCALPHA allocation
        surf_size = (hb.width + padding * 2, hb.height + padding * 2)
        if self._glow_surf is None or self._glow_surf.get_size() != surf_size:
            self._glow_surf = pygame.Surface(surf_size, pygame.SRCALPHA)
        self._glow_surf.fill((0, 0, 0, 0))
        pygame.draw.polygon(self._glow_surf, (255, 255, 255, alpha), diamond_points)

        surface.blit(self._glow_surf, (hb.x - padding, hb.y - padding))

    def render_precision_indicator(self, surface: pygame.Surface, hitbox_timer: int) -> None:
        """Subtle ring indicator around the ship during precision (CTRL)."""
        owner = self._owner
        pulse = 0.6 + 0.4 * abs(math.sin(hitbox_timer * 0.06))
        radius = int((owner.rect.width + owner.rect.height) // 4 + 8)
        alpha = int(55 + 20 * pulse)
        indicator = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(
            indicator,
            (100, 180, 220, alpha),
            (radius + 2, radius + 2),
            radius,
            1,
        )
        surface.blit(indicator, indicator.get_rect(center=(owner.rect.centerx, owner.rect.centery)))
