"""Chamfered (cut-corner) panel component for military UI style."""
import pygame
from typing import Tuple
from airwar.config.design_tokens import SystemColors, SystemUI


# Cache for rendered panels
_panel_surface_cache = {}
_bg_cache = {}
_border_cache = {}


def _get_chamfered_surface(width: int, height: int, chamfer_depth: int) -> pygame.Surface:
    """Get or create a cached chamfered panel surface."""
    cache_key = (width, height, chamfer_depth)
    if cache_key not in _panel_surface_cache:
        surf = _create_chamfered_surface(width, height, chamfer_depth)
        _panel_surface_cache[cache_key] = surf
    return _panel_surface_cache[cache_key]


def _create_chamfered_surface(width: int, height: int, chamfer_depth: int) -> pygame.Surface:
    """Create a chamfered (cut-corner) rectangle surface."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    # Create chamfered polygon points (clockwise from top-left)
    points = [
        # Top-left corner cut
        (chamfer_depth, 0),
        (width - chamfer_depth, 0),
        # Top-right corner cut
        (width, chamfer_depth),
        (width, height - chamfer_depth),
        # Bottom-right corner cut
        (width - chamfer_depth, height),
        (chamfer_depth, height),
        # Bottom-left corner cut
        (0, height - chamfer_depth),
        (0, chamfer_depth),
    ]

    # Draw filled polygon
    pygame.draw.polygon(surface, (255, 255, 255, 255), points)

    return surface


def draw_chamfered_panel(
    surface: pygame.Surface,
    x: int,
    y: int,
    width: int,
    height: int,
    bg_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int, int] = None,
    glow_color: Tuple[int, int, int, int] = None,
    chamfer_depth: int = None
) -> None:
    """Draw a chamfered (cut-corner) panel with optional glow border.

    Args:
        surface: Target pygame surface
        x: Left position
        y: Top position
        width: Panel width
        height: Panel height
        bg_color: Background color (RGB)
        border_color: Border color (RGBA), optional
        glow_color: Glow color (RGBA), optional
        chamfer_depth: Cut corner depth, defaults to SystemUI.CHAMFER_DEPTH
    """
    if chamfer_depth is None:
        chamfer_depth = SystemUI.CHAMFER_DEPTH

    # Get cached chamfered surface
    panel_surf = _get_chamfered_surface(width, height, chamfer_depth)

    # Create background surface with color
    bg_surf = panel_surf.copy()
    bg_surf.fill(bg_color + (255,) if len(bg_color) == 3 else bg_color)

    # Apply mask to get chamfered shape
    mask = pygame.mask.Mask((width, height))
    mask.fill()
    # Create outline for masking would be complex, so we use a different approach

    # Draw glow layer first (if specified)
    if glow_color is not None:
        glow_surf = _get_chamfered_surface(width + 4, height + 4, chamfer_depth + 2)
        glow_size = glow_surf.get_size()
        glow_blit_x = x - 2
        glow_blit_y = y - 2

        # Scale glow color alpha
        scaled_glow = (*glow_color[:3], int(glow_color[3] * 0.3))
        glow_filled = pygame.Surface(glow_size, pygame.SRCALPHA)
        glow_filled.fill((0, 0, 0, 0))

        # Create glow shape (from cached base)
        glow_shape = _get_chamfered_surface(width + 4, height + 4, chamfer_depth + 2).copy()
        glow_filled.blit(glow_shape, (0, 0))
        pygame.draw.polygon(glow_filled, scaled_glow,
                           [(chamfer_depth + 2, 0), (width + 2, 0),
                            (width + 2, height + 2), (0, height + 2),
                            (0, chamfer_depth + 2), (width + 2, chamfer_depth + 2)][:4], 0)

        glow_filled.set_colorkey((0, 0, 0, 0))
        glow_mask = _get_chamfered_surface(width + 4, height + 4, chamfer_depth + 2).copy()
        glow_mask.set_colorkey((0, 0, 0, 0))
        pygame.draw.polygon(glow_mask, (255, 255, 255, 255),
                           [(chamfer_depth + 2, 0), (width + 2, 0),
                            (width + 2, height + 2), (0, height + 2),
                            (0, chamfer_depth + 2)])

        surface.blit(glow_filled, (glow_blit_x, glow_blit_y))

    # Draw border (if specified)
    if border_color is not None:
        border_surf = _get_chamfered_surface(width, height, chamfer_depth).copy()
        border_surf.set_colorkey((0, 0, 0, 0))
        pygame.draw.polygon(border_surf, border_color if len(border_color) == 4 else (*border_color, 255),
                          [(chamfer_depth, 0), (width - chamfer_depth, 0),
                           (width, chamfer_depth), (width, height - chamfer_depth),
                           (width - chamfer_depth, height), (chamfer_depth, height),
                           (0, height - chamfer_depth), (0, chamfer_depth)],
                          SystemUI.CHAMFER_BORDER_WIDTH)

    # Draw background (from cache)
    bg_key = (width, height, chamfer_depth, bg_color)
    if bg_key not in _bg_cache:
        bg_result = pygame.Surface((width, height), pygame.SRCALPHA)
        bg_result.fill((0, 0, 0, 0))
        chamfer_shape = _get_chamfered_surface(width, height, chamfer_depth).copy()
        chamfer_shape.set_colorkey((0, 0, 0, 0))
        pygame.draw.polygon(chamfer_shape, bg_color if len(bg_color) == 3 else bg_color[:3],
                           [(chamfer_depth, 0), (width - chamfer_depth, 0),
                            (width, chamfer_depth), (width, height - chamfer_depth),
                            (width - chamfer_depth, height), (chamfer_depth, height),
                            (0, height - chamfer_depth), (0, chamfer_depth)])
        bg_result.blit(chamfer_shape, (0, 0))
        _bg_cache[bg_key] = bg_result

    surface.blit(_bg_cache[bg_key], (x, y))

    # Draw border on top (from cache)
    if border_color is not None:
        border_key = (width, height, chamfer_depth, border_color)
        if border_key not in _border_cache:
            border_result = pygame.Surface((width, height), pygame.SRCALPHA)
            border_result.fill((0, 0, 0, 0))
            points = [
                (chamfer_depth, 0),
                (width - chamfer_depth, 0),
                (width, chamfer_depth),
                (width, height - chamfer_depth),
                (width - chamfer_depth, height),
                (chamfer_depth, height),
                (0, height - chamfer_depth),
                (0, chamfer_depth),
            ]
            pygame.draw.lines(border_result,
                             border_color if len(border_color) == 4 else (*border_color, 255),
                             False, points, SystemUI.CHAMFER_BORDER_WIDTH)
            _border_cache[border_key] = border_result
        surface.blit(_border_cache[border_key], (x, y))


class ChamferedPanel:
    """Reusable chamfered panel component with caching."""

    def __init__(
        self,
        width: int,
        height: int,
        bg_color: Tuple[int, int, int] = None,
        border_color: Tuple[int, int, int, int] = None,
        glow_color: Tuple[int, int, int, int] = None,
        chamfer_depth: int = None
    ):
        """Initialize chamfered panel.

        Args:
            width: Panel width
            height: Panel height
            bg_color: Background color, defaults to SystemColors.BG_PANEL
            border_color: Border color, defaults to SystemColors.BORDER_GLOW
            glow_color: Glow color for outer glow effect
            chamfer_depth: Cut corner depth, defaults to SystemUI.CHAMFER_DEPTH
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color or SystemColors.BG_PANEL
        self.border_color = border_color or SystemColors.BORDER_GLOW
        self.glow_color = glow_color
        self.chamfer_depth = chamfer_depth or SystemUI.CHAMFER_DEPTH

        # Pre-render the panel
        self._rendered_surface = None
        self._render()

    def _render(self) -> None:
        """Pre-render the panel to a cached surface."""
        self._rendered_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self._rendered_surface.fill((0, 0, 0, 0))

        # Draw using the draw function
        draw_chamfered_panel(
            self._rendered_surface,
            0, 0,
            self.width, self.height,
            self.bg_color,
            self.border_color,
            self.glow_color,
            self.chamfer_depth
        )

    def render(self, surface: pygame.Surface, x: int, y: int) -> None:
        """Render the panel to a surface at the specified position.

        Args:
            surface: Target pygame surface
            x: Left position
            y: Top position
        """
        if self._rendered_surface:
            surface.blit(self._rendered_surface, (x, y))

    def render_with_content(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        content_renderer: callable = None
    ) -> None:
        """Render panel with custom content inside.

        Args:
            surface: Target pygame surface
            x: Left position
            y: Top position
            content_renderer: Optional callback(content_surf) to draw content
        """
        # First blit the panel background
        panel_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 0))

        # Create chamfered mask
        mask = _create_chamfered_surface(self.width, self.height, self.chamfer_depth)
        mask.set_colorkey((0, 0, 0, 0))
        pygame.draw.polygon(mask, self.bg_color,
                           [(self.chamfer_depth, 0), (self.width - self.chamfer_depth, 0),
                            (self.width, self.chamfer_depth), (self.width, self.height - self.chamfer_depth),
                            (self.width - self.chamfer_depth, self.height), (self.chamfer_depth, self.height),
                            (0, self.height - self.chamfer_depth), (0, self.chamfer_depth)])
        panel_surf.blit(mask, (0, 0))

        # Draw border
        points = [
            (self.chamfer_depth, 0),
            (self.width - self.chamfer_depth, 0),
            (self.width, self.chamfer_depth),
            (self.width, self.height - self.chamfer_depth),
            (self.width - self.chamfer_depth, self.height),
            (self.chamfer_depth, self.height),
            (0, self.height - self.chamfer_depth),
            (0, self.chamfer_depth),
        ]
        pygame.draw.lines(panel_surf,
                         self.border_color if len(self.border_color) == 4 else (*self.border_color, 255),
                         False, points, SystemUI.CHAMFER_BORDER_WIDTH)

        # Apply content if provided
        if content_renderer:
            content_renderer(panel_surf)

        surface.blit(panel_surf, (x, y))
