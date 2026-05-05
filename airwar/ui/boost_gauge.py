"""Boost gauge UI — 270° arc fuel gauge with pointer needle."""
import math
import pygame
from airwar.utils.fonts import get_cjk_font
from airwar.config.design_tokens import get_design_tokens, SystemColors
import contextlib


class BoostGauge:
    """270° arc boost gauge — 3/4 circle with 90° gap at bottom.

    Classic speedometer-style gauge. Needle sweeps 270° from
    bottom-left (empty) clockwise through top to bottom-right (full).
    """

    ARC_RADIUS = 80
    ARC_START_DEG = 225          # empty: bottom-left
    ARC_END_DEG = -45            # full: bottom-right (= 315°)
    TICK_MAJOR_INTERVAL = 45    # degrees between major ticks

    # Colors
    BG_COLOR = (12, 16, 22)
    ARC_COLOR = (55, 90, 130)
    ARC_GLOW_COLOR = (70, 120, 170)
    TICK_DIM_COLOR = (45, 55, 70)
    TICK_MAJOR_COLOR = (120, 185, 220)

    # Layout
    NUM_TICKS = 31
    TICK_DIVISOR = 30
    MAJOR_TICK_INNER = 9
    MINOR_TICK_INNER = 5
    CENTER_X = 108
    PANEL_W = 200
    PANEL_H = 180
    PANEL_PAD_X = 8
    PANEL_PAD_Y = 12

    # Hub circle
    HUB_RADIUS = 9
    HUB_INNER_RADIUS = 7
    HUB_INNER_WIDTH = 1
    HUB_DOT_RADIUS = 3

    # Panel rendering
    PANEL_BG_ALPHA = 215
    PANEL_BORDER_RADIUS = 14
    PANEL_INNER_INSET = -3
    PANEL_INNER_BORDER_ALPHA = 50
    PANEL_INNER_BORDER_RADIUS = 12
    PANEL_OUTER_BORDER_ALPHA = 90

    # Arc track
    ARC_STEPS = 90
    ARC_GLOW_BASE_ALPHA = 25
    ARC_GLOW_ALPHA_RANGE = 20
    ARC_GLOW_WIDTH = 5
    ARC_CORE_BASE_ALPHA = 90
    ARC_CORE_ALPHA_RANGE = 60
    ARC_CORE_WIDTH = 2

    # Dim ticks
    DIM_TICK_MAJOR_ALPHA = 100
    DIM_TICK_MINOR_ALPHA = 55
    DIM_TICK_MAJOR_WIDTH = 3
    DIM_TICK_MINOR_WIDTH = 1

    # Lit ticks
    TICK_LIT_MAJOR_ALPHA = 240
    TICK_LIT_MINOR_ALPHA = 160
    TICK_LIT_MAJOR_EXTRA = 5
    TICK_LIT_MINOR_EXTRA = 2
    TICK_LIT_MAJOR_WIDTH = 2
    TICK_LIT_MINOR_WIDTH = 1

    # Needle
    NEEDLE_TIP_INSET = 10
    NEEDLE_TAIL_LEN = 14
    NEEDLE_ALPHA = 210
    NEEDLE_WIDTH = 2
    NEEDLE_TAIL_ALPHA = 90
    NEEDLE_TAIL_WIDTH = 1
    NEEDLE_TIP_ALPHA = 240
    NEEDLE_TIP_RADIUS = 2

    # Label sizes and offsets
    LABEL_TITLE_FONT_SIZE = 16
    LABEL_TITLE_Y_OFFSET = 10
    LABEL_VALUE_FONT_SIZE = 24
    LABEL_VALUE_Y_OFFSET = 30
    LABEL_TINY_FONT_SIZE = 11
    LABEL_EXTRA_RADIUS = 12
    LABEL_ACTIVE_FONT_SIZE = 14
    LABEL_ACTIVE_ALPHA = 200
    LABEL_ACTIVE_Y_OFFSET = 44
    COMPACT_SCALE = 0.78
    COMPACT_HEIGHT_THRESHOLD = 760

    def __init__(self):
        tokens = get_design_tokens()
        c = tokens.colors
        self._bg_color = self.BG_COLOR
        self._arc_color = self.ARC_COLOR
        self._arc_glow = self.ARC_GLOW_COLOR
        self._tick_dim = self.TICK_DIM_COLOR
        self._tick_lit = SystemColors.ACCENT_TEAL
        self._tick_major = self.TICK_MAJOR_COLOR
        self._cooldown_color = SystemColors.DANGER_RED
        self._cooldown_dim = SystemColors.DANGER_RED_DIM
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
        for i in range(self.NUM_TICKS):
            t = i / self.TICK_DIVISOR
            deg = self.ARC_START_DEG - t * (self.ARC_START_DEG - self.ARC_END_DEG)
            rad = math.radians(deg)
            is_major = (i % 5 == 0)
            inner = self.ARC_RADIUS - (self.MAJOR_TICK_INNER if is_major else self.MINOR_TICK_INNER)
            outer = self.ARC_RADIUS
            ticks.append((rad, inner, outer, is_major, t))
        return ticks

    def _get_font(self, size):
        if size not in self._fonts:
            self._fonts[size] = get_cjk_font(size)
        return self._fonts[size]

    def render(
        self,
        surface: pygame.Surface,
        boost_current: float,
        boost_max: float,
        boost_active: bool,
        boost_status: dict | None = None,
    ) -> None:
        screen_h = surface.get_height()
        scale = self.COMPACT_SCALE if screen_h <= self.COMPACT_HEIGHT_THRESHOLD else 1.0
        if scale < 1.0:
            self._render_compact(surface, boost_current, boost_max, boost_active, boost_status, scale)
            return

        cx = self.CENTER_X
        cy = screen_h - 98
        r = self.ARC_RADIUS
        ratio = boost_current / boost_max if boost_max > 0 else 0
        dash_cooling = bool(
            boost_status
            and boost_status.get('dash_enabled')
            and boost_status.get('dash_cooldown', 0) > 0
        )
        dash_active = bool(boost_status and boost_status.get('dash_active'))

        # Panel
        pw, ph = self.PANEL_W, self.PANEL_H
        px, py = self.PANEL_PAD_X, screen_h - ph - self.PANEL_PAD_Y
        self._render_panel(surface, px, py, pw, ph)

        # Arc track + dim ticks — cached as pre-rendered layer
        cache_key = (cx, cy, int(screen_h))
        if self._arc_cache is None or self._arc_cache_key != cache_key:
            arc_layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
            with contextlib.suppress(pygame.error):
                arc_layer = arc_layer.convert_alpha()
            self._draw_arc(arc_layer, cx - px, cy - py, r)
            self._draw_ticks(arc_layer, cx - px, cy - py, 0.0)
            self._arc_cache = arc_layer
            self._arc_cache_key = cache_key
        surface.blit(self._arc_cache, (px, py))

        # Lit ticks — drawn on top each frame
        if ratio > 0:
            self._draw_ticks_lit(surface, cx, cy, ratio, dash_cooling)

        # Needle
        angle_deg = self.ARC_START_DEG - ratio * (self.ARC_START_DEG - self.ARC_END_DEG)
        self._draw_needle(surface, cx, cy, r, angle_deg, boost_active, dash_cooling)

        # Center hub — metallic cap
        pygame.draw.circle(surface, (*self._bg_color, 255), (cx, cy), self.HUB_RADIUS)
        pygame.draw.circle(surface, (*self._arc_color, 140), (cx, cy), self.HUB_INNER_RADIUS, self.HUB_INNER_WIDTH)
        hub_color = self._cooldown_color if dash_cooling else self._tick_lit
        pygame.draw.circle(surface, (*hub_color, 80), (cx, cy), self.HUB_DOT_RADIUS)

        # Labels
        self._draw_labels(
            surface,
            cx,
            cy,
            r,
            boost_current,
            boost_max,
            boost_active,
            dash_cooling,
            dash_active,
        )

    # ------------------------------------------------------------------

    def _render_compact(
        self,
        surface: pygame.Surface,
        boost_current: float,
        boost_max: float,
        boost_active: bool,
        boost_status: dict | None,
        scale: float,
    ) -> None:
        pw, ph = self.PANEL_W, self.PANEL_H
        layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
        with contextlib.suppress(pygame.error):
            layer = layer.convert_alpha()

        cx = self.CENTER_X - self.PANEL_PAD_X
        cy = ph + self.PANEL_PAD_Y - 98
        r = self.ARC_RADIUS
        ratio = boost_current / boost_max if boost_max > 0 else 0
        dash_cooling = bool(
            boost_status
            and boost_status.get('dash_enabled')
            and boost_status.get('dash_cooldown', 0) > 0
        )
        dash_active = bool(boost_status and boost_status.get('dash_active'))

        self._render_panel(layer, 0, 0, pw, ph)

        cache_key = ("compact", pw, ph)
        if self._arc_cache is None or self._arc_cache_key != cache_key:
            arc_layer = pygame.Surface((pw, ph), pygame.SRCALPHA)
            with contextlib.suppress(pygame.error):
                arc_layer = arc_layer.convert_alpha()
            self._draw_arc(arc_layer, cx, cy, r)
            self._draw_ticks(arc_layer, cx, cy, 0.0)
            self._arc_cache = arc_layer
            self._arc_cache_key = cache_key
        layer.blit(self._arc_cache, (0, 0))

        if ratio > 0:
            self._draw_ticks_lit(layer, cx, cy, ratio, dash_cooling)

        angle_deg = self.ARC_START_DEG - ratio * (self.ARC_START_DEG - self.ARC_END_DEG)
        self._draw_needle(layer, cx, cy, r, angle_deg, boost_active, dash_cooling)

        pygame.draw.circle(layer, (*self._bg_color, 255), (cx, cy), self.HUB_RADIUS)
        pygame.draw.circle(layer, (*self._arc_color, 140), (cx, cy), self.HUB_INNER_RADIUS, self.HUB_INNER_WIDTH)
        hub_color = self._cooldown_color if dash_cooling else self._tick_lit
        pygame.draw.circle(layer, (*hub_color, 80), (cx, cy), self.HUB_DOT_RADIUS)

        self._draw_labels(
            layer,
            cx,
            cy,
            r,
            boost_current,
            boost_max,
            boost_active,
            dash_cooling,
            dash_active,
        )

        scaled_size = (max(1, int(pw * scale)), max(1, int(ph * scale)))
        compact = pygame.transform.smoothscale(layer, scaled_size)
        px = self.PANEL_PAD_X
        py = surface.get_height() - scaled_size[1] - self.PANEL_PAD_Y
        surface.blit(compact, (px, py))

    def _render_panel(self, surface, x, y, w, h):
        cache_key = (w, h)
        if self._bg_cache is None or self._bg_cache.get('key') != cache_key:
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (*self._bg_color, self.PANEL_BG_ALPHA),
                             panel.get_rect(), border_radius=self.PANEL_BORDER_RADIUS)
            # Inner border accent
            pygame.draw.rect(panel, (*self._arc_color, self.PANEL_INNER_BORDER_ALPHA),
                             panel.get_rect().inflate(self.PANEL_INNER_INSET, self.PANEL_INNER_INSET),
                             width=1, border_radius=self.PANEL_INNER_BORDER_RADIUS)
            # Outer border
            pygame.draw.rect(panel, (*self._arc_color, self.PANEL_OUTER_BORDER_ALPHA),
                             panel.get_rect(), width=1, border_radius=self.PANEL_BORDER_RADIUS)
            self._bg_cache = {'key': cache_key, 'surf': panel}
        surface.blit(self._bg_cache['surf'], (x, y))

    def _draw_arc(self, surface, cx, cy, r):
        """Draw 270° arc track with subtle glow."""
        steps = self.ARC_STEPS
        for i in range(steps):
            t1 = i / steps
            t2 = (i + 1) / steps
            d1 = self.ARC_START_DEG - t1 * (self.ARC_START_DEG - self.ARC_END_DEG)
            d2 = self.ARC_START_DEG - t2 * (self.ARC_START_DEG - self.ARC_END_DEG)
            a1, a2 = math.radians(d1), math.radians(d2)
            x1, y1 = cx + math.cos(a1) * r, cy - math.sin(a1) * r
            x2, y2 = cx + math.cos(a2) * r, cy - math.sin(a2) * r
            # Glow layer
            glow_a = self.ARC_GLOW_BASE_ALPHA + int(self.ARC_GLOW_ALPHA_RANGE * (i / steps))
            pygame.draw.line(surface, (*self._arc_glow, glow_a), (x1, y1), (x2, y2), self.ARC_GLOW_WIDTH)
            # Core arc
            alpha = self.ARC_CORE_BASE_ALPHA + int(self.ARC_CORE_ALPHA_RANGE * (i / steps))
            pygame.draw.line(surface, (*self._arc_color, alpha), (x1, y1), (x2, y2), self.ARC_CORE_WIDTH)

    def _draw_ticks(self, surface, cx, cy, _ratio):
        """Draw all tick marks in dim state (for cached layer)."""
        for rad, inner, outer, is_major, _t in self._ticks:
            color = self._tick_dim
            alpha = self.DIM_TICK_MAJOR_ALPHA if is_major else self.DIM_TICK_MINOR_ALPHA
            x1 = cx + math.cos(rad) * inner
            y1 = cy - math.sin(rad) * inner
            x2 = cx + math.cos(rad) * outer
            y2 = cy - math.sin(rad) * outer
            w = self.DIM_TICK_MAJOR_WIDTH if is_major else self.DIM_TICK_MINOR_WIDTH
            pygame.draw.line(surface, (*color, alpha), (x1, y1), (x2, y2), w)

    def _draw_ticks_lit(self, surface, cx, cy, ratio, cooldown=False):
        """Draw only lit ticks on top of cached dim layer."""
        for rad, inner, outer, is_major, t in self._ticks:
            if t > ratio:
                continue
            if cooldown:
                color = self._cooldown_color if is_major else self._cooldown_dim
            else:
                color = self._tick_major if is_major else self._tick_lit
            alpha = self.TICK_LIT_MAJOR_ALPHA if is_major else self.TICK_LIT_MINOR_ALPHA
            r2 = outer + (self.TICK_LIT_MAJOR_EXTRA if is_major else self.TICK_LIT_MINOR_EXTRA)
            x1 = cx + math.cos(rad) * inner
            y1 = cy - math.sin(rad) * inner
            x2 = cx + math.cos(rad) * r2
            y2 = cy - math.sin(rad) * r2
            w = self.TICK_LIT_MAJOR_WIDTH if is_major else self.TICK_LIT_MINOR_WIDTH
            pygame.draw.line(surface, (*color, alpha), (x1, y1), (x2, y2), w)

    def _draw_needle(self, surface, cx, cy, r, angle_deg, active, cooldown=False):
        """Pointer needle."""
        rad = math.radians(angle_deg)
        tip_r = r - self.NEEDLE_TIP_INSET
        tip_x = cx + math.cos(rad) * tip_r
        tip_y = cy - math.sin(rad) * tip_r

        back_rad = math.radians(angle_deg + 180)
        tail_x = cx + math.cos(back_rad) * self.NEEDLE_TAIL_LEN
        tail_y = cy - math.sin(back_rad) * self.NEEDLE_TAIL_LEN

        color = self._cooldown_color if cooldown else self._needle_active if active else self._needle_color
        pygame.draw.line(surface, (*color, self.NEEDLE_ALPHA), (cx, cy), (tip_x, tip_y), self.NEEDLE_WIDTH)
        pygame.draw.line(surface, (*color, self.NEEDLE_TAIL_ALPHA), (cx, cy), (tail_x, tail_y), self.NEEDLE_TAIL_WIDTH)
        pygame.draw.circle(surface, (*color, self.NEEDLE_TIP_ALPHA), (int(tip_x), int(tip_y)), self.NEEDLE_TIP_RADIUS)

    def _draw_labels(self, surface, cx, cy, r, current, max_val, active, cooldown=False, dash_active=False):
        """Title, value, min/max, and BOOSTING indicator."""
        title_font = self._get_font(self.LABEL_TITLE_FONT_SIZE)
        label_color = self._cooldown_color if cooldown else self._text_color
        title = title_font.render("加速燃料", True, label_color)
        surface.blit(title, title.get_rect(center=(cx, cy + self.LABEL_TITLE_Y_OFFSET)))

        val_font = self._get_font(self.LABEL_VALUE_FONT_SIZE)
        val_color = self._cooldown_color if cooldown else self._text_bright if active else self._text_color
        val = val_font.render(str(int(current)), True, val_color)
        surface.blit(val, val.get_rect(center=(cx, cy + self.LABEL_VALUE_Y_OFFSET)))

        tiny = self._get_font(self.LABEL_TINY_FONT_SIZE)
        rad_start = math.radians(self.ARC_START_DEG)
        rad_end = math.radians(self.ARC_END_DEG)
        lr = r + self.LABEL_EXTRA_RADIUS

        zero = tiny.render("0", True, self._text_color)
        lx, ly = cx + math.cos(rad_start) * lr, cy - math.sin(rad_start) * lr
        surface.blit(zero, zero.get_rect(center=(lx, ly)))

        full = tiny.render(f"{int(max_val)}", True, self._text_color)
        rx, ry = cx + math.cos(rad_end) * lr, cy - math.sin(rad_end) * lr
        surface.blit(full, full.get_rect(center=(rx, ry)))

        if cooldown or dash_active or active:
            af = self._get_font(self.LABEL_ACTIVE_FONT_SIZE)
            if cooldown:
                text = "突进冷却"
                color = self._cooldown_color
            elif dash_active:
                text = "相位突进"
                color = self._cooldown_color
            else:
                text = "加速中"
                color = self._needle_active
            at = af.render(text, True, (*color, self.LABEL_ACTIVE_ALPHA))
            surface.blit(at, at.get_rect(center=(cx, cy + self.LABEL_ACTIVE_Y_OFFSET)))
