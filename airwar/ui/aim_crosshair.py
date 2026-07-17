"""Mouse-following aim crosshair for gameplay."""

import math

import pygame

from airwar.config.design_tokens import get_design_tokens


class AimCrosshair:
    """Render a compact modern crosshair at the current mouse position."""

    RADIUS = 18
    INNER_RADIUS = 5
    GAP = 8
    LINE_LENGTH = 14
    LINE_WIDTH = 2
    PULSE_SPEED = 0.04
    _ARC_ANGLES = (
        (math.radians(18), math.radians(78)),
        (math.radians(108), math.radians(168)),
        (math.radians(198), math.radians(258)),
        (math.radians(288), math.radians(348)),
    )

    def __init__(self) -> None:
        self._tokens = get_design_tokens()
        self._frame = 0
        self._glow_cache: dict[tuple[int, tuple[int, int, int], int], pygame.Surface] = {}

    def update(self) -> None:
        self._frame += 1

    def render(self, surface: pygame.Surface, position: tuple[float, float]) -> None:
        x, y = int(position[0]), int(position[1])
        pulse = (math.sin(self._frame * self.PULSE_SPEED) + 1.0) * 0.5
        colors = self._tokens.system
        accent = colors.ACCENT_BRIGHT
        dim = colors.ACCENT_DIM
        glow_alpha = int(14 + 8 * pulse)

        glow_size = self.RADIUS * 4
        glow = self._get_glow_surface(glow_size, accent, glow_alpha)
        glow_center = (glow_size // 2, glow_size // 2)
        surface.blit(glow, (x - glow_center[0], y - glow_center[1]))

        ring_rect = pygame.Rect(0, 0, self.RADIUS * 2, self.RADIUS * 2)
        ring_rect.center = (x, y)
        arc_width = 2
        for start_angle, end_angle in self._ARC_ANGLES:
            pygame.draw.arc(surface, accent, ring_rect, start_angle, end_angle, arc_width)

        line_color = (*dim, 185)
        pygame.draw.line(surface, line_color, (x - self.GAP - self.LINE_LENGTH, y), (x - self.GAP, y), self.LINE_WIDTH)
        pygame.draw.line(surface, line_color, (x + self.GAP, y), (x + self.GAP + self.LINE_LENGTH, y), self.LINE_WIDTH)
        pygame.draw.line(surface, line_color, (x, y - self.GAP - self.LINE_LENGTH), (x, y - self.GAP), self.LINE_WIDTH)
        pygame.draw.line(surface, line_color, (x, y + self.GAP), (x, y + self.GAP + self.LINE_LENGTH), self.LINE_WIDTH)

        pygame.draw.circle(surface, accent, (x, y), self.INNER_RADIUS, width=1)
        pygame.draw.circle(surface, (180, 220, 228), (x, y), 2)

    def _get_glow_surface(
        self, glow_size: int, accent: tuple[int, int, int], glow_alpha: int
    ) -> pygame.Surface:
        """Return the cached glow for one of the small number of pulse alpha values."""
        cache_key = (glow_size, accent, glow_alpha)
        glow = self._glow_cache.get(cache_key)
        if glow is None:
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            glow_center = (glow_size // 2, glow_size // 2)
            pygame.draw.circle(glow, (*accent, glow_alpha), glow_center, self.RADIUS + 7, width=2)
            pygame.draw.circle(glow, (*accent, max(16, glow_alpha // 2)), glow_center, self.INNER_RADIUS + 4)
            self._glow_cache[cache_key] = glow
        return glow
