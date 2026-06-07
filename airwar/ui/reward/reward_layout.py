"""Reward panel layout — panel positioning and option card sizing."""

import pygame

# Option card geometry constants (preserved from original RewardSelector).
OPTION_HEIGHT = 84
OPTION_GAP = 14
OPTION_SECTION_HEIGHT = OPTION_HEIGHT * 3 + OPTION_GAP * 2
PANEL_HEIGHT = 340
NON_THEMED_BOX_WIDTH = 480
THEMED_BOX_WIDTH = 500
MAX_OPTION_BOX_WIDTH_FLOOR = 360
MAX_OPTION_BOX_PADDING = 160
BOX_WIDTH_PADDING = 70
PANEL_PADDING = 40
PANEL_MIN_WIDTH = 540
PANEL_MIN_WIDTH_FLOOR = 400
PANEL_SIDE_MARGIN = 120


class RewardLayout:
    """Compute panel and option card positions for the reward selector.

    The original god class embedded these calculations as private methods
    (``_calculate_option_box_width``, ``_calculate_panel_width``) plus
    inline ``box_width = ...; center_x = ...; panel_y = ...`` math inside
    ``render``. This component centralizes the math so the renderer and
    orchestrator share a single source of truth.
    """

    @staticmethod
    def calculate_option_box_width(
        surface: pygame.Surface,
        options: list[dict],
        use_themed_style: bool,
        option_font: pygame.font.Font,
        hint_font: pygame.font.Font,
        buff_levels: dict,
        unlocked_buffs: list,
    ) -> int:
        """Return the widest sensible option box width.

        Args:
            surface: Target surface (used for clamping).
            options: Reward options being displayed.
            use_themed_style: Whether the themed (chamfered) style is active.
            option_font: Font used to render the option name.
            hint_font: Font used to render the option description.
            buff_levels: Mapping of buff name to current level.
            unlocked_buffs: List of buff names already unlocked.
        """
        max_width = max(MAX_OPTION_BOX_WIDTH_FLOOR, surface.get_width() - MAX_OPTION_BOX_PADDING)
        box_width = THEMED_BOX_WIDTH if use_themed_style else NON_THEMED_BOX_WIDTH
        for option in options:
            buff_name = option.get("name", "")
            level = buff_levels.get(buff_name, 0)
            is_upgraded = buff_name in unlocked_buffs and level > 0
            name_text = f"> {buff_name} [Lv.{level}]" if is_upgraded else f"> {buff_name}"
            desc_text = option.get("desc", "")
            box_width = max(
                box_width,
                option_font.size(name_text)[0] + BOX_WIDTH_PADDING,
                min(hint_font.size(desc_text)[0] + BOX_WIDTH_PADDING, max_width),
            )
        return min(box_width, max_width)

    @staticmethod
    def calculate_panel_width(surface: pygame.Surface, box_width: int) -> int:
        """Return the outer panel width, clamped to the screen.

        Args:
            surface: Target surface (used for clamping).
            box_width: Inner option box width.
        """
        return min(
            max(box_width + PANEL_PADDING, PANEL_MIN_WIDTH),
            max(PANEL_MIN_WIDTH_FLOOR, surface.get_width() - PANEL_SIDE_MARGIN),
        )

    @staticmethod
    def panel_position(surface: pygame.Surface, glow_offset: float) -> tuple[int, int, int, int]:
        """Return (panel_x, panel_y, panel_width, panel_height) for the main panel.

        Args:
            surface: Target surface.
            glow_offset: Animated vertical glow offset.
        """
        width, height = surface.get_size()
        panel_width = NON_THEMED_BOX_WIDTH
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - PANEL_HEIGHT // 2 + glow_offset * 0.3
        return panel_x, panel_y, panel_width, PANEL_HEIGHT

    @staticmethod
    def option_section_anchor(surface: pygame.Surface, glow_offset: float) -> tuple[int, int, int]:
        """Return (center_x, panel_y, start_y) for option rendering.

        ``center_x`` is the screen-horizontal center; ``panel_y`` matches
        ``panel_position``; ``start_y`` is the y-coordinate of the first
        option card.

        Args:
            surface: Target surface.
            glow_offset: Animated vertical glow offset.
        """
        width, height = surface.get_size()
        center_x = width // 2
        panel_y = height // 2 - PANEL_HEIGHT // 2 + glow_offset * 0.3
        start_y = panel_y + (PANEL_HEIGHT - OPTION_SECTION_HEIGHT) // 2 + 10
        return center_x, panel_y, start_y

    @staticmethod
    def option_rect(
        center_x: int,
        start_y: int,
        index: int,
        box_width: int,
    ) -> pygame.Rect:
        """Compute the pygame.Rect for one option card.

        Args:
            center_x: Horizontal center of the option card.
            start_y: y-coordinate of the first card.
            index: Option index (0-based).
            box_width: Card width.
        """
        y = start_y + index * (OPTION_HEIGHT + OPTION_GAP)
        return pygame.Rect(center_x - box_width // 2, y, box_width, OPTION_HEIGHT)
