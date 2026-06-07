"""Approach / launch / strike phase renderer.

Handles three phase groups:
- APPROACH (camera pan toward landing pad; player trail)
- BASE_LAUNCH (launch corridor + player catapult animation)
- ORBITAL_STRIKE (post-departure enemy-clear strike)
"""

import math

import pygame

from airwar.utils.sprites import draw_glow_circle, draw_player_ship


class ApproachCameraRenderer:
    """Renders the approach pan, launch corridor, and orbital strike."""

    LAUNCH_CORRIDOR_PULSE_CYCLES = 1.5
    LAUNCH_CORRIDOR_LINE_ALPHA_BASE = 92
    LAUNCH_CORRIDOR_LINE_ALPHA_RANGE = 24
    LAUNCH_CORRIDOR_RING_ALPHA_RATIO_BASE = 0.72
    LAUNCH_CORRIDOR_RING_ALPHA_RATIO_RANGE = 0.18

    def render_approach(
        self,
        surface: pygame.Surface,
        sequence,
        player,
        progress: float,
    ) -> None:
        """Draw the APPROACH phase player sprite with trail."""
        x, y = sequence.get_player_center()
        scale = 0.58 + 0.38 * progress
        trail_alpha = int(140 * (1 - progress))
        if trail_alpha > 0:
            trail_color = (225, 245, 255, trail_alpha)
            pygame.draw.line(surface, trail_color, (int(x), int(y + 70)), (int(x), int(y + 170)), 10)

        width = max(22, int(player.rect.width * scale))
        height = max(26, int(player.rect.height * scale))
        draw_player_ship(surface, x, y, width, height)

    def render_launch_corridor(
        self,
        surface: pygame.Surface,
        sequence,
        progress: float,
    ) -> None:
        """Draw BASE_LAUNCH phase launch guide corridor."""
        entry_x, entry_y = sequence.get_base_entry_center()
        sw, sh = surface.get_size()
        guide = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(progress * math.tau * self.LAUNCH_CORRIDOR_PULSE_CYCLES)

        pygame.draw.line(
            guide,
            (72, 222, 210, self.LAUNCH_CORRIDOR_LINE_ALPHA_BASE + int(self.LAUNCH_CORRIDOR_LINE_ALPHA_RANGE * pulse)),
            (int(entry_x), int(entry_y)),
            (int(entry_x), sh + 80),
            5,
        )
        for index in range(9):
            t = index / 8
            ring_y = int(entry_y + (sh - entry_y) * t + progress * 42) % max(1, sh + 60)
            ring_y = max(int(entry_y), ring_y)
            ring_w = int(80 + 280 * t)
            ring_h = max(12, int(24 + 58 * t))
            alpha = int(
                (88 - 46 * t)
                * (self.LAUNCH_CORRIDOR_RING_ALPHA_RATIO_BASE + self.LAUNCH_CORRIDOR_RING_ALPHA_RATIO_RANGE * pulse)
            )
            rect = pygame.Rect(0, 0, ring_w, ring_h)
            rect.center = (int(entry_x), ring_y)
            pygame.draw.ellipse(guide, (90, 238, 220, alpha), rect, 2)

        draw_glow_circle(guide, (int(entry_x), int(entry_y + 18)), 24, (82, 238, 218), 78)
        surface.blit(guide, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def render_launch_player(
        self,
        surface: pygame.Surface,
        sequence,
        player,
        progress: float,
    ) -> None:
        """Draw BASE_LAUNCH phase player being catapulted from base."""
        x, y = sequence.get_player_center()
        entry_x, entry_y = sequence.get_base_entry_center()
        trail_alpha = int(190 * max(0.0, 1.0 - progress * 0.9))
        if trail_alpha > 0:
            width = max(4, int(24 * (1.0 - progress) + 5))
            trail_color = (226, 248, 255, trail_alpha)
            pygame.draw.line(surface, trail_color, (int(entry_x), int(entry_y)), (int(x), int(y)), width)
            draw_glow_circle(surface, (int(entry_x), int(entry_y)), 18, (236, 250, 255), 64)

        scale = 0.58 + 0.64 * progress
        width = max(22, int(player.rect.width * scale))
        height = max(26, int(player.rect.height * scale))
        sprite = pygame.Surface((width * 3, height * 3), pygame.SRCALPHA)
        draw_player_ship(sprite, sprite.get_width() / 2, sprite.get_height() / 2, width, height)
        sprite = pygame.transform.rotate(sprite, 180)
        surface.blit(sprite, sprite.get_rect(center=(int(x), int(y))))

    def render_orbital_strike(
        self,
        surface: pygame.Surface,
        sequence,
        progress: float,
    ) -> None:
        """Draw the ORBITAL_STRIKE phase (targeting reticle, missile, impact, ring)."""
        sw, sh = surface.get_size()
        impact_progress = sequence.ORBITAL_STRIKE_IMPACT_PROGRESS
        impact_x = sw // 2
        impact_y = int(sh * 0.42)

        reveal = min(1.0, progress / 0.30)
        if reveal < 1.0:
            overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(210 * (1.0 - reveal))))
            surface.blit(overlay, (0, 0))

        targeting = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(progress * math.tau * 1.5)
        for radius in (52, 88, 128):
            alpha = int(36 + 22 * pulse)
            pygame.draw.circle(targeting, (82, 236, 218, alpha), (impact_x, impact_y), radius, 2)
        pygame.draw.line(targeting, (82, 236, 218, 52), (impact_x - 170, impact_y), (impact_x + 170, impact_y), 1)
        pygame.draw.line(targeting, (82, 236, 218, 52), (impact_x, impact_y - 150), (impact_x, impact_y + 150), 1)

        if progress < impact_progress:
            t = progress / max(0.001, impact_progress)
            eased = t * t
            missile_y = int(-140 + (impact_y + 120) * eased)
            trail_len = int(160 + 420 * t)
            pygame.draw.line(
                targeting,
                (188, 230, 236, 148),
                (impact_x, missile_y - trail_len),
                (impact_x, missile_y + 18),
                max(4, int(12 - 5 * t)),
            )
            draw_glow_circle(targeting, (impact_x, missile_y), 10, (180, 230, 236), 30)
            pygame.draw.polygon(
                targeting,
                (214, 236, 238, 170),
                [(impact_x, missile_y + 28), (impact_x - 9, missile_y - 12), (impact_x + 9, missile_y - 12)],
            )
            surface.blit(targeting, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            return

        t = (progress - impact_progress) / max(0.001, 1.0 - impact_progress)
        flash_alpha = int(48 * max(0.0, 1.0 - t * 2.2))
        if flash_alpha > 0:
            flash = pygame.Surface((sw, sh), pygame.SRCALPHA)
            flash.fill((140, 210, 220, flash_alpha))
            surface.blit(flash, (0, 0))

        beam_alpha = int(92 * max(0.0, 1.0 - t))
        if beam_alpha > 0:
            beam_w = max(14, int(42 * (1.0 - t) + 14))
            beam_color = (162, 226, 232, beam_alpha)
            pygame.draw.line(targeting, beam_color, (impact_x, -40), (impact_x, sh + 40), beam_w)

        ring_radius = int(max(sw, sh) * (0.08 + 1.08 * t))
        ring_alpha = int(82 * max(0.0, 1.0 - t))
        if ring_alpha > 0:
            pygame.draw.circle(targeting, (168, 246, 236, ring_alpha), (impact_x, impact_y), ring_radius, 5)
            inner_ring_color = (184, 236, 232, int(ring_alpha * 0.55))
            inner_ring_r = max(12, ring_radius // 5)
            pygame.draw.circle(targeting, inner_ring_color, (impact_x, impact_y), inner_ring_r, 3)
            for side in (-1, 1):
                pygame.draw.line(
                    targeting,
                    (164, 226, 232, int(ring_alpha * 0.48)),
                    (impact_x, impact_y),
                    (impact_x + side * sw, int(impact_y + sh * 0.32 * t)),
                    3,
                )

        surface.blit(targeting, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
