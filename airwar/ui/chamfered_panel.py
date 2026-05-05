"""Chamfered (cut-corner) panel component for military UI style."""
import pygame
from typing import Tuple
from airwar.config.design_tokens import SystemUI


# Cache for rendered panels
_panel_surface_cache = {}
_bg_cache = {}
_border_cache = {}
_glow_cache = {}


def create_chamfered_points(width: int, height: int, chamfer_depth: int) -> list[tuple[int, int]]:
    """Create chamfered polygon points for a rectangle."""
    return [
        (chamfer_depth, 0),
        (width - chamfer_depth, 0),
        (width, chamfer_depth),
        (width, height - chamfer_depth),
        (width - chamfer_depth, height),
        (chamfer_depth, height),
        (0, height - chamfer_depth),
        (0, chamfer_depth),
    ]


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
    points = create_chamfered_points(width, height, chamfer_depth)

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

    if glow_color is not None:
        glow_key = (width, height, chamfer_depth, glow_color)
        if glow_key not in _glow_cache:
            glow_result = pygame.Surface((width + 4, height + 4), pygame.SRCALPHA)
            glow_result.fill((0, 0, 0, 0))
            glow_points = create_chamfered_points(width + 4, height + 4, chamfer_depth + 2)
            pygame.draw.polygon(
                glow_result,
                (*glow_color[:3], int(glow_color[3] * 0.3) if len(glow_color) == 4 else 76),
                glow_points,
            )
            _glow_cache[glow_key] = glow_result
        surface.blit(_glow_cache[glow_key], (x - 2, y - 2))

    # Draw background (from cache)
    bg_key = (width, height, chamfer_depth, bg_color)
    if bg_key not in _bg_cache:
        bg_result = pygame.Surface((width, height), pygame.SRCALPHA)
        bg_result.fill((0, 0, 0, 0))
        chamfer_shape = _get_chamfered_surface(width, height, chamfer_depth).copy()
        chamfer_shape.set_colorkey((0, 0, 0, 0))
        pygame.draw.polygon(chamfer_shape, bg_color if len(bg_color) == 3 else bg_color[:3],
                           create_chamfered_points(width, height, chamfer_depth))
        bg_result.blit(chamfer_shape, (0, 0))
        _bg_cache[bg_key] = bg_result

    surface.blit(_bg_cache[bg_key], (x, y))

    # Draw border on top (from cache)
    if border_color is not None:
        border_key = (width, height, chamfer_depth, border_color)
        if border_key not in _border_cache:
            border_result = pygame.Surface((width, height), pygame.SRCALPHA)
            border_result.fill((0, 0, 0, 0))
            points = create_chamfered_points(width, height, chamfer_depth)
            pygame.draw.lines(border_result,
                             border_color if len(border_color) == 4 else (*border_color, 255),
                             False, points, SystemUI.CHAMFER_BORDER_WIDTH)
            _border_cache[border_key] = border_result
        surface.blit(_border_cache[border_key], (x, y))
