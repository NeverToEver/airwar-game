"""Shared UI rendering utilities for scene files.

Consolidates duplicated rendering code across death_scene.py, pause_scene.py,
and exit_confirm_scene.py into a single utility class.
"""

import pygame
from typing import List, Optional, Tuple
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.config.design_tokens import SceneColors
from airwar.utils.responsive import ResponsiveHelper


def draw_centered_option_box(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    y: int,
    is_selected: bool,
    box_width: int,
    box_height: int,
    selected_bg_color: Tuple[int, int, int],
    selected_border_color: Tuple[int, int, int],
    unselected_bg_color: Tuple[int, int, int],
    unselected_border_color: Tuple[int, int, int],
    selected_glow_color: Tuple[int, int, int],
    selected_text_color: Tuple[int, int, int],
    unselected_text_color: Tuple[int, int, int],
    glow_layers: int = 3,
    glow_alpha_divisor: int = 50,
    selected_border_width: int = 3,
    unselected_border_width: int = 2,
    border_radius: int = 12,
) -> pygame.Rect:
    """Draw a centered menu option box and return its rect."""
    width = surface.get_width()
    center_x = width // 2

    arrow = ">> " if is_selected else "   "
    display_text = f"{arrow}{text}"
    box_width = adaptive_box_width(font, display_text, box_width, width)
    box_rect = pygame.Rect(
        center_x - box_width // 2, y - box_height // 2, box_width, box_height
    )

    if is_selected:
        for i in range(glow_layers, 0, -1):
            glow_rect = box_rect.inflate(i * 4, i * 4)
            glow_surf = pygame.Surface(
                (glow_rect.width, glow_rect.height), pygame.SRCALPHA
            )
            pygame.draw.rect(
                glow_surf,
                (*selected_glow_color, glow_alpha_divisor // i),
                glow_surf.get_rect(),
            )
            surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, selected_bg_color, box_rect, border_radius=border_radius)
        pygame.draw.rect(
            surface,
            selected_border_color,
            box_rect,
            selected_border_width,
            border_radius=border_radius,
        )
    else:
        pygame.draw.rect(surface, unselected_bg_color, box_rect, border_radius=border_radius)
        pygame.draw.rect(
            surface,
            unselected_border_color,
            box_rect,
            unselected_border_width,
            border_radius=border_radius,
        )

    option_text = fit_text_to_width(
        font,
        display_text,
        selected_text_color if is_selected else unselected_text_color,
        box_rect.width - 48,
    )
    text_rect = option_text.get_rect(center=(center_x, y))
    surface.blit(option_text, text_rect)
    return box_rect


def fit_string_to_width(
    font: pygame.font.Font,
    text: str,
    max_width: int,
    ellipsis: str = "...",
) -> str:
    """Return text truncated to fit max_width using font metrics."""
    if max_width <= 0 or not text:
        return ""
    if font.size(text)[0] <= max_width:
        return text

    ellipsis_width = font.size(ellipsis)[0]
    if ellipsis_width > max_width:
        return ""

    lo = 0
    hi = len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid] + ellipsis
        if font.size(candidate)[0] <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def fit_text_to_width(
    font: pygame.font.Font,
    text: str,
    color: Tuple[int, int, int],
    max_width: int,
    ellipsis: str = "...",
) -> pygame.Surface:
    """Render text guaranteed not to exceed max_width."""
    return font.render(
        fit_string_to_width(font, text, max_width, ellipsis),
        True,
        color,
    )


def wrap_text(
    text: str,
    font: pygame.font.Font,
    max_width: int,
    max_lines: Optional[int] = None,
) -> List[str]:
    """Wrap text by measured width, handling both spaced and CJK text."""
    if max_width <= 0:
        return [""]
    if not text:
        return [""]

    tokens = text.split(" ") if " " in text else list(text)
    use_spaces = " " in text
    lines: List[str] = []
    current = ""

    for token in tokens:
        candidate = f"{current} {token}" if current and use_spaces else current + token
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue

        if current:
            lines.append(current)
            if max_lines and len(lines) >= max_lines:
                lines[-1] = fit_string_to_width(font, lines[-1], max_width)
                return lines
            current = token
        else:
            lines.append(fit_string_to_width(font, token, max_width))
            if max_lines and len(lines) >= max_lines:
                return lines
            current = ""

    if current:
        lines.append(current)

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = fit_string_to_width(font, lines[-1], max_width)

    return lines or [""]


def adaptive_box_width(
    font: pygame.font.Font,
    text: str,
    base_width: int,
    surface_width: int,
    *,
    horizontal_padding: int = 96,
    side_margin: int = 80,
) -> int:
    """Grow a centered box to fit text while staying inside the screen."""
    needed = font.size(text)[0] + horizontal_padding
    max_width = max(120, surface_width - side_margin)
    return min(max(base_width, needed), max_width)


