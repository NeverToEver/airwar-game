"""Boost gauge UI — 270° arc fuel gauge with pointer needle."""
import math
import pygame
from airwar.config.design_tokens import get_design_tokens, SystemColors


class BoostGauge:
    """270° arc boost gauge — 3/4 circle with 90° gap at bottom.

    Classic speedometer-style gauge. Needle sweeps 270° from
    bottom-left (empty) clockwise through top to bottom-right (full).
    """

    ARC_RADIUS = 80
    ARC_START_DEG = 225          # empty: bottom-left
    ARC_END_DEG = -45            # full: bottom-right (= 315°)
    TICK_MAJOR_INTERVAL = 45    # degrees between major ticks

    def __init__(self):
        tokens = get_design_tokens()
        c = tokens.colors
        self._bg_color = (12, 16, 22)
        self._arc_color = (55, 90, 130)
        self._arc_glow = (70, 120, 170)
        self._tick_dim = (45, 55, 70)
        self._tick_lit = SystemColors.ACCENT_TEAL
        self._tick_major = (120, 185, 220)
        self._needle_color = c.TEXT_PRIMARY
        self._needle_active = c.WARNING
        self._text_color = c.TEXT_MUTED
        self._text_bright = c.TEXT_PRIMARY
        self._fonts: dict = {}
        self._bg_cache = None
        self._arc_cache = None
        self._arc_cache_key = (0, 0)
        self._ticks = self._build_ticks()

    def _build_ticks(self):
        """Pre-compute tick geometry for all 31 ticks (every 9°)."""
        ticks = []
        for i in range(31):
            t = i / 30
            deg = self.ARC_START_DEG - t * (self.ARC_START_DEG - self.ARC_END_DEG)
            rad = math.radians(deg)
            is_major = (i % 5 == 0)
            inner = self.ARC_RADIUS - (9 if is_major else 5)
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

        cx = 108
        cy = screen_h - 98
        r = self.ARC_RADIUS
        ratio = boost_current / boost_max if boost_max > 0 else 0

        # Panel
        pw, ph = 200, 180
        px, py = 8, screen_h - ph - 12
        self._render_panel(surface, px, py, pw, ph)

        # Arc track + dim ticks — cached as pre-rendered layer
        cache_key = (cx, cy, int(screen_h))
        if self._arc_cache is None or self._arc_cache_key != cache_key:
            arc_layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
            try:
                arc_layer = arc_layer.convert_alpha()
            except pygame.error:
                pass
            self._draw_arc(arc_layer, cx - px, cy - py, r)
            self._draw_ticks(arc_layer, cx - px, cy - py, 0.0)
            self._arc_cache = arc_layer
            self._arc_cache_key = cache_key
        surface.blit(self._arc_cache, (px, py))

        # Lit ticks — drawn on top each frame
        if ratio > 0:
            self._draw_ticks_lit(surface, cx, cy, ratio)

        # Needle
        angle_deg = self.ARC_START_DEG - ratio * (self.ARC_START_DEG - self.ARC_END_DEG)
        self._draw_needle(surface, cx, cy, r, angle_deg, boost_active)

        # Center hub — metallic cap
        pygame.draw.circle(surface, (*self._bg_color, 255), (cx, cy), 9)
        pygame.draw.circle(surface, (*self._arc_color, 140), (cx, cy), 7, 1)
        pygame.draw.circle(surface, (*self._tick_lit, 80), (cx, cy), 3)

        # Labels
        self._draw_labels(surface, cx, cy, r, boost_current, boost_max, boost_active)

    # ------------------------------------------------------------------

    def _render_panel(self, surface, x, y, w, h):
        cache_key = (w, h)
        if self._bg_cache is None or self._bg_cache[0] != cache_key:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (*self._bg_color, 215),
                             panel.get_rect(), border_radius=14)
            # Inner border accent
            pygame.draw.rect(panel, (*self._arc_color, 50),
                             panel.get_rect().inflate(-3, -3),
                             width=1, border_radius=12)
            # Outer border
            pygame.draw.rect(panel, (*self._arc_color, 90),
                             panel.get_rect(), width=1, border_radius=14)
            self._bg_cache = (cache_key, panel)
        surface.blit(self._bg_cache[1], (x, y))

    def _draw_arc(self, surface, cx, cy, r):
        """Draw 270° arc track with subtle glow."""
        steps = 90
        for i in range(steps):
            t1 = i / steps
            t2 = (i + 1) / steps
            d1 = self.ARC_START_DEG - t1 * (self.ARC_START_DEG - self.ARC_END_DEG)
            d2 = self.ARC_START_DEG - t2 * (self.ARC_START_DEG - self.ARC_END_DEG)
            a1, a2 = math.radians(d1), math.radians(d2)
            x1, y1 = cx + math.cos(a1) * r, cy - math.sin(a1) * r
            x2, y2 = cx + math.cos(a2) * r, cy - math.sin(a2) * r
            # Glow layer
            glow_a = 25 + int(20 * (i / steps))
            pygame.draw.line(surface, (*self._arc_glow, glow_a), (x1, y1), (x2, y2), 5)
            # Core arc
            alpha = 90 + int(60 * (i / steps))
            pygame.draw.line(surface, (*self._arc_color, alpha), (x1, y1), (x2, y2), 2)

    def _draw_ticks(self, surface, cx, cy, _ratio):
        """Draw all tick marks in dim state (for cached layer)."""
        for rad, inner, outer, is_major, t in self._ticks:
            color = self._tick_dim
            alpha = 100 if is_major else 55
            x1 = cx + math.cos(rad) * inner
            y1 = cy - math.sin(rad) * inner
            x2 = cx + math.cos(rad) * outer
            y2 = cy - math.sin(rad) * outer
            w = 3 if is_major else 1
            pygame.draw.line(surface, (*color, alpha), (x1, y1), (x2, y2), w)

    def _draw_ticks_lit(self, surface, cx, cy, ratio):
        """Draw only lit ticks on top of cached dim layer."""
        for rad, inner, outer, is_major, t in self._ticks:
            if t > ratio:
                continue
            color = self._tick_major if is_major else self._tick_lit
            alpha = 240 if is_major else 160
            r2 = outer + (5 if is_major else 2)
            x1 = cx + math.cos(rad) * inner
            y1 = cy - math.sin(rad) * inner
            x2 = cx + math.cos(rad) * r2
            y2 = cy - math.sin(rad) * r2
            w = 2 if is_major else 1
            pygame.draw.line(surface, (*color, alpha), (x1, y1), (x2, y2), w)

    def _draw_needle(self, surface, cx, cy, r, angle_deg, active):
        """Pointer needle."""
        rad = math.radians(angle_deg)
        tip_r = r - 10
        tip_x = cx + math.cos(rad) * tip_r
        tip_y = cy - math.sin(rad) * tip_r

        back_rad = math.radians(angle_deg + 180)
        tail_x = cx + math.cos(back_rad) * 14
        tail_y = cy - math.sin(back_rad) * 14

        color = self._needle_active if active else self._needle_color
        pygame.draw.line(surface, (*color, 210), (cx, cy), (tip_x, tip_y), 2)
        pygame.draw.line(surface, (*color, 90), (cx, cy), (tail_x, tail_y), 1)
        pygame.draw.circle(surface, (*color, 240), (int(tip_x), int(tip_y)), 2)

    def _draw_labels(self, surface, cx, cy, r, current, max_val, active):
        """Title, value, min/max, and BOOSTING indicator."""
        title_font = self._get_font(14)
        title = title_font.render("BOOST FUEL", True, self._text_color)
        surface.blit(title, title.get_rect(center=(cx, cy + 10)))

        val_font = self._get_font(24)
        val_color = self._text_bright if active else self._text_color
        val = val_font.render(str(int(current)), True, val_color)
        surface.blit(val, val.get_rect(center=(cx, cy + 30)))

        tiny = self._get_font(11)
        rad_start = math.radians(self.ARC_START_DEG)
        rad_end = math.radians(self.ARC_END_DEG)
        lr = r + 12

        zero = tiny.render("0", True, self._text_color)
        lx, ly = cx + math.cos(rad_start) * lr, cy - math.sin(rad_start) * lr
        surface.blit(zero, zero.get_rect(center=(lx, ly)))

        full = tiny.render(f"{int(max_val)}", True, self._text_color)
        rx, ry = cx + math.cos(rad_end) * lr, cy - math.sin(rad_end) * lr
        surface.blit(full, full.get_rect(center=(rx, ry)))

        if active:
            af = self._get_font(12)
            at = af.render("BOOSTING", True, (*self._needle_active, 200))
            surface.blit(at, at.get_rect(center=(cx, cy + 44)))
