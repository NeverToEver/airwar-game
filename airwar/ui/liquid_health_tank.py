"""Liquid health tank — glass canister with physics-driven fluid animation for HP."""
import math
import random
import pygame


class LiquidHealthTank:
    """Glass-canister health display with spring-physics liquid animation.

    Only the liquid carries bright color (green/amber/red by HP ratio).
    The empty space above the liquid exposes a dark black-steel housing —
    just like a real fuel gauge. Spring physics give the liquid surface
    natural overshoot and wave motion on HP changes.
    """

    def __init__(self, width: int = 60, height: int = 230):
        self._w = width
        self._h = height

        # Spring-physics state
        self._liquid_level = 1.0
        self._liquid_velocity = 0.0
        self._target_level = 1.0
        self._spring_k = 8.0
        self._spring_damping = 3.5
        self._disturbance = 0.0

        self._wave_phase = 0.0
        self._bubbles: list = []
        self._bubble_timer = 0.0

        # Cached surfaces
        self._frame_cache = None
        self._frame_key = (0, 0)
        self._steel_bg_cache = None
        self._steel_bg_key = (0, 0)
        self._liquid_surf: pygame.Surface = None
        self._liquid_key = (0, 0)
        self._last_tick = pygame.time.get_ticks()
        self._pct_font: pygame.font.Font = None

        # Interior region
        self._itop = 14
        self._ibot = height - 14
        self._ih = self._ibot - self._itop

        # Color stops: ratio → (r, g, b)
        self._color_stops = [
            (1.0,  (80, 210, 115)),
            (0.5,  (195, 180, 55)),
            (0.25, (225, 85, 45)),
            (0.0,  (215, 40, 40)),
        ]

    # ── Public API ───────────────────────────────────────────────────────────

    def set_health(self, current: int, max_hp: int) -> None:
        new_target = max(0.0, min(1.0, current / max_hp if max_hp > 0 else 0))
        delta = abs(new_target - self._target_level)
        self._target_level = new_target
        if delta > 0.05:
            self._disturbance = min(1.0, self._disturbance + delta * 2.5)

    def update(self) -> None:
        now = pygame.time.get_ticks()
        dt = (now - self._last_tick) / 1000.0
        self._last_tick = now
        if dt > 0.1:
            dt = 0.1

        displacement = self._target_level - self._liquid_level
        self._liquid_velocity += (displacement * self._spring_k
                                  - self._liquid_velocity * self._spring_damping) * dt
        self._liquid_level += self._liquid_velocity * dt

        if self._liquid_level < 0.0:
            self._liquid_level = 0.0
            if self._liquid_velocity < 0:
                self._liquid_velocity *= -0.3
        elif self._liquid_level > 1.0:
            self._liquid_level = 1.0
            if self._liquid_velocity > 0:
                self._liquid_velocity *= -0.3

        if (abs(displacement) < 0.0008 and abs(self._liquid_velocity) < 0.002
                and abs(self._target_level - self._liquid_level) < 0.001):
            self._liquid_level = self._target_level
            self._liquid_velocity = 0.0

        self._wave_phase += dt * 3.0
        self._disturbance = max(0.0, self._disturbance - dt * 0.8)

        self._bubble_timer += dt
        if self._bubble_timer > 0.18 and self._liquid_level > 0.04:
            self._bubble_timer = 0.0
            if len(self._bubbles) < 8:
                bx = random.uniform(6, self._w - 6)
                self._bubbles.append([bx, 0.0, random.uniform(0.5, 1.5),
                                      random.uniform(1.2, 4.0)])
        for b in self._bubbles[:]:
            b[1] += b[3] * dt * 15
            if b[1] > 1.0:
                self._bubbles.remove(b)

    # ── Surface helpers ──────────────────────────────────────────────────────

    def _ensure_surfaces(self) -> None:
        w, h = self._w, self._h
        fkey = (w, h)
        if self._frame_cache is None or self._frame_key != fkey:
            self._frame_cache = self._build_frame(w, h)
            self._frame_key = fkey
        if self._steel_bg_cache is None or self._steel_bg_key != fkey:
            self._steel_bg_cache = self._build_steel_bg(w, h)
            self._steel_bg_key = fkey
        if self._liquid_surf is None or self._liquid_key != fkey:
            self._liquid_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            self._liquid_key = fkey

    def _build_frame(self, w: int, h: int) -> pygame.Surface:
        """Border-only frame — interior left transparent for tank bg + liquid."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        r = 10

        # Outer border
        pygame.draw.rect(surf, (55, 65, 90, 220),
                         (0, 0, w, h), width=2, border_radius=r)
        # Inner hairline
        pygame.draw.rect(surf, (35, 45, 65, 100),
                         (4, 4, w - 8, h - 8), width=1, border_radius=r - 2)

        # Caps
        ch = 10
        pygame.draw.rect(surf, (50, 60, 82, 220),
                         (3, 3, w - 6, ch), border_radius=4)
        pygame.draw.rect(surf, (50, 60, 82, 220),
                         (3, h - ch - 3, w - 6, ch), border_radius=4)
        pygame.draw.line(surf, (80, 90, 115, 100), (6, 3), (w - 6, 3), 1)
        pygame.draw.line(surf, (80, 90, 115, 100), (6, h - 3), (w - 6, h - 3), 1)

        # Rivets
        rv = (100, 110, 135, 150)
        for cx, cy in [(r - 1, r - 1), (w - r + 1, r - 1),
                       (r - 1, h - r + 1), (w - r + 1, h - r + 1)]:
            pygame.draw.circle(surf, rv, (cx, cy), 2)

        # Left reflection
        pygame.draw.rect(surf, (150, 170, 200, 22),
                         (7, 18, 4, h - 36), border_radius=2)

        return surf

    def _build_steel_bg(self, w: int, h: int) -> pygame.Surface:
        """Pre-render the black-steel housing interior. Cached permanently."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        ix, iy = 3, self._itop
        iw, ih = w - 6, self._ih

        for row in range(ih):
            t = row / max(ih - 1, 1)
            sr = int(32 - t * 10)
            sg = int(30 - t * 9)
            sb = int(28 - t * 8)
            pygame.draw.line(surf, (sr, sg, sb, 240),
                             (ix, iy + row), (ix + iw - 1, iy + row), 1)

        for gy in range(iy + 5, iy + ih, 8):
            pygame.draw.line(surf, (48, 44, 40, 40),
                             (ix + 1, gy), (ix + iw - 1, gy), 1)

        return surf

    def _liquid_color(self, ratio: float) -> tuple:
        stops = self._color_stops
        if ratio >= stops[0][0]:
            return stops[0][1]
        if ratio <= stops[-1][0]:
            return stops[-1][1]
        for i in range(len(stops) - 1):
            r_hi, c_hi = stops[i]
            r_lo, c_lo = stops[i + 1]
            if r_lo <= ratio <= r_hi:
                t = (ratio - r_lo) / (r_hi - r_lo) if r_hi != r_lo else 0
                return tuple(int(c_lo[j] + (c_hi[j] - c_lo[j]) * t) for j in range(3))
        return stops[-1][1]

    # ── Render ───────────────────────────────────────────────────────────────

    def render(self, surface: pygame.Surface, x: int, y: int) -> None:
        self._ensure_surfaces()
        w, h = self._w, self._h
        level = self._liquid_level
        lc = self._liquid_color(level)
        itop, ibot, ih = self._itop, self._ibot, self._ih

        # ── 1. Black-steel housing (cached) ──
        surface.blit(self._steel_bg_cache, (x, y))

        # ── 2. Draw colored liquid (bottom → surface_y) ──
        ix, iw_full = 3, w - 6
        surface_y = ibot - level * ih
        self._liquid_surf.fill((0, 0, 0, 0))

        body_top = int(surface_y)
        if body_top < ibot:
            body_h = ibot - body_top
            if body_h > 0:
                bands = min(10, body_h)
                band_h = body_h // bands
                for bi in range(bands):
                    t = bi / max(bands - 1, 1)
                    alpha = 200 + int(40 * (1.0 - t))
                    by = body_top + bi * band_h
                    bh = band_h if bi < bands - 1 else ibot - by
                    if bh > 0:
                        pygame.draw.rect(self._liquid_surf, (*lc, alpha),
                                         (ix, by, iw_full, bh))

        # Wave surface
        if level > 0.008:
            base_amp = 3.0 + (1.0 - level) * 2.5
            disturb_boost = 1.0 + self._disturbance * 2.0
            wave_amp = base_amp * disturb_boost
            wave_pts = []
            steps = 24
            for i in range(steps + 1):
                px = ix + iw_full * i / steps
                w1 = math.sin(self._wave_phase + i * 0.75) * wave_amp
                w2 = math.sin(self._wave_phase * 1.8 + i * 0.45) * wave_amp * 0.5
                w3 = math.sin(self._wave_phase * 0.6 + i * 0.3) * wave_amp * 0.25
                wave_pts.append((px, surface_y + w1 + w2 + w3))
            if len(wave_pts) >= 2:
                wave_poly = wave_pts + [(ix + iw_full, itop), (ix, itop)]
                try:
                    pygame.draw.polygon(self._liquid_surf, (*lc, 215), wave_poly)
                except (ValueError, pygame.error):
                    pass
                try:
                    pygame.draw.lines(self._liquid_surf, (255, 255, 255, 45),
                                      False, wave_pts, 1)
                except (ValueError, pygame.error):
                    pass

        # Bubbles
        for bx, by_prog, bsize, _ in self._bubbles:
            bubble_y = ibot - by_prog * ih * level
            if itop < bubble_y < ibot:
                alpha = 50 + int(35 * (1.0 - by_prog))
                pygame.draw.circle(self._liquid_surf, (210, 225, 240, alpha),
                                   (int(ix + bx), int(bubble_y)), max(1, int(bsize)))

        # Blit liquid with clip
        old_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(x + ix, y + itop, iw_full, ih))
        surface.blit(self._liquid_surf, (x, y))
        surface.set_clip(old_clip)

        # ── 3. Glass frame on top ──
        surface.blit(self._frame_cache, (x, y))

        # ── 4. HP label ──
        if self._pct_font is None:
            self._pct_font = pygame.font.Font(None, 20)
        label = self._pct_font.render(f"{int(level * 100)}%", True, lc)
        surface.blit(label, label.get_rect(center=(x + w // 2, y + h + 14)))
