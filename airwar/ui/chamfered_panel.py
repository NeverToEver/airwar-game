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
