"""Landing / handoff phase renderer -- LANDING + HANDOFF + final fade overlay."""

import math

import pygame

from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.homecoming._constants import (
    PHASE_BASE_LAUNCH,
    PHASE_BLACKOUT,
    PHASE_HANDOFF,
    PHASE_LANDING,
    PHASE_STATION_REVEAL,
)
from airwar.utils.fonts import get_cjk_font
from airwar.utils.sprites import draw_glow_circle, draw_player_ship


class LandingHandoffRenderer:
    """Renders LANDING + HANDOFF phases and the per-phase fade overlay."""

    def __init__(self) -> None:
        self._font = get_cjk_font(18)

    def render_landing_player(
        self,
        surface: pygame.Surface,
        sequence,
        player,
        progress: float,
        phase: str,
    ) -> None:
        """Draw the LANDING / HANDOFF phase player sprite + entry trail."""
        x, y = sequence.get_player_center()
        if phase == PHASE_LANDING:
            scale = 0.96 - 0.12 * progress
        else:
            scale = 0.84 * (1 - progress) + 0.16 * progress
            entry_x, entry_y = sequence.get_base_entry_center()
            trail_alpha = int(115 * (1 - progress))
            if trail_alpha > 0:
                pygame.draw.line(
                    surface,
                    (145, 238, 222, trail_alpha),
                    (int(x), int(y)),
                    (int(entry_x), int(entry_y)),
                    max(2, int(8 * (1 - progress))),
                )

        if phase == PHASE_HANDOFF and progress >= 0.96:
            return

        width = max(22, int(player.rect.width * scale))
        height = max(26, int(player.rect.height * scale))
        draw_player_ship(surface, x, y, width, height)

    def render_docking_corridor(
        self,
        surface: pygame.Surface,
        sequence,
        progress: float,
    ) -> None:
        """Draw the HANDOFF docking corridor guide + landing pad rings."""
        entry_x, entry_y = sequence.get_base_entry_center()
        landing_x, landing_y = sequence.get_landing_center()
        alpha = int(220 + 35 * math.sin(progress * math.pi * 5))

        guide = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.line(
            guide,
            (72, 210, 190, 120),
            (int(landing_x), int(landing_y)),
            (int(entry_x), int(entry_y)),
            3,
        )
        for i in range(6):
            t = (i + 1) / 7
            gx = int(landing_x + (entry_x - landing_x) * t)
            gy = int(landing_y + (entry_y - landing_y) * t)
            draw_glow_circle(guide, (gx, gy), 4, (90, 235, 210), 14)
            pygame.draw.circle(guide, (190, 255, 245, 200), (gx, gy), 2)

        for radius in (54, 34, 18):
            ring_alpha = max(55, alpha - radius * 2)
            ring_color = (90, 236, 214, ring_alpha)
            pygame.draw.circle(guide, ring_color, (int(entry_x), int(entry_y)), radius, 2)
        draw_glow_circle(guide, (int(entry_x), int(entry_y)), 18, (80, 230, 210), 58)
        surface.blit(guide, (0, 0))

    def render_handoff(self, surface: pygame.Surface, progress: float) -> None:
        """Draw the HANDOFF phase '基地接入中' panel."""
        sw, sh = surface.get_size()
        panel_w = 360
        panel_h = 42
        x = sw // 2 - panel_w // 2
        y = int(sh * 0.77)
        alpha = int(210 * min(1.0, progress * 2))
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        draw_chamfered_panel(panel, 0, 0, panel_w, panel_h, (12, 22, 34), (82, 210, 190), None, 7)
        panel.set_alpha(alpha)
        surface.blit(panel, (x, y))
        text = self._font.render("基地接入中", True, (214, 242, 238))
        text.set_alpha(alpha)
        surface.blit(text, text.get_rect(center=(sw // 2, y + panel_h // 2)))

    def render_fade_overlay(self, surface: pygame.Surface, phase: str, progress: float) -> None:
        """Draw the per-phase fade overlay (BLACKOUT/STATION_REVEAL/HANDOFF/BASE_LAUNCH)."""
        if phase == PHASE_BLACKOUT:
            alpha = 255
        elif phase == PHASE_STATION_REVEAL:
            alpha = int(255 * (1 - progress))
        elif phase == PHASE_HANDOFF:
            alpha = int(210 * progress)
        elif phase == PHASE_BASE_LAUNCH:
            alpha = int(230 * max(0.0, (progress - 0.76) / 0.24))
        else:
            alpha = 0

        if alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))
