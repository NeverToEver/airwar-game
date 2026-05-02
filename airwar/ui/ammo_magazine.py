"""Ammo magazine UI — vertical sci-fi ammunition rack for mothership cooldown/duration."""
import math
import pygame
from airwar.utils.fonts import get_cjk_font
from airwar.config.design_tokens import SystemColors


class AmmoMagazine:
    """Vertical ammo magazine display on the left side of screen.

    Shows 10 ammo cells that fill/empty to represent mothership cooldown
    and docked stay duration. Military sci-fi aesthetic with metallic frame,
    glowing cells, and corner rivet details.
    """

    CELL_COUNT = 10
    CELL_WIDTH = 48
    CELL_HEIGHT = 16
    CELL_GAP = 4
    WARNING_CELL_THRESHOLD = 3  # bottom N cells turn red when ammo is low
    FRAME_PAD_X = 9
    FRAME_PAD_TOP = 28
    FRAME_PAD_BOTTOM = 14
    FRAME_RADIUS = 6

    def __init__(self):
        self._frame_color = (35, 50, 70)
        self._frame_border = (60, 85, 115)
        self._cell_empty = (25, 35, 50)
        self._cell_empty_border = (40, 55, 75)
        self._cell_filled = (60, 200, 240)
        self._cell_glow = (40, 140, 200)
        self._cell_warning = (240, 80, 40)
        self._cell_warning_glow = (200, 50, 20)
        self._text_color = SystemColors.TEXT_DIM
        self._label_font: pygame.font.Font = None
        self._count_font: pygame.font.Font = None
        self._frame_cache = None
        self._frame_cache_key = (0, 0)
        self._pulse_phase = 0.0

    @property
    def frame_width(self) -> int:
        return self.CELL_WIDTH + self.FRAME_PAD_X * 2

    @property
    def frame_height(self) -> int:
        return (self.CELL_COUNT * self.CELL_HEIGHT +
                (self.CELL_COUNT - 1) * self.CELL_GAP +
                self.FRAME_PAD_TOP + self.FRAME_PAD_BOTTOM)

    def _ensure_fonts(self):
        if self._label_font is None:
            self._label_font = get_cjk_font(16)
        if self._count_font is None:
            self._count_font = get_cjk_font(13)

    def _build_frame_cache(self, w: int, h: int) -> pygame.Surface:
        """Pre-render the metallic frame with corner rivets."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except pygame.error:
            pass

        r = self.FRAME_RADIUS

        # Frame background
        pygame.draw.rect(surf, (*self._frame_color, 220),
                         surf.get_rect(), border_radius=r)

        # Inner border accent
        inner = surf.get_rect().inflate(-2, -2)
        pygame.draw.rect(surf, (*self._frame_border, 50),
                         inner, width=1, border_radius=max(r - 1, 2))

        # Outer border
        pygame.draw.rect(surf, (*self._frame_border, 110),
                         surf.get_rect(), width=1, border_radius=r)

        # Corner rivets
        rivet_color = (*self._frame_border, 140)
        rivet_r = 2
        corners = [
            (r + 2, r + 2),
            (w - r - 2, r + 2),
            (r + 2, h - r - 2),
            (w - r - 2, h - r - 2),
        ]
        for cx, cy in corners:
            pygame.draw.circle(surf, rivet_color, (cx, cy), rivet_r)

        return surf

    def render(self, surface: pygame.Surface, ammo_count: float,
               ammo_max: float, *, is_cooldown: bool, is_docked: bool,
               is_warning: bool, is_present: bool) -> None:
        """Render the ammo magazine.

        Args:
            ammo_count: Current ammo value (0.0 ~ ammo_max).
            ammo_max: Maximum ammo (equals CELL_COUNT).
            is_cooldown: True during COOLDOWN state (ammo filling up).
            is_docked: True during DOCKED state (ammo depleting).
            is_warning: True when ammo is critically low.
            is_present: True when mothership is active/present.
        """
        if not is_present and ammo_count <= 0 and not is_cooldown:
            return  # Hide when not relevant

        self._ensure_fonts()
        self._pulse_phase += 0.05

        screen_h = surface.get_height()
        fw = self.frame_width
        fh = self.frame_height
        fx = 9
        fy = screen_h // 2 - fh // 2

        # Cache frame background
        cache_key = (fw, fh)
        if self._frame_cache is None or self._frame_cache_key != cache_key:
            self._frame_cache = self._build_frame_cache(fw, fh)
            self._frame_cache_key = cache_key
        surface.blit(self._frame_cache, (fx, fy))

        # Header label
        label = self._label_font.render("母舰", True, self._text_color)
        label_rect = label.get_rect(center=(fx + fw // 2, fy + 14))
        surface.blit(label, label_rect)

        # Draw cells
        cells_start_y = fy + self.FRAME_PAD_TOP
        cells_x = fx + self.FRAME_PAD_X

        filled_cells = max(0.0, min(ammo_count, ammo_max))
        full_cells = int(filled_cells)
        partial = filled_cells - full_cells

        for i in range(self.CELL_COUNT):
            cell_idx = self.CELL_COUNT - 1 - i  # fill from bottom
            cy = cells_start_y + cell_idx * (self.CELL_HEIGHT + self.CELL_GAP)

            if i < full_cells:
                # Fully filled
                cell_color = self._cell_warning if (is_warning and i < self.WARNING_CELL_THRESHOLD) else self._cell_filled
                glow_color = self._cell_warning_glow if (is_warning and i < 3) else self._cell_glow
                if is_cooldown:
                    pulse = 0.7 + 0.3 * math.sin(self._pulse_phase * 2.0)
                    alpha = int(180 + 40 * pulse)
                else:
                    alpha = 220
                self._draw_cell(surface, cells_x, cy, cell_color, glow_color, alpha, 1.0)
            elif i == full_cells and partial > 0.01:
                # Partially filled
                cell_color = self._cell_warning if is_warning else self._cell_filled
                glow_color = self._cell_warning_glow if is_warning else self._cell_glow
                self._draw_cell(surface, cells_x, cy, cell_color, glow_color, 200, partial)
            else:
                # Empty
                self._draw_cell(surface, cells_x, cy, None, None, 0, 0.0)

        # Ammo count footer
        count_text = f"{int(ammo_count)}/{int(ammo_max)}"
        count_color = (240, 120, 60) if is_warning else self._text_color
        count_surf = self._count_font.render(count_text, True, count_color)
        count_rect = count_surf.get_rect(
            center=(fx + fw // 2, fy + fh - self.FRAME_PAD_BOTTOM // 2 - 1))
        surface.blit(count_surf, count_rect)

    def _draw_cell(self, surface, x, y, fill_color, glow_color, alpha, ratio):
        """Draw a single ammo cell with optional fill and glow."""
        cw = self.CELL_WIDTH
        ch = self.CELL_HEIGHT
        radius = 3

        # Empty background
        bg_rect = pygame.Rect(x, y, cw, ch)
        pygame.draw.rect(surface, (*self._cell_empty, 160), bg_rect, border_radius=radius)
        pygame.draw.rect(surface, (*self._cell_empty_border, 70), bg_rect, width=1,
                         border_radius=radius)

        if fill_color and ratio > 0:
            fill_width = int(cw * ratio)
            if fill_width > 0:
                fill_rect = pygame.Rect(x, y, fill_width, ch)

                # Glow halo
                glow_surf = pygame.Surface((fill_width + 6, ch + 6), pygame.SRCALPHA)
                glow_alpha = int(alpha * 0.3)
                pygame.draw.rect(glow_surf, (*glow_color, glow_alpha),
                                 glow_surf.get_rect(), border_radius=radius + 1)
                surface.blit(glow_surf, (x - 3, y - 3))

                # Fill bar
                fill_surf = pygame.Surface((fill_width, ch), pygame.SRCALPHA)
                pygame.draw.rect(fill_surf, (*fill_color, alpha),
                                 fill_surf.get_rect(), border_radius=radius)
                surface.blit(fill_surf, (x, y))

                # Bright top-edge highlight
                if fill_width > 4:
                    hl_surf = pygame.Surface((fill_width - 4, 3), pygame.SRCALPHA)
                    hl_alpha = min(140, alpha + 40)
                    pygame.draw.rect(hl_surf, (*fill_color, hl_alpha),
                                     hl_surf.get_rect(), border_radius=1)
                    surface.blit(hl_surf, (x + 2, y + 2))
