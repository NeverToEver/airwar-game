"""Blackout phase renderers -- outgoing and return blackout fade with streaks."""

import pygame

from airwar.ui.homecoming._constants import PHASE_BLACKOUT, PHASE_RETURN_BLACKOUT


class BlackoutTransitionRenderer:
    """Renders both the outgoing BLACKOUT bridge and the return BLACKOUT."""

    def render(
        self,
        surface: pygame.Surface,
        phase: str,
        progress: float,
    ) -> None:
        """Dispatch to the matching blackout variant."""
        if phase == PHASE_BLACKOUT:
            self._render_blackout_bridge(surface, progress)
            return
        if phase == PHASE_RETURN_BLACKOUT:
            self._render_return_blackout(surface, progress)

    def _render_blackout_bridge(self, surface: pygame.Surface, progress: float) -> None:
        surface.fill((0, 0, 0))
        sw, sh = surface.get_size()
        center_x = sw // 2
        center_y = int(sh * 0.47)

        residue = max(0.0, 1.0 - progress / 0.42)
        if residue > 0:
            afterimage = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for index in range(11):
                offset = int((index - 5) * (18 + 76 * progress))
                alpha = int(92 * residue * (0.35 + 0.65 * (1 - abs(index - 5) / 5)))
                width = max(1, int(5 * residue))
                pygame.draw.line(
                    afterimage,
                    (216, 240, 255, alpha),
                    (center_x + offset, sh),
                    (center_x + int(offset * 0.18), int(sh * 0.08)),
                    width,
                )
            bloom = pygame.Rect(0, 0, int(180 + 160 * residue), int(sh * 0.72))
            bloom.center = (center_x, int(sh * 0.42))
            pygame.draw.ellipse(afterimage, (190, 230, 255, int(34 * residue)), bloom)
            surface.blit(afterimage, (0, 0))

        preview = max(0.0, (progress - 0.46) / 0.54)
        if preview <= 0:
            return

        reveal = preview * preview * (3 - 2 * preview)
        ghost = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ghost_alpha = int(86 * reveal)

        ring_outer = pygame.Rect(0, 0, 520, 210)
        ring_outer.center = (center_x, center_y)
        ring_inner = ring_outer.inflate(-112, -68)
        pygame.draw.ellipse(ghost, (78, 104, 126, ghost_alpha), ring_outer, 2)
        pygame.draw.ellipse(ghost, (70, 238, 218, int(ghost_alpha * 0.74)), ring_inner, 1)

        for side in (-1, 1):
            mast_start = (center_x + side * 190, center_y - 10)
            mast_end = (center_x + side * 500, center_y - 78)
            pygame.draw.line(ghost, (72, 214, 202, int(ghost_alpha * 0.56)), mast_start, mast_end, 2)

        port_center = (center_x, center_y + 18)
        pygame.draw.circle(ghost, (88, 238, 220, int(118 * reveal)), port_center, 50, 2)
        pygame.draw.circle(ghost, (192, 255, 248, int(135 * reveal)), port_center, 4)

        scan_y = int(center_y - 122 + 244 * reveal)
        scan_alpha = int(122 * reveal)
        pygame.draw.line(
            ghost,
            (126, 246, 232, scan_alpha),
            (center_x - 340, scan_y),
            (center_x + 340, scan_y),
            2,
        )
        surface.blit(ghost, (0, 0))

    def _render_return_blackout(self, surface: pygame.Surface, progress: float) -> None:
        surface.fill((0, 0, 0))
        sw, sh = surface.get_size()
        center_x = sw // 2
        streaks = pygame.Surface((sw, sh), pygame.SRCALPHA)
        fade = max(0.0, 1.0 - progress)

        for index in range(19):
            lane = index - 9
            x = center_x + int(lane * (22 + 86 * progress))
            length = int(sh * (0.38 + 0.56 * progress))
            y = int((index * 73 + progress * sh * 1.8) % (sh + length) - length)
            alpha = int(132 * fade * (0.42 + 0.58 * (1 - abs(lane) / 9)))
            width = max(1, int(5 - 3 * progress))
            pygame.draw.line(streaks, (218, 240, 255, alpha), (x, y), (center_x + lane * 5, y + length), width)

        aperture = max(0.0, (progress - 0.58) / 0.42)
        if aperture > 0:
            radius = int(36 + 520 * aperture)
            pygame.draw.circle(streaks, (206, 238, 255, int(66 * aperture)), (center_x, int(sh * 0.45)), radius, 2)
            inner_color = (88, 218, 230, int(80 * aperture))
            inner_radius = max(8, radius // 8)
            pygame.draw.circle(streaks, inner_color, (center_x, int(sh * 0.45)), inner_radius, 2)

        surface.blit(streaks, (0, 0))
