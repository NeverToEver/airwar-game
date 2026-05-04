"""Homecoming UI -- return-to-base progress and cinematic overlay."""

import math

import pygame

from airwar.game.homecoming import HomecomingPhase, HomecomingSequence
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.utils.fonts import get_cjk_font
from airwar.utils.sprites import draw_glow_circle, draw_player_ship


class HomecomingUI:
    """Renders hold progress and the return-to-base cinematic."""

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._visible = False
        self._progress = 0.0
        self._animation_time = 0
        self._bar_width = 310
        self._bar_height = 14
        self._font = get_cjk_font(18)
        self._small_font = get_cjk_font(15)

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0

    def update_progress(self, progress: float) -> None:
        self._progress = max(0.0, min(1.0, progress))
        self._animation_time += 1

    def render_progress(self, surface: pygame.Surface) -> None:
        if not self._visible or self._progress <= 0:
            return

        center_x = self._screen_width // 2
        center_y = 92
        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2
        pulse = 0.5 + 0.5 * math.sin(self._animation_time * 0.18)

        label = self._font.render("返航引擎预热", True, (220, 235, 255))
        hint = self._small_font.render("按住 B 启动基地返航", True, (142, 165, 190))
        surface.blit(label, label.get_rect(center=(center_x, center_y - 31)))
        surface.blit(hint, hint.get_rect(center=(center_x, center_y + 28)))

        draw_chamfered_panel(
            surface,
            bar_x,
            bar_y,
            self._bar_width,
            self._bar_height,
            (12, 20, 34),
            (90, 130, 170),
            None,
            5,
        )

        fill_width = int((self._bar_width - 4) * self._progress)
        if fill_width <= 0:
            return

        fill = pygame.Surface((fill_width, self._bar_height - 4), pygame.SRCALPHA)
        color = (210, 236, 255, 195 + int(45 * pulse))
        pygame.draw.rect(fill, color, fill.get_rect(), border_radius=4)
        surface.blit(fill, (bar_x + 2, bar_y + 2))

    def render_sequence(self, surface: pygame.Surface, sequence: HomecomingSequence, player) -> None:
        if not sequence.is_active() and not sequence.is_complete():
            return

        phase = sequence.phase
        progress = sequence.get_phase_progress()

        if phase == HomecomingPhase.FTL_ESCAPE:
            self._render_ftl_escape(surface, sequence, player, progress)
            return

        self._render_deep_space(surface, phase, progress)
        self._render_asteroid_belt(surface, phase, progress)
        self._render_space_station(surface, phase, progress, sequence)

        if phase in (HomecomingPhase.APPROACH, HomecomingPhase.LANDING, HomecomingPhase.HANDOFF):
            if phase == HomecomingPhase.HANDOFF:
                self._render_docking_corridor(surface, sequence, progress)
            self._render_landing_player(surface, sequence, player, progress)

        if phase == HomecomingPhase.HANDOFF:
            self._render_handoff(surface, progress)

        self._render_fade_overlay(surface, phase, progress)

    def _render_ftl_escape(
        self,
        surface: pygame.Surface,
        sequence: HomecomingSequence,
        player,
        progress: float,
    ) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(185 * progress)))
        surface.blit(overlay, (0, 0))

        x, y = sequence.get_player_center()
        trail_length = int(160 + 620 * progress)
        trail = pygame.Surface((90, trail_length), pygame.SRCALPHA)
        for i in range(trail_length):
            t = i / max(1, trail_length - 1)
            alpha = int(235 * (1 - t) ** 2)
            width = int(7 + 36 * t)
            pygame.draw.line(
                trail,
                (238, 248, 255, alpha),
                (45 - width // 2, trail_length - i),
                (45 + width // 2, trail_length - i),
                max(1, width),
            )
        surface.blit(trail, (int(x - 45), int(y + player.rect.height // 2)))
        draw_glow_circle(surface, (int(x), int(y + player.rect.height // 2)), 15, (230, 246, 255), 34)
        draw_player_ship(surface, x, y, player.rect.width, player.rect.height)

    def _render_deep_space(self, surface: pygame.Surface, phase: HomecomingPhase, progress: float) -> None:
        surface.fill((2, 4, 10))
        sw, sh = surface.get_size()
        reveal = progress if phase == HomecomingPhase.STATION_REVEAL else 1.0
        for index in range(90):
            x = (index * 97) % sw
            y = (index * 53 + int(progress * 26)) % sh
            alpha = int(35 + 105 * ((index % 7) / 6) * reveal)
            surface.set_at((x, y), (alpha, alpha, min(255, alpha + 35)))

    def _render_asteroid_belt(self, surface: pygame.Surface, phase: HomecomingPhase, progress: float) -> None:
        reveal = progress if phase == HomecomingPhase.STATION_REVEAL else 1.0
        if phase == HomecomingPhase.BLACKOUT or reveal <= 0:
            return

        sw, sh = surface.get_size()
        belt = pygame.Surface((sw, sh), pygame.SRCALPHA)
        center_x = sw * 0.47
        center_y = sh * 0.47
        for index in range(34):
            angle = math.radians(index * 17 + 12)
            radius_x = sw * (0.34 + (index % 5) * 0.025)
            radius_y = sh * (0.12 + (index % 7) * 0.012)
            drift = progress * 16 if phase in (HomecomingPhase.APPROACH, HomecomingPhase.LANDING) else 0
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
        phase: HomecomingPhase,
        progress: float,
        sequence: HomecomingSequence,
    ) -> None:
        reveal = progress if phase == HomecomingPhase.STATION_REVEAL else 1.0
        if phase == HomecomingPhase.BLACKOUT or reveal <= 0:
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

    def _render_landing_player(
        self,
        surface: pygame.Surface,
        sequence: HomecomingSequence,
        player,
        progress: float,
    ) -> None:
        x, y = sequence.get_player_center()
        if sequence.phase == HomecomingPhase.APPROACH:
            scale = 0.58 + 0.38 * progress
            trail_alpha = int(140 * (1 - progress))
            if trail_alpha > 0:
                pygame.draw.line(surface, (225, 245, 255, trail_alpha), (int(x), int(y + 70)), (int(x), int(y + 170)), 10)
        elif sequence.phase == HomecomingPhase.LANDING:
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

        if sequence.phase == HomecomingPhase.HANDOFF and progress >= 0.96:
            return

        width = max(22, int(player.rect.width * scale))
        height = max(26, int(player.rect.height * scale))
        draw_player_ship(surface, x, y, width, height)

    def _render_docking_corridor(
        self,
        surface: pygame.Surface,
        sequence: HomecomingSequence,
        progress: float,
    ) -> None:
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
            pygame.draw.circle(guide, (90, 236, 214, max(55, alpha - radius * 2)), (int(entry_x), int(entry_y)), radius, 2)
        draw_glow_circle(guide, (int(entry_x), int(entry_y)), 18, (80, 230, 210), 58)
        surface.blit(guide, (0, 0))

    def _render_handoff(self, surface: pygame.Surface, progress: float) -> None:
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

    def _render_fade_overlay(self, surface: pygame.Surface, phase: HomecomingPhase, progress: float) -> None:
        if phase == HomecomingPhase.BLACKOUT:
            alpha = 255
        elif phase == HomecomingPhase.STATION_REVEAL:
            alpha = int(255 * (1 - progress))
        elif phase == HomecomingPhase.HANDOFF:
            alpha = int(210 * progress)
        else:
            alpha = 0

        if alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))
