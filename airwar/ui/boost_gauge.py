"""Boost gauge UI — 270° arc fuel gauge with pointer needle."""
import math
import pygame
from airwar.config.design_tokens import get_design_tokens, SystemColors


class BoostGauge:
    """270° arc boost gauge — 3/4 circle with 90° gap at bottom.

    Classic speedometer-style gauge. Needle sweeps 270° from
    bottom-left (empty) clockwise through top to bottom-right (full).
    """

    ARC_RADIUS = 115
    ARC_START_DEG = 225          # empty: bottom-left
    ARC_END_DEG = -45            # full: bottom-right (= 315°)
    TICK_MAJOR_INTERVAL = 45    # degrees between major ticks

    def __init__(self):
        tokens = get_design_tokens()
        self._bg_color = (10, 14, 24)
        self._arc_color = (55, 65, 85)
        self._tick_dim = (80, 95, 115)
        self._tick_lit = (130, 200, 235)
        self._needle_color = (200, 190, 170)
        self._needle_active = (235, 85, 65)
        self._text_color = tokens.colors.TEXT_MUTED
        self._text_bright = tokens.colors.TEXT_PRIMARY
        self._fonts: dict = {}
        self._bg_cache = None
        self._ticks = self._build_ticks()

    def _build_ticks(self):
        """Pre-compute tick geometry for all 31 ticks (every 9°)."""
        ticks = []
        for i in range(31):
            t = i / 30
            deg = self.ARC_START_DEG - t * (self.ARC_START_DEG - self.ARC_END_DEG)
            rad = math.radians(deg)
            is_major = (i % 5 == 0)
            inner = self.ARC_RADIUS - (13 if is_major else 8)
            outer = self.ARC_RADIUS
            ticks.append((rad, inner, outer, is_major, t))
        return ticks

    def _get_font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def render(self, surface: pygame.Surface, boost_current: float,
               boost_max: float, boost_active: bool) -> None:
        screen_h = surface.get_height()

        cx = 155
        cy = screen_h - 55
        r = self.ARC_RADIUS
        ratio = boost_current / boost_max if boost_max > 0 else 0

        # Panel
        pw, ph = 290, 220
        px, py = 12, screen_h - ph - 14
        self._render_panel(surface, px, py, pw, ph)

        # Arc track
        self._draw_arc(surface, cx, cy, r)

        # Ticks
        self._draw_ticks(surface, cx, cy, ratio)

        # Needle
        angle_deg = self.ARC_START_DEG - ratio * (self.ARC_START_DEG - self.ARC_END_DEG)
        self._draw_needle(surface, cx, cy, r, angle_deg, boost_active)

        # Center hub
        pygame.draw.circle(surface, (25, 30, 42), (cx, cy), 13)
        pygame.draw.circle(surface, (*self._arc_color, 160), (cx, cy), 11, 1)
        pygame.draw.circle(surface, (*self._tick_lit, 60), (cx, cy), 5)

        # Labels
        self._draw_labels(surface, cx, cy, r, boost_current, boost_max, boost_active)

    # ------------------------------------------------------------------

    def _render_panel(self, surface, x, y, w, h):
        cache_key = (w, h)
        if self._bg_cache is None or self._bg_cache[0] != cache_key:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (*self._bg_color, 200),
                             panel.get_rect(), border_radius=14)
            pygame.draw.rect(panel, (*self._arc_color, 80),
                             panel.get_rect(), width=1, border_radius=14)
            self._bg_cache = (cache_key, panel)
        surface.blit(self._bg_cache[1], (x, y))

    def _draw_arc(self, surface, cx, cy, r):
        """Draw 270° arc track."""
        steps = 90
        for i in range(steps):
            t1 = i / steps
            t2 = (i + 1) / steps
            d1 = self.ARC_START_DEG - t1 * (self.ARC_START_DEG - self.ARC_END_DEG)
            d2 = self.ARC_START_DEG - t2 * (self.ARC_START_DEG - self.ARC_END_DEG)
            a1, a2 = math.radians(d1), math.radians(d2)
            x1, y1 = cx + math.cos(a1) * r, cy - math.sin(a1) * r
            x2, y2 = cx + math.cos(a2) * r, cy - math.sin(a2) * r
            alpha = 70 + int(60 * (i / steps))
            pygame.draw.line(surface, (*self._arc_color, alpha), (x1, y1), (x2, y2), 3)

    def _draw_ticks(self, surface, cx, cy, ratio):
        """Tick marks — lit up to current ratio, dim beyond."""
        for rad, inner, outer, is_major, t in self._ticks:
            filled = t <= ratio
            if filled:
                color = self._tick_lit
                alpha = 230 if is_major else 150
                r2 = outer + (6 if is_major else 3)
            else:
                color = self._tick_dim
                alpha = 110 if is_major else 60
                r2 = outer
            x1 = cx + math.cos(rad) * inner
            y1 = cy - math.sin(rad) * inner
            x2 = cx + math.cos(rad) * r2
            y2 = cy - math.sin(rad) * r2
            w = 3 if is_major else 1
            pygame.draw.line(surface, (*color, alpha), (x1, y1), (x2, y2), w)

    def _draw_needle(self, surface, cx, cy, r, angle_deg, active):
        """Pointer needle."""
        rad = math.radians(angle_deg)
        tip_r = r - 14
        tip_x = cx + math.cos(rad) * tip_r
        tip_y = cy - math.sin(rad) * tip_r

        back_rad = math.radians(angle_deg + 180)
        tail_x = cx + math.cos(back_rad) * 20
        tail_y = cy - math.sin(back_rad) * 20

        color = self._needle_active if active else self._needle_color
        pygame.draw.line(surface, (*color, 210), (cx, cy), (tip_x, tip_y), 2)
        pygame.draw.line(surface, (*color, 90), (cx, cy), (tail_x, tail_y), 1)
        pygame.draw.circle(surface, (*color, 240), (int(tip_x), int(tip_y)), 3)

    def _draw_labels(self, surface, cx, cy, r, current, max_val, active):
        """Title, value, min/max, and BOOSTING indicator."""
        title_font = self._get_font(18)
        title = title_font.render("BOOST FUEL", True, self._text_color)
        surface.blit(title, title.get_rect(center=(cx, cy + 12)))

        val_font = self._get_font(34)
        val_color = self._text_bright if active else self._text_color
        val = val_font.render(str(int(current)), True, val_color)
        surface.blit(val, val.get_rect(center=(cx, cy + 40)))

        tiny = self._get_font(14)
        rad_start = math.radians(self.ARC_START_DEG)
        rad_end = math.radians(self.ARC_END_DEG)
        lr = r + 16

        zero = tiny.render("0", True, self._text_color)
        lx, ly = cx + math.cos(rad_start) * lr, cy - math.sin(rad_start) * lr
        surface.blit(zero, zero.get_rect(center=(lx, ly)))

        full = tiny.render(f"{int(max_val)}", True, self._text_color)
        rx, ry = cx + math.cos(rad_end) * lr, cy - math.sin(rad_end) * lr
        surface.blit(full, full.get_rect(center=(rx, ry)))

        if active:
            af = self._get_font(15)
            at = af.render("BOOSTING", True, (*self._needle_active, 200))
            surface.blit(at, at.get_rect(center=(cx, cy + 58)))
