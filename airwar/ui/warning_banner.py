"""Warning banner — slide-in tech alert panel for mothership ammo depletion."""
import math
import pygame
from airwar.utils.fonts import get_cjk_font


class WarningBanner:
    """Top-of-screen slide-in warning panel.

    Slides in from the top when ammo is critically low, displays a pulsing
    static warning, then slides out before triggering departure. No scrolling
    text — clean, readable, modern tech-alert style.

    Lifecycle: INACTIVE → ENTERING → HOLDING → EXITING → (callback) → INACTIVE
    Timing is wall-clock driven via pygame.time.get_ticks().
    """

    WARNING_TEXT = "母舰弹药耗尽"
    SUB_TEXT = "准备脱离"
    BANNER_HEIGHT = 60
    HAZARD_WIDTH = 70
    HAZARD_STRIPE = 10
    ENTER_DURATION = 0.55     # seconds — ease-out slide in
    HOLD_DURATION = 4.0       # seconds — static pulse display
    EXIT_DURATION = 0.45      # seconds — ease-in slide out

    # Text colors
    WARNING_TEXT_COLOR = (255, 160, 40)
    SUB_TEXT_COLOR = (220, 130, 50)

    # Timing constraints
    MAX_ELAPSED = 0.1
    PULSE_MULT = 3.0

    # Animation exponents (cubic)
    EASE_OUT_EXP = 3
    EASE_IN_EXP = 3

    # Layout
    BANNER_Y_FRACTION = 0.12

    # Pulse overlay
    PULSE_BASE = 0.8
    PULSE_AMPLITUDE = 0.2
    DIM_ALPHA_MAX = 60

    # Glow bar
    GLOW_FREQUENCY = 1.5
    GLOW_ALPHA_BASE = 60
    GLOW_ALPHA_RANGE = 40
    GLOW_BAR_COLOR = (255, 140, 20)
    GLOW_BAR_HEIGHT = 4

    # Text positions
    TEXT_CENTERY = 22
    SUBTEXT_CENTERY = 44

    # Banner background
    BANNER_BG_COLOR = (28, 16, 8, 215)
    ACCENT_TOP_COLOR = (255, 140, 20, 140)
    ACCENT_BOTTOM_COLOR = (255, 100, 10, 140)
    ACCENT_MID_COLOR = (255, 160, 40, 50)
    ACCENT_TOP_WIDTH = 2
    ACCENT_BOTTOM_WIDTH = 2
    ACCENT_MID_WIDTH = 1

    # Corner brackets
    BRACKET_COLOR = (255, 140, 20, 170)
    BRACKET_LENGTH = 12
    BRACKET_THICKNESS = 2
    BRACKET_MARGIN = 4
    BRACKET_TOP = 6

    # Hazard stripes
    HAZARD_STRIPE_COLOR = (255, 150, 20, 90)
    HAZARD_BG_COLOR = (40, 20, 5, 180)

    _STATE_INACTIVE = 0
    _STATE_ENTERING = 1
    _STATE_HOLDING = 2
    _STATE_EXITING = 3

    def __init__(self):
        self._state = self._STATE_INACTIVE
        self._state_time = 0.0
        self._on_complete = None
        self._banner_cache = None
        self._banner_cache_key = (0,)
        self._main_font: pygame.font.Font = None
        self._sub_font: pygame.font.Font = None
        self._main_text: pygame.Surface = None
        self._sub_text: pygame.Surface = None
        self._pulse_phase = 0.0
        self._y_offset = 0.0  # current vertical offset from target position
        self._last_tick: int = 0

    @property
    def is_active(self) -> bool:
        return self._state != self._STATE_INACTIVE

    def activate(self, on_complete=None) -> bool:
        """Activate: panel slides in, holds, slides out, then calls on_complete.

        Returns:
            True if banner was activated, False if already active.
        """
        if self._state != self._STATE_INACTIVE:
            return False
        self._state = self._STATE_ENTERING
        self._state_time = 0.0
        self._pulse_phase = 0.0
        self._y_offset = -self.BANNER_HEIGHT
        self._on_complete = on_complete
        self._last_tick = pygame.time.get_ticks()

        if self._main_font is None:
            self._main_font = get_cjk_font(28)
            self._sub_font = get_cjk_font(20)
        self._main_text = self._main_font.render(
            self.WARNING_TEXT, True, self.WARNING_TEXT_COLOR)
        self._sub_text = self._sub_font.render(
            self.SUB_TEXT, True, self.SUB_TEXT_COLOR)
        return True

    def reset(self) -> None:
        self._state = self._STATE_INACTIVE
        self._state_time = 0.0
        self._on_complete = None
        self._y_offset = 0.0

    def update(self) -> None:
        if self._state == self._STATE_INACTIVE:
            return

        now = pygame.time.get_ticks()
        elapsed = (now - self._last_tick) / 1000.0
        self._last_tick = now
        if elapsed > self.MAX_ELAPSED:
            elapsed = self.MAX_ELAPSED

        self._state_time += elapsed
        self._pulse_phase += elapsed * self.PULSE_MULT

        if self._state == self._STATE_ENTERING:
            t = min(self._state_time / self.ENTER_DURATION, 1.0)
            # Ease-out-cubic: slide from above to resting position
            eased = 1.0 - (1.0 - t) ** self.EASE_OUT_EXP
            self._y_offset = -self.BANNER_HEIGHT * (1.0 - eased)
            if t >= 1.0:
                self._state = self._STATE_HOLDING
                self._state_time = 0.0
                self._y_offset = 0.0

        elif self._state == self._STATE_HOLDING:
            if self._state_time >= self.HOLD_DURATION:
                self._state = self._STATE_EXITING
                self._state_time = 0.0

        elif self._state == self._STATE_EXITING:
            t = min(self._state_time / self.EXIT_DURATION, 1.0)
            # Ease-in-cubic: slide up and away
            eased = t ** self.EASE_IN_EXP
            self._y_offset = -self.BANNER_HEIGHT * eased
            if t >= 1.0:
                self._state = self._STATE_INACTIVE
                self._y_offset = -self.BANNER_HEIGHT
                if self._on_complete:
                    cb = self._on_complete
                    self._on_complete = None
                    cb()

    def render(self, surface: pygame.Surface) -> None:
        if self._state == self._STATE_INACTIVE:
            return

        screen_w = surface.get_width()
        target_y = int(surface.get_height() * self.BANNER_Y_FRACTION)
        banner_y = target_y + int(self._y_offset)

        # Build/cache background
        cache_key = (screen_w,)
        if self._banner_cache is None or self._banner_cache_key != cache_key:
            self._banner_cache = self._build_banner_bg(screen_w)
            self._banner_cache_key = cache_key

        # Draw cached banner
        surface.blit(self._banner_cache, (0, banner_y))

        # Pulse dimming — simple dark overlay instead of copy+BLEND_RGBA_MULT
        pulse = self.PULSE_BASE + self.PULSE_AMPLITUDE * math.sin(self._pulse_phase)
        dim_alpha = int(self.DIM_ALPHA_MAX * (1.0 - pulse))
        if dim_alpha > 5:
            dim_rect = pygame.Rect(0, banner_y, screen_w, self.BANNER_HEIGHT)
            pygame.draw.rect(surface, (0, 0, 0, dim_alpha), dim_rect)

        # Glow bar at bottom edge
        glow_alpha = int(self.GLOW_ALPHA_BASE + self.GLOW_ALPHA_RANGE * math.sin(self._pulse_phase * self.GLOW_FREQUENCY))
        pygame.draw.rect(surface, (*self.GLOW_BAR_COLOR, glow_alpha),
                         (0, banner_y + self.BANNER_HEIGHT - self.GLOW_BAR_HEIGHT, screen_w, self.GLOW_BAR_HEIGHT))

        # Centered text
        if self._main_text and self._sub_text:
            main_rect = self._main_text.get_rect(
                center=(screen_w // 2, banner_y + self.TEXT_CENTERY))
            sub_rect = self._sub_text.get_rect(
                center=(screen_w // 2, banner_y + self.SUBTEXT_CENTERY))
            surface.blit(self._main_text, main_rect)
            surface.blit(self._sub_text, sub_rect)

    def _build_banner_bg(self, screen_w: int) -> pygame.Surface:
        """Pre-render banner background with hazard stripes and tech frame."""
        h = self.BANNER_HEIGHT
        surf = pygame.Surface((screen_w, h), pygame.SRCALPHA)

        # Dark panel
        pygame.draw.rect(surf, self.BANNER_BG_COLOR, surf.get_rect())

        # Accent lines
        pygame.draw.line(surf, self.ACCENT_TOP_COLOR, (0, 0), (screen_w, 0), self.ACCENT_TOP_WIDTH)
        pygame.draw.line(surf, self.ACCENT_BOTTOM_COLOR, (0, h - 1), (screen_w, h - 1), self.ACCENT_BOTTOM_WIDTH)
        pygame.draw.line(surf, self.ACCENT_MID_COLOR, (0, 3), (screen_w, 3), self.ACCENT_MID_WIDTH)

        # Hazard stripes on sides
        self._draw_hazard_stripes(surf, 0, self.HAZARD_WIDTH)
        self._draw_hazard_stripes(surf, screen_w - self.HAZARD_WIDTH, self.HAZARD_WIDTH)

        # Tech corner brackets
        bl, bt = self.BRACKET_LENGTH, self.BRACKET_THICKNESS
        hw = self.HAZARD_WIDTH
        m, t = self.BRACKET_MARGIN, self.BRACKET_TOP
        pygame.draw.rect(surf, self.BRACKET_COLOR, (hw + m, t, bl, bt))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (hw + m, t, bt, bl))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (screen_w - hw - m - bl, t, bl, bt))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (screen_w - hw - m - bt, t, bt, bl))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (hw + m, h - t - bt, bl, bt))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (hw + m, h - t - bl, bt, bl))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (screen_w - hw - m - bl, h - t - bt, bl, bt))
        pygame.draw.rect(surf, self.BRACKET_COLOR, (screen_w - hw - m - bt, h - t - bl, bt, bl))

        return surf

    def _draw_hazard_stripes(self, surf: pygame.Surface, start_x: int, width: int) -> None:
        h = self.BANNER_HEIGHT
        stripe_color = self.HAZARD_STRIPE_COLOR
        bg_stripe = self.HAZARD_BG_COLOR

        pygame.draw.rect(surf, bg_stripe, (start_x, 0, width, h))

        stripe_w = self.HAZARD_STRIPE
        step = stripe_w * 2
        for offset in range(-h, width + h, step):
            points = [
                (start_x + offset, h),
                (start_x + offset + stripe_w, h),
                (start_x + offset + stripe_w + h, 0),
                (start_x + offset + h, 0),
            ]
            try:
                pygame.draw.polygon(surf, stripe_color, points)
            except (ValueError, pygame.error):
                pass
