"""Station reveal phase renderer -- space backdrop (deep space + asteroid belt + base station)."""

import math

import pygame

from airwar.ui.homecoming._constants import (
    PHASE_APPROACH,
    PHASE_BLACKOUT,
    PHASE_LANDING,
    PHASE_STATION_REVEAL,
)
from airwar.utils.sprites import draw_glow_circle


class StationRevealRenderer:
    """Renders the shared space backdrop used by STATION_REVEAL/APPROACH/LANDING/HANDOFF/BASE_LAUNCH."""

    def render(
        self,
        surface: pygame.Surface,
        phase: str,
        progress: float,
        sequence,
    ) -> None:
        """Draw deep space + asteroid belt + space station as the base backdrop."""
        self._render_deep_space(surface, phase, progress)
        self._render_asteroid_belt(surface, phase, progress)
        self._render_space_station(surface, phase, progress, sequence)

    def _render_deep_space(self, surface: pygame.Surface, phase: str, progress: float) -> None:
        surface.fill((2, 4, 10))
        sw, sh = surface.get_size()
        reveal = progress if phase == PHASE_STATION_REVEAL else 1.0
        for index in range(90):
            x = (index * 97) % sw
            y = (index * 53 + int(progress * 26)) % sh
            alpha = int(35 + 105 * ((index % 7) / 6) * reveal)
            surface.set_at((x, y), (alpha, alpha, min(255, alpha + 35)))

    def _render_asteroid_belt(self, surface: pygame.Surface, phase: str, progress: float) -> None:
        reveal = progress if phase == PHASE_STATION_REVEAL else 1.0
        if phase == PHASE_BLACKOUT or reveal <= 0:
            return

        sw, sh = surface.get_size()
        belt = pygame.Surface((sw, sh), pygame.SRCALPHA)
        center_x = sw * 0.47
        center_y = sh * 0.47
        for index in range(34):
            angle = math.radians(index * 17 + 12)
            radius_x = sw * (0.34 + (index % 5) * 0.025)
            radius_y = sh * (0.12 + (index % 7) * 0.012)
            drift = progress * 16 if phase in (PHASE_APPROACH, PHASE_LANDING) else 0
            x = int(center_x + math.cos(angle) * radius_x + drift)
            y = int(center_y + math.sin(angle) * radius_y + (index % 4 - 1.5) * 18)
            size = 5 + (index * 7) % 18
            shade = 54 + (index * 13) % 58
            alpha = int((70 + (index % 6) * 20) * reveal)
            points = self._asteroid_points(x, y, size, index)
            pygame.draw.polygon(belt, (shade, shade + 8, shade + 16, alpha), points)
            pygame.draw.polygon(belt, (shade + 38, shade + 46, shade + 54, int(alpha * 0.7)), points, 1)

        surface.blit(belt, (0, 0))

    def _render_space_station(
        self,
        surface: pygame.Surface,
        phase: str,
        progress: float,
        sequence,
    ) -> None:
        reveal = progress if phase == PHASE_STATION_REVEAL else 1.0
        if phase == PHASE_BLACKOUT or reveal <= 0:
            return

        sw, sh = surface.get_size()
        station = pygame.Surface((sw, sh), pygame.SRCALPHA)
        cx, cy = sequence.get_base_entry_center()
        cx = int(cx)
        cy = int(cy)
        alpha = int(255 * reveal)

        self._render_station_solar_arrays(station, cx, cy, reveal)
        self._render_station_ring(station, cx, cy, reveal)
        self._render_station_spokes(station, cx, cy, reveal)
        self._render_station_hub(station, cx, cy, reveal)
        self._render_station_docking_port(station, cx, cy, reveal, progress)

        station.set_alpha(alpha)
        surface.blit(station, (0, 0))

    def _asteroid_points(self, x: int, y: int, size: int, seed: int) -> list[tuple[int, int]]:
        point_count = 7
        points = []
        for i in range(point_count):
            angle = math.tau * i / point_count
            wobble = 0.72 + ((seed * 19 + i * 11) % 40) / 100
            px = int(x + math.cos(angle) * size * wobble)
            py = int(y + math.sin(angle) * size * (0.7 + wobble * 0.25))
            points.append((px, py))
        return points

    def _render_station_solar_arrays(self, surface: pygame.Surface, cx: int, cy: int, reveal: float) -> None:
        alpha = int(210 * reveal)
        for side in (-1, 1):
            mast_start = (cx + side * 190, cy - 10)
            mast_end = (cx + side * 520, cy - 84)
            pygame.draw.line(surface, (118, 145, 170, alpha), mast_start, mast_end, 6)
            pygame.draw.line(surface, (52, 234, 210, int(alpha * 0.42)), mast_start, mast_end, 2)

            for i in range(4):
                panel_x = cx + side * (250 + i * 78)
                panel_y = cy - 144 + i * 5
                panel = [
                    (panel_x - side * 30, panel_y - 48),
                    (panel_x + side * 48, panel_y - 62),
                    (panel_x + side * 62, panel_y + 58),
                    (panel_x - side * 18, panel_y + 70),
                ]
                pygame.draw.polygon(surface, (18, 56, 86, int(alpha * 0.86)), panel)
                pygame.draw.polygon(surface, (82, 184, 220, int(alpha * 0.72)), panel, 2)
                for stripe in range(1, 4):
                    t = stripe / 4
                    sx1 = int(panel[0][0] + (panel[1][0] - panel[0][0]) * t)
                    sy1 = int(panel[0][1] + (panel[1][1] - panel[0][1]) * t)
                    sx2 = int(panel[3][0] + (panel[2][0] - panel[3][0]) * t)
                    sy2 = int(panel[3][1] + (panel[2][1] - panel[3][1]) * t)
                    pygame.draw.line(surface, (108, 220, 246, int(alpha * 0.34)), (sx1, sy1), (sx2, sy2), 1)

    def _render_station_ring(self, surface: pygame.Surface, cx: int, cy: int, reveal: float) -> None:
        alpha = int(230 * reveal)
        ring_outer = pygame.Rect(0, 0, 520, 210)
        ring_outer.center = (cx, cy)
        ring_inner = ring_outer.inflate(-108, -66)
        pygame.draw.ellipse(surface, (30, 42, 58, int(alpha * 0.92)), ring_outer, 24)
        pygame.draw.ellipse(surface, (108, 132, 154, int(alpha * 0.86)), ring_outer, 3)
        pygame.draw.ellipse(surface, (74, 232, 214, int(alpha * 0.42)), ring_inner, 2)

        for index in range(18):
            angle = math.tau * index / 18
            px = cx + int(math.cos(angle) * 250)
            py = cy + int(math.sin(angle) * 98)
            module = pygame.Rect(px - 18, py - 8, 36, 16)
            pygame.draw.rect(surface, (48, 62, 80, int(alpha * 0.92)), module, border_radius=3)
            pygame.draw.rect(surface, (124, 148, 168, int(alpha * 0.72)), module, 1, border_radius=3)
            if index % 3 == 0:
                draw_glow_circle(surface, (px, py), 3, (94, 234, 214), 14)

    def _render_station_spokes(self, surface: pygame.Surface, cx: int, cy: int, reveal: float) -> None:
        alpha = int(190 * reveal)
        for angle_deg in (0, 45, 90, 135, 180, 225, 270, 315):
            angle = math.radians(angle_deg)
            inner = (cx + int(math.cos(angle) * 56), cy + int(math.sin(angle) * 28))
            outer = (cx + int(math.cos(angle) * 230), cy + int(math.sin(angle) * 92))
            pygame.draw.line(surface, (86, 108, 130, alpha), inner, outer, 5)
            pygame.draw.line(surface, (64, 222, 204, int(alpha * 0.38)), inner, outer, 1)

    def _render_station_hub(self, surface: pygame.Surface, cx: int, cy: int, reveal: float) -> None:
        alpha = int(245 * reveal)
        hub = pygame.Rect(cx - 92, cy - 54, 184, 108)
        pygame.draw.ellipse(surface, (38, 52, 70, alpha), hub)
        pygame.draw.ellipse(surface, (132, 154, 178, int(alpha * 0.9)), hub, 3)
        pygame.draw.ellipse(surface, (8, 14, 22, int(alpha * 0.95)), hub.inflate(-58, -34))
        pygame.draw.ellipse(surface, (78, 238, 214, int(alpha * 0.8)), hub.inflate(-58, -34), 2)
        draw_glow_circle(surface, (cx, cy), 16, (82, 226, 210), 48)

    def _render_station_docking_port(
        self,
        surface: pygame.Surface,
        cx: int,
        cy: int,
        reveal: float,
        progress: float,
    ) -> None:
        pulse = 0.5 + 0.5 * math.sin(progress * math.pi * 8)
        alpha = int(230 * reveal)
        port_y = cy + 18
        for radius, width in ((74, 4), (52, 3), (30, 2)):
            color_alpha = int((130 + 90 * pulse) * reveal)
            pygame.draw.circle(surface, (82, 238, 218, color_alpha), (cx, port_y), radius, width)
        pygame.draw.circle(surface, (2, 6, 10, int(alpha * 0.98)), (cx, port_y), 24)
        pygame.draw.circle(surface, (190, 255, 246, int(alpha * 0.95)), (cx, port_y), 5)
