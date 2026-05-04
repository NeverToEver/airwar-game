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
        self._render_space_carrier(surface, phase, progress)

        if phase in (HomecomingPhase.APPROACH, HomecomingPhase.LANDING, HomecomingPhase.HANDOFF):
            if phase == HomecomingPhase.HANDOFF:
                self._render_base_entry(surface, sequence, progress)
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
        reveal = progress if phase == HomecomingPhase.CARRIER_REVEAL else 1.0
        for index in range(90):
            x = (index * 97) % sw
            y = (index * 53 + int(progress * 26)) % sh
            alpha = int(35 + 105 * ((index % 7) / 6) * reveal)
            surface.set_at((x, y), (alpha, alpha, min(255, alpha + 35)))

    def _render_space_carrier(self, surface: pygame.Surface, phase: HomecomingPhase, progress: float) -> None:
        sw, sh = surface.get_size()
        reveal = progress if phase == HomecomingPhase.CARRIER_REVEAL else 1.0
        if phase == HomecomingPhase.BLACKOUT:
            reveal = 0.0
        if reveal <= 0:
            return

        cx = sw // 2
        cy = int(sh * 0.43)
        carrier = pygame.Surface((sw, sh), pygame.SRCALPHA)
        alpha = int(255 * reveal)

        deck = [
            (cx - 520, cy - 18),
            (cx + 430, cy - 92),
            (cx + 575, cy - 26),
            (cx + 438, cy + 84),
            (cx - 470, cy + 104),
            (cx - 610, cy + 38),
        ]
        pygame.draw.polygon(carrier, (36, 45, 61, alpha), deck)
        pygame.draw.polygon(carrier, (102, 123, 148, alpha), deck, 3)

        runway = [
            (cx - 420, cy + 9),
            (cx + 330, cy - 44),
            (cx + 390, cy - 9),
            (cx - 365, cy + 50),
        ]
        pygame.draw.polygon(carrier, (13, 20, 30, alpha), runway)
        pygame.draw.polygon(carrier, (78, 220, 190, int(150 * reveal)), runway, 2)

        for offset in range(-330, 360, 90):
            light_x = int(cx + offset)
            light_y = int(cy + 22 - offset * 0.065)
            draw_glow_circle(carrier, (light_x, light_y), 4, (110, 238, 220), 13)
            pygame.draw.circle(carrier, (180, 255, 245, alpha), (light_x, light_y), 2)

        island = pygame.Rect(cx + 210, cy - 164, 110, 82)
        pygame.draw.rect(carrier, (41, 54, 75, alpha), island, border_radius=4)
        pygame.draw.rect(carrier, (130, 155, 182, alpha), island, 2, border_radius=4)
        pygame.draw.polygon(
            carrier,
            (54, 70, 94, alpha),
            [(cx + 236, cy - 164), (cx + 292, cy - 164), (cx + 274, cy - 220), (cx + 250, cy - 220)],
        )

        for engine_x in (cx - 430, cx - 250, cx + 455):
            draw_glow_circle(carrier, (engine_x, cy + 116), 18, (82, 166, 255), 46)
            pygame.draw.circle(carrier, (198, 228, 255, alpha), (engine_x, cy + 116), 7)

        carrier.set_alpha(alpha)
        surface.blit(carrier, (0, 0))

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

    def _render_base_entry(
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

        bay_w = 190
        bay_h = 88
        bay_x = int(entry_x - bay_w / 2)
        bay_y = int(entry_y - bay_h / 2)
        outer = [
            (bay_x - 34, bay_y + bay_h),
            (bay_x + 18, bay_y - 22),
            (bay_x + bay_w - 18, bay_y - 22),
            (bay_x + bay_w + 34, bay_y + bay_h),
        ]
        pygame.draw.polygon(guide, (14, 22, 32, 235), outer)
        pygame.draw.polygon(guide, (120, 156, 184, 210), outer, 3)

        inner = pygame.Rect(bay_x + 24, bay_y + 8, bay_w - 48, bay_h - 18)
        pygame.draw.rect(guide, (0, 4, 8, 245), inner, border_radius=5)
        pygame.draw.rect(guide, (95, 236, 214, alpha), inner, 2, border_radius=5)

        shutter_count = 6
        for i in range(shutter_count):
            sx = inner.x + int((i + 1) * inner.width / (shutter_count + 1))
            pygame.draw.line(guide, (42, 72, 86, 150), (sx, inner.y + 6), (sx - 18, inner.bottom - 6), 2)

        draw_glow_circle(guide, (int(entry_x), int(entry_y)), 20, (80, 230, 210), 54)
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
        elif phase == HomecomingPhase.CARRIER_REVEAL:
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