class SceneRenderingUtils:
    """Static methods for common UI rendering patterns used across scenes."""

    @staticmethod
    def draw_glow_text(
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: Tuple[int, int],
        color: Tuple[int, int, int],
        glow_color: Tuple[int, int, int],
        glow_radius: int = 5,
        glow_offset: int = 1,
        alpha_divisor: int = 100,
    ) -> None:
        """Draw text with a layered glow effect beneath it.

        Args:
            surface: Surface to draw on.
            text: Text string to render.
            font: Pygame font object.
            pos: (x, y) center position for the text.
            color: RGB tuple for the main text color.
            glow_color: RGB tuple for the glow layers.
            glow_radius: Number of glow layers (higher = more glow).
            glow_offset: Vertical offset multiplier per layer (i * glow_offset).
            alpha_divisor: Base alpha value divided by layer index (alpha_divisor / i).
        """
        for i in range(glow_radius, 0, -1):
            alpha = int(alpha_divisor / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i * glow_offset))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    @staticmethod
    def draw_option_box(
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        y: int,
        is_selected: bool,
        box_width: int,
        box_height: int,
        option_rects: List[pygame.Rect],
        selected_bg_color: Tuple[int, int, int],
        selected_border_color: Tuple[int, int, int],
        unselected_bg_color: Tuple[int, int, int],
        unselected_border_color: Tuple[int, int, int],
        selected_glow_color: Tuple[int, int, int],
        selected_text_color: Tuple[int, int, int],
        unselected_text_color: Tuple[int, int, int],
        glow_layers: int = 3,
        glow_alpha_divisor: int = 50,
        selected_border_width: int = 3,
        unselected_border_width: int = 2,
        border_radius: int = 12,
    ) -> None:
        """Draw a menu option box with selection highlight.

        Args:
            surface: Surface to draw on.
            text: Option text string.
            font: Pygame font for option text.
            y: Vertical center position of the box.
            is_selected: Whether this option is currently selected.
            box_width: Width of the option box.
            box_height: Height of the option box.
            option_rects: List to append the computed rect to (for mouse hit-testing).
            selected_bg_color: Fill color when selected.
            selected_border_color: Border color when selected.
            unselected_bg_color: Fill color when not selected.
            unselected_border_color: Border color when not selected.
            selected_glow_color: RGB tuple for the glow effect when selected.
            selected_text_color: Text color when selected.
            unselected_text_color: Text color when not selected.
            glow_layers: Number of glow layers around the box when selected.
            glow_alpha_divisor: Alpha divisor for glow layers (alpha = divisor // i).
            selected_border_width: Border thickness when selected.
            unselected_border_width: Border thickness when not selected.
            border_radius: Corner radius for the box.
        """
        box_rect = draw_centered_option_box(
            surface,
            text,
            font,
            y,
            is_selected,
            box_width,
            box_height,
            selected_bg_color,
            selected_border_color,
            unselected_bg_color,
            unselected_border_color,
            selected_glow_color,
            selected_text_color,
            unselected_text_color,
            glow_layers,
            glow_alpha_divisor,
            selected_border_width,
            unselected_border_width,
            border_radius,
        )
        option_rects.append(box_rect)

    @staticmethod
    def draw_decorative_lines(
        surface: pygame.Surface,
        center_x: int,
        top_y: int,
        color: Tuple[int, int, int],
        count: int = 3,
        start_offset_y: int = -100,
        line_increment_y: int = 20,
        line_width: int = 300,
        alpha_base: int = 30,
        alpha_decrement: int = 8,
    ) -> None:
        """Draw decorative horizontal lines beneath a title.

        Args:
            surface: Surface to draw on.
            center_x: Horizontal center for the lines.
            top_y: Vertical reference point (lines are offset from here).
            color: RGB color tuple for the lines (alpha is computed per layer).
            count: Number of lines to draw.
            start_offset_y: Y offset from top_y for the first line.
            line_increment_y: Vertical spacing between lines.
            line_width: Width of each line in pixels.
            alpha_base: Alpha value for the first line.
            alpha_decrement: Alpha subtracted per subsequent line.
        """
        for i in range(count):
            offset_y = start_offset_y + i * line_increment_y
            line_surf = pygame.Surface((line_width, 2), pygame.SRCALPHA)
            line_surf.fill((*color[:3], alpha_base - i * alpha_decrement))
            surface.blit(line_surf, (center_x - line_width // 2, top_y + offset_y))


def draw_themed_title(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    pos: Tuple[int, int],
) -> None:
    """Draw title with military-style layered amber glow effect.

    Renders two layers of glow (wide-dim and tight-bright) beneath the main
    text, using SceneColors.GOLD_DIM and SceneColors.GOLD_PRIMARY.

    Args:
        surface: Surface to draw on.
        text: Text string to render.
        font: Pygame font object.
        pos: (x, y) center position for the text.
    """
    for blur, alpha, color in [
        (4, 20, SceneColors.GOLD_DIM),
        (2, 35, SceneColors.GOLD_PRIMARY),
    ]:
        glow_surf = font.render(text, True, color)
        glow_surf.set_alpha(alpha)
        for offset_x in range(-blur, blur + 1, 2):
            for offset_y in range(-blur, blur + 1, 2):
                if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                    glow_rect = glow_surf.get_rect(
                        center=(pos[0] + offset_x, pos[1] + offset_y)
                    )
                    surface.blit(glow_surf, glow_rect)

    title = font.render(text, True, SceneColors.GOLD_PRIMARY)
    surface.blit(title, title.get_rect(center=pos))


def draw_themed_decorations(
    surface: pygame.Surface,
    width: int,
    height: int,
) -> None:
    """Draw military-style corner bracket decorations around the title area.

    Draws four L-shaped brackets (top-left, top-right, bottom-left,
    bottom-right) centered horizontally at width//2, vertically at height//3.

    Args:
        surface: Surface to draw on.
        width: Screen width in pixels.
        height: Screen height in pixels.
    """
    center_x = width // 2

    bracket_size = 20
    bracket_color = SceneColors.BORDER_DIM

    # Top bracket
    pygame.draw.lines(
        surface,
        bracket_color,
        False,
        [
            (center_x - 100, height // 3 - 50),
            (center_x - 100, height // 3 - 50 - bracket_size),
            (center_x - 100 + bracket_size, height // 3 - 50 - bracket_size),
        ],
        2,
    )
    pygame.draw.lines(
        surface,
        bracket_color,
        False,
        [
            (center_x + 100, height // 3 - 50),
            (center_x + 100, height // 3 - 50 - bracket_size),
            (center_x + 100 - bracket_size, height // 3 - 50 - bracket_size),
        ],
        2,
    )

    # Bottom bracket
    pygame.draw.lines(
        surface,
        bracket_color,
        False,
        [
            (center_x - 100, height // 3 + 50),
            (center_x - 100, height // 3 + 50 + bracket_size),
            (center_x - 100 + bracket_size, height // 3 + 50 + bracket_size),
        ],
        2,
    )
    pygame.draw.lines(
        surface,
        bracket_color,
        False,
        [
            (center_x + 100, height // 3 + 50),
            (center_x + 100, height // 3 + 50 + bracket_size),
            (center_x + 100 - bracket_size, height // 3 + 50 + bracket_size),
        ],
        2,
    )


def draw_themed_option_box(
    surface: pygame.Surface,
    text: str,
    y: int,
    is_selected: bool,
    option_font: pygame.font.Font,
    option_rects: List[pygame.Rect],
    base_box_width: int,
    base_box_height: int,
    scale: float = 1.0,
) -> None:
    """Draw option box with military-style chamfered corners.

    Renders a chamfered-panel option box with an outer glow effect when
    selected. Uses SceneColors for the military color scheme.

    Args:
        surface: Surface to draw on.
        text: Option text string.
        y: Vertical center position of the box.
        is_selected: Whether this option is currently selected.
        option_font: Pygame font for option text.
        option_rects: List to append the computed rect to (for mouse hit-testing).
        base_box_width: Base width of the option box (before scaling).
        base_box_height: Base height of the option box (before scaling).
        scale: Responsive scale factor.
    """
    width, height = surface.get_size()
    center_x = width // 2

    box_width = ResponsiveHelper.scale(base_box_width, scale)
    box_height = ResponsiveHelper.scale(base_box_height, scale)
    arrow = ">> " if is_selected else "   "
    display_text = f"{arrow}{text}"
    box_width = adaptive_box_width(
        option_font,
        display_text,
        box_width,
        width,
        horizontal_padding=96,
    )
    box_rect = pygame.Rect(
        center_x - box_width // 2, y - box_height // 2, box_width, box_height
    )
    option_rects.append(box_rect)

    if is_selected:
        draw_chamfered_panel(
            surface,
            box_rect.x - 4,
            box_rect.y - 4,
            box_rect.width + 8,
            box_rect.height + 8,
            SceneColors.BG_PANEL,
            SceneColors.GOLD_GLOW,
            SceneColors.GOLD_GLOW,
            10,
        )

    draw_chamfered_panel(
        surface,
        box_rect.x,
        box_rect.y,
        box_rect.width,
        box_rect.height,
        SceneColors.BG_PANEL if is_selected else SceneColors.BG_PANEL_LIGHT,
        SceneColors.GOLD_PRIMARY if is_selected else SceneColors.BORDER_DIM,
        None,
        8,
    )

    option_text = fit_text_to_width(
        option_font,
        display_text,
        SceneColors.GOLD_PRIMARY if is_selected else SceneColors.TEXT_DIM,
        box_rect.width - 48,
    )
    text_rect = option_text.get_rect(center=(center_x, y))
    surface.blit(option_text, text_rect)


def render_cached_text(font, text, color, cache_key: str, text_cache: dict):
    """Render text surface, reusing cached surface if text unchanged.

    Args:
        font: Pygame font object.
        text: Text string to render.
        color: RGB color tuple.
        cache_key: Key for the text cache dict.
        text_cache: Dictionary mapping cache_key -> (text, surface).

    Returns:
        pygame.Surface: The rendered text surface (cached or fresh).
    """
    entry = text_cache.get(cache_key)
    if entry is not None and entry[0] == text:
        return entry[1]
    surf = font.render(text, True, color)
    text_cache[cache_key] = (text, surf)
    return surf
