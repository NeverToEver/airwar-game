"""Design tokens — color themes, typography, spacing, and animation values."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

from airwar.utils.fonts import get_cjk_font


class Colors:
    """Base color theme — cold steel palette matching ship armor."""

    BACKGROUND_PRIMARY = (6, 8, 16)
    BACKGROUND_SECONDARY = (10, 12, 22)
    BACKGROUND_PANEL = (8, 10, 18)
    BACKGROUND_OVERLAY = (0, 0, 0, 200)

    ACCENT_PRIMARY = (140, 170, 210)
    ACCENT_BRIGHT = (170, 195, 230)
    ACCENT_WARM = (180, 150, 120)
    ACCENT_WARM_DEEP = (140, 110, 80)

    # Legacy aliases
    HUD_AMBER = ACCENT_PRIMARY
    HUD_AMBER_BRIGHT = ACCENT_BRIGHT
    HUD_ORANGE = ACCENT_WARM
    HUD_ORANGE_DEEP = ACCENT_WARM_DEEP

    ACCENT_EXPLOSIVE = (255, 100, 50)
    ACCENT_DANGER = (255, 50, 50)

    PARTICLE_PRIMARY = (120, 150, 200)
    PARTICLE_ALT = (140, 120, 180)

    TEXT_PRIMARY = (210, 215, 230)
    TEXT_SECONDARY = (175, 180, 200)
    TEXT_MUTED = (130, 140, 160)
    TEXT_HINT = (100, 110, 135)

    HEALTH_NORMAL = (170, 180, 110)
    HEALTH_DANGER = (220, 70, 55)
    SCORE_COLOR = (210, 215, 230)
    PROGRESS_COLOR = (140, 170, 210)
    KILLS_COLOR = (170, 175, 200)
    BOSS_COLOR = (210, 90, 70)

    BUTTON_SELECTED_BG = (30, 38, 55)
    BUTTON_UNSELECTED_BG = (18, 24, 38)
    PANEL_BORDER = (120, 140, 170)

    BUTTON_SELECTED_PRIMARY = (160, 185, 220)
    BUTTON_SELECTED_GLOW = (140, 170, 210)
    BUTTON_SELECTED_TEXT = (230, 235, 245)

    BUTTON_UNSELECTED_PRIMARY = (120, 140, 170)
    BUTTON_UNSELECTED_GLOW = (140, 155, 180)
    BUTTON_UNSELECTED_TEXT = (170, 175, 195)

    DANGER_BUTTON_SELECTED_PRIMARY = (220, 85, 55)
    DANGER_BUTTON_SELECTED_GLOW = (230, 110, 85)
    DANGER_BUTTON_UNSELECTED_PRIMARY = (150, 50, 35)
    DANGER_BUTTON_UNSELECTED_GLOW = (180, 70, 50)

    BOSS_HEALTH_HIGH = (210, 120, 55)
    BOSS_HEALTH_MED = (220, 90, 55)
    BOSS_HEALTH_LOW = (220, 70, 55)

    WARNING = (210, 90, 70)
    SUCCESS = (140, 180, 110)
    INFO = (140, 170, 210)

    @staticmethod
    def star_color(brightness: int) -> tuple[int, int, int]:
        return (brightness + 50, brightness + 50, brightness + 70)


class Typography:
    """Typography — font sizes for all UI text elements."""

    DISPLAY_SIZE = 110
    TITLE_SIZE = 100
    HEADING_SIZE = 72
    SUBHEADING_SIZE = 48
    BODY_SIZE = 36
    OPTION_SIZE = 44
    CAPTION_SIZE = 32
    HUD_SIZE = 26
    SMALL_SIZE = 24
    TINY_SIZE = 20

    FONT_FAMILY_DEFAULT = None


class Spacing:
    """Spacing — margin, padding, and layout spacing values."""

    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 20
    SPACE_2XL = 24
    SPACE_3XL = 32
    SPACE_4XL = 40
    SPACE_5XL = 48

    BORDER_RADIUS_SM = 4
    BORDER_RADIUS_MD = 8
    BORDER_RADIUS_LG = 12
    BORDER_RADIUS_XL = 15
    BORDER_RADIUS_2XL = 18

    PANEL_WIDTH = 400
    PANEL_HEIGHT = 460
    OPTION_HEIGHT = 70
    OPTION_GAP = 12
    BOX_WIDTH = 350
    BOX_HEIGHT = 60


class Animation:
    """Animation — timing and easing values."""

    GLOW_SPEED = 0.08
    GLOW_RADIUS_DEFAULT = 4
    GLOW_RADIUS_TITLE = 6
    GLOW_RADIUS_BUTTON = 5

    HOVER_SCALE_FACTOR = 0.18
    CLICK_SCALE_FACTOR = 0.10
    CLICK_DECAY_FACTOR = 0.82

    BLINK_INTERVAL = 25
    TWINKLE_SPEED_MIN = 0.05
    TWINKLE_SPEED_MAX = 0.12

    PARTICLE_SPEED_MIN = 0.4
    PARTICLE_SPEED_MAX = 1.0
    STAR_SPEED = 0.01

    NEBULA_COUNT = 5
    NEBULA_RADIUS_MIN = 150
    NEBULA_RADIUS_MAX = 350
    NEBULA_ALPHA_MIN = 15
    NEBULA_ALPHA_MAX = 35
    NEBULA_DRIFT_X_RANGE = 0.0002
    NEBULA_DRIFT_Y_RANGE = 0.0001


class UIComponents:
    """UI components — dimensions for standard UI elements."""

    BUTTON_WIDTH = 280
    BUTTON_HEIGHT = 60
    TITLE_Y = 100
    HINT_Y_OFFSET = 70
    CONTROLS_Y_OFFSET = 45

    HEALTH_BAR_WIDTH = 400
    HEALTH_BAR_HEIGHT = 28

    PROGRESS_BAR_WIDTH = 300
    PROGRESS_BAR_HEIGHT = 20

    STAR_COUNT = 120
    PARTICLE_COUNT = 45
    PARTICLE_PARTICLE_ALT_COUNT = 30

    BUFF_PANEL_WIDTH = 180
    BUFF_PANEL_HEIGHT = 36

    HUD_PANEL_WIDTH = 220
    HUD_PANEL_PADDING = 15
    HUD_PANEL_GAP = 8
    HUD_PANEL_MODULE_HEIGHT = 55
    HUD_PANEL_CORNER_RADIUS = 10
    HUD_PANEL_COLLAPSED_RATIO = 0.4

    HUD_LABEL_FONT_SIZE = 22
    HUD_VALUE_FONT_SIZE = 32
    HUD_BUFF_FONT_SIZE = 20
    HUD_MORE_FONT_SIZE = 18
    HUD_EXPAND_ARROW_SIZE = 18
    HUD_EXPAND_HINT_SIZE = 14

    HUD_PROGRESS_BAR_HEIGHT = 12
    HUD_HEALTH_BAR_HEIGHT = 16
    HUD_COEFFICIENT_BAR_HEIGHT = 12

    COEFFICIENT_MAX_MULTIPLIER = 8.0

    BUFF_CONTRAST_THRESHOLD_HIGH = 180
    BUFF_CONTRAST_THRESHOLD_MED = 120
    BUFF_TEXT_DARK = (40, 30, 20)
    BUFF_TEXT_LIGHT = (255, 245, 235)
    BUFF_HIGH_CONTRAST_COLORS = [
        (255, 200, 150),
        (255, 220, 200),
        (220, 255, 220),
        (255, 255, 220),
    ]

    BUFF_SCROLL_SPEED = 0.02
    BUFF_SCROLL_VISIBLE_COUNT = 6


# ─── System (HUD / in-game) theme ────────────────────────────────────────


class SystemColors:
    """System color palette — in-game HUD and overlay elements."""

    ACCENT_PRIMARY = (140, 170, 210)
    ACCENT_DIM = (110, 140, 175)
    ACCENT_BRIGHT = (170, 195, 230)
    ACCENT_GLOW = (140, 170, 210, 80)

    ACCENT_TEAL = (80, 140, 180)
    ACCENT_TEAL_DIM = (60, 110, 145)

    BG_PRIMARY = (8, 10, 16)
    BG_PANEL = (14, 17, 24)
    BG_PANEL_LIGHT = (20, 24, 33)

    BORDER_GLOW = (140, 170, 210, 80)
    BORDER_DIM = (100, 120, 150)
    GRID_LINE = (140, 170, 210, 20)

    DANGER_RED = (220, 65, 60)
    DANGER_RED_DIM = (160, 45, 45)
    WARNING_ACCENT = (190, 150, 85)

    TEXT_PRIMARY = (215, 220, 235)
    TEXT_DIM = (135, 142, 160)
    TEXT_BRIGHT = (235, 240, 250)

    HEALTH_FULL = (90, 200, 115)
    HEALTH_MEDIUM = (185, 170, 100)
    HEALTH_LOW = (220, 65, 60)
    HEALTH_CRITICAL = (230, 45, 45)

    BOSS_BAR_FULL = (200, 120, 60)
    BOSS_BAR_EMPTY = (30, 28, 35)

    SEGMENT_FILL = (140, 170, 210)
    SEGMENT_EMPTY = (22, 25, 33)
    SEGMENT_BORDER = (75, 85, 105)

    ICON_POWER = (220, 190, 90)
    ICON_DEFENSE = (100, 190, 210)
    ICON_SPEED = (120, 180, 240)
    ICON_LASER = (210, 120, 190)
    ICON_MISSILE = (210, 140, 100)

    STATS_TEXT = (200, 205, 220)
    STATS_TEXT_BRIGHT = (225, 230, 245)
    STATS_TEXT_DIM = (145, 150, 170)

    GIVE_UP_BG = (35, 10, 12)

    COEFFICIENT_EASY = (90, 210, 110)
    COEFFICIENT_MEDIUM = (200, 190, 100)
    COEFFICIENT_HARD = (220, 140, 50)
    COEFFICIENT_BAR_BG = (30, 35, 55)
    COEFFICIENT_BAR_FILL = (16, 18, 32)

    PANEL_OVERLAY_DARK = (20, 25, 45)
    PANEL_OVERLAY_LIGHT = (14, 17, 32)


class SystemUI:
    """System UI component sizing and styling constants."""

    CHAMFER_DEPTH = 12
    CHAMFER_BORDER_WIDTH = 2
    CHAMFER_GLOW_WIDTH = 1
    CHAMFER_CORNER_RADIUS = 0

    GRID_ALPHA = 10
    GRID_SPACING = 40

    HEXAGON_SIZE = 24
    HEXAGON_BORDER_WIDTH = 2

    PANEL_PADDING = 15
    PANEL_MARGIN = 10
    PANEL_CORNER_CHAMFER = 12

    SEGMENT_GAP = 2
    SEGMENT_MIN_WIDTH = 8

    PULSE_FAST = 15
    PULSE_NORMAL = 30
    PULSE_SLOW = 60
    FLASH_DURATION = 10

    SCANLINE_ALPHA = 25
    SCANLINE_SPACING = 4

    HUD_LABEL_SIZE = 18
    HUD_VALUE_SIZE = 24
    HUD_TITLE_SIZE = 36
    HUD_SMALL_SIZE = 14


# ─── Scene (menu / pause / login) theme ──────────────────────────────────


class SceneColors:
    """Scene color palette — menus, pause, login, and overlay screens."""

    ACCENT_PRIMARY = (140, 170, 210)
    ACCENT_DIM = (110, 140, 175)
    ACCENT_BRIGHT = (170, 195, 230)
    ACCENT_GLOW = (140, 170, 210, 60)

    ACCENT_TEAL = (80, 130, 170)
    ACCENT_TEAL_DIM = (60, 100, 140)
    ACCENT_TEAL_BRIGHT = (100, 155, 195)

    BG_PRIMARY = (6, 8, 14)
    BG_PANEL = (12, 15, 22)
    BG_PANEL_LIGHT = (18, 22, 30)

    BORDER_GLOW = (140, 170, 210, 60)
    BORDER_DIM = (90, 110, 135)
    BORDER_TEAL = (80, 130, 170, 70)

    MARQUEE_COLOR = (140, 170, 210, 35)
    MARQUEE_STRIP_SIZE = 24
    MARQUEE_SPEED = 0.4

    DANGER_RED = (180, 55, 48)
    DANGER_RED_DIM = (120, 38, 32)
    WARNING_ACCENT = (185, 145, 80)

    TEXT_PRIMARY = (210, 215, 230)
    TEXT_DIM = (130, 140, 160)
    TEXT_BRIGHT = (230, 235, 245)

    HEALTH_FULL = (85, 190, 110)
    HEALTH_MEDIUM = (185, 165, 100)
    HEALTH_LOW = (200, 75, 55)
    HEALTH_CRITICAL = (210, 55, 48)

    BOSS_BAR_FULL = (190, 110, 60)
    BOSS_BAR_EMPTY = (28, 27, 30)

    SEGMENT_FILL = (140, 170, 210)
    SEGMENT_EMPTY = (20, 23, 30)
    SEGMENT_BORDER = (75, 90, 110)

    ICON_POWER = (220, 190, 90)
    ICON_DEFENSE = (100, 190, 210)
    ICON_SPEED = (120, 180, 240)
    ICON_LASER = (210, 120, 190)
    ICON_MISSILE = (210, 140, 100)

    INPUT_BG = (16, 20, 36)
    INPUT_ACTIVE = (24, 30, 52)
    INPUT_TEXT = (210, 215, 230)
    INPUT_PLACEHOLDER = (75, 85, 110)

    BUTTON_LOGIN = (25, 55, 105)
    BUTTON_REGISTER = (45, 75, 115)
    BUTTON_QUIT = (170, 50, 38)
    BUTTON_FULLSCREEN = (28, 55, 95)
    BUTTON_TEXT = (235, 240, 250)

    HINT_DIM = (70, 80, 110)
    HINT_BRIGHT = (100, 110, 150)

    TITLE_GLOW_INNER = (120, 180, 230)
    TITLE_GLOW_MIDDLE = (80, 150, 210)
    TITLE_GLOW_OUTER = (50, 110, 170)
    TITLE_SHADOW = (18, 45, 85)

    PARTICLE_COLOR = (140, 170, 210)

    PANEL_OVERLAY_DARK = (18, 25, 50)
    PANEL_OVERLAY_LIGHT = (14, 17, 35)

    BACK_BUTTON = (200, 100, 90)
    DESC_TEXT = (60, 65, 90)

    STATS_TEXT = (200, 205, 220)
    STATS_TEXT_BRIGHT = (225, 230, 245)
    STATS_TEXT_DIM = (145, 150, 170)

    GIVE_UP_BG = (35, 10, 12)

    COEFFICIENT_EASY = (90, 210, 110)
    COEFFICIENT_MEDIUM = (200, 190, 100)
    COEFFICIENT_HARD = (220, 140, 50)
    COEFFICIENT_BAR_BG = (30, 35, 55)
    COEFFICIENT_BAR_FILL = (16, 18, 32)


# ─── Backward-compatible aliases ──────────────────────────────────────────

MilitaryColors = SystemColors
MilitaryUI = SystemUI
ForestColors = SceneColors

# Legacy constant aliases on SystemColors
SystemColors.AMBER_PRIMARY = SystemColors.ACCENT_PRIMARY  # type: ignore[attr-defined]
SystemColors.AMBER_DIM = SystemColors.ACCENT_DIM  # type: ignore[attr-defined]
SystemColors.AMBER_BRIGHT = SystemColors.ACCENT_BRIGHT  # type: ignore[attr-defined]
SystemColors.AMBER_GLOW = SystemColors.ACCENT_GLOW  # type: ignore[attr-defined]
SystemColors.MILITARY_GREEN = SystemColors.ACCENT_TEAL  # type: ignore[attr-defined]
SystemColors.MILITARY_GREEN_DIM = SystemColors.ACCENT_TEAL_DIM  # type: ignore[attr-defined]
SystemColors.WARNING_AMBER = SystemColors.WARNING_ACCENT  # type: ignore[attr-defined]
SystemColors.MILITARY_LABEL_SIZE = SystemUI.HUD_LABEL_SIZE  # type: ignore[attr-defined]
SystemColors.MILITARY_VALUE_SIZE = SystemUI.HUD_VALUE_SIZE  # type: ignore[attr-defined]
SystemColors.MILITARY_TITLE_SIZE = SystemUI.HUD_TITLE_SIZE  # type: ignore[attr-defined]
SystemColors.MILITARY_SMALL_SIZE = SystemUI.HUD_SMALL_SIZE  # type: ignore[attr-defined]

# Legacy constant aliases on SceneColors
SceneColors.GOLD_PRIMARY = SceneColors.ACCENT_PRIMARY  # type: ignore[attr-defined]
SceneColors.GOLD_DIM = SceneColors.ACCENT_DIM  # type: ignore[attr-defined]
SceneColors.GOLD_BRIGHT = SceneColors.ACCENT_BRIGHT  # type: ignore[attr-defined]
SceneColors.GOLD_GLOW = SceneColors.ACCENT_GLOW  # type: ignore[attr-defined]
SceneColors.FOREST_GREEN = SceneColors.ACCENT_TEAL  # type: ignore[attr-defined]
SceneColors.FOREST_GREEN_DIM = SceneColors.ACCENT_TEAL_DIM  # type: ignore[attr-defined]
SceneColors.FOREST_GREEN_BRIGHT = SceneColors.ACCENT_TEAL_BRIGHT  # type: ignore[attr-defined]
SceneColors.BORDER_FOREST = SceneColors.BORDER_TEAL  # type: ignore[attr-defined]
SceneColors.WARNING_AMBER = SceneColors.WARNING_ACCENT  # type: ignore[attr-defined]

# Legacy constant aliases on SystemUI
SystemUI.MILITARY_LABEL_SIZE = SystemUI.HUD_LABEL_SIZE  # type: ignore[attr-defined]
SystemUI.MILITARY_VALUE_SIZE = SystemUI.HUD_VALUE_SIZE  # type: ignore[attr-defined]
SystemUI.MILITARY_TITLE_SIZE = SystemUI.HUD_TITLE_SIZE  # type: ignore[attr-defined]
SystemUI.MILITARY_SMALL_SIZE = SystemUI.HUD_SMALL_SIZE  # type: ignore[attr-defined]


# ─── Layout: Anchors & standard position tokens ──────────────────────────
# These tokens replace hardcoded screen arithmetic such as
#     surface.get_width() // 2, height - 50, (108, screen_h - 98)
# with semantically named helpers that survive window resize and DPI changes.
#
# Usage:
#     from airwar.config.design_tokens import Anchors, SystemLayout
#     cx, cy = Anchors.center(surface.get_width(), surface.get_height())
#     y      = surface.get_height() - SystemLayout.BOTTOM_HINT_OFFSET
#     rect   = pygame.Rect(*Anchors.bottom_left(w, h, dx=PANEL_LEFT_INSET, dy=98), w, h)


class Anchors:
    """Screen-relative anchor helpers — pure functions over (width, height)."""

    @staticmethod
    def center(width: int, height: int) -> tuple[int, int]:
        """Return the centre of a (width, height) rectangle."""
        return (width // 2, height // 2)

    @staticmethod
    def center_x(width: int) -> int:
        return width // 2

    @staticmethod
    def center_y(height: int) -> int:
        return height // 2

    @staticmethod
    def top_center(width: int, dy: int = 0) -> tuple[int, int]:
        return (width // 2, dy)

    @staticmethod
    def top_left(width: int, height: int, dx: int = 0, dy: int = 0) -> tuple[int, int]:
        return (dx, dy)

    @staticmethod
    def top_right(width: int, height: int, dx: int = 0, dy: int = 0) -> tuple[int, int]:
        return (width - dx, dy)

    @staticmethod
    def bottom_center(width: int, height: int, dy: int = 0) -> tuple[int, int]:
        return (width // 2, height - dy)

    @staticmethod
    def bottom_left(width: int, height: int, dx: int = 0, dy: int = 0) -> tuple[int, int]:
        return (dx, height - dy)

    @staticmethod
    def bottom_right(width: int, height: int, dx: int = 0, dy: int = 0) -> tuple[int, int]:
        return (width - dx, height - dy)


class SystemLayout:
    """In-game HUD layout — positions and insets for game-scene overlays."""

    # Generic panel insets
    PANEL_LEFT_INSET = 15
    PANEL_RIGHT_INSET = 15
    PANEL_TOP_INSET = 95
    PANEL_MIN_Y = 50
    PANEL_MIN_WIDTH = 170
    PANEL_MAX_INSET_TOTAL = 140

    # Boost gauge (bottom-left arc)
    BOOST_GAUGE_BOTTOM_PAD = 98
    BOOST_GAUGE_LEFT_INSET = 15
    BOOST_GAUGE_CENTER_X = 108  # legacy: prefer BOOST_GAUGE_LEFT_INSET

    # Bottom hint offsets (from screen bottom)
    BOTTOM_HINT_OFFSET = 100
    BOTTOM_CONTROLS_OFFSET = 70
    BOTTOM_ESC_OFFSET = 50

    # Homecoming progress bar
    HOMECOMING_BAR_Y = 92
    HOMECOMING_BAR_W = 310
    HOMECOMING_BAR_H = 14
    HOMECOMING_LABEL_OFFSET = 31
    HOMECOMING_HINT_OFFSET = 28
    HOMECOMING_BAR_INSET_X = 4
    HOMECOMING_BAR_INSET_Y = 4

    # Give-up bar
    GIVE_UP_BAR_Y = 60
    GIVE_UP_BAR_W = 250
    GIVE_UP_BAR_H = 16
    GIVE_UP_BAR_INSET = 4

    # Buff stats panel (left side)
    BUFF_PANEL_TOP_PAD = 10
    BUFF_PANEL_DIVIDER_Y = 30
    BUFF_PANEL_LIST_TOP = 40
    BUFF_PANEL_ROW_H = 32
    BUFF_PANEL_DIVIDER_PAD_X = 10
    BUFF_PANEL_VALUE_INSET_X = 10
    BUFF_PANEL_VALUE_TOP_PAD = 2

    # Pause button (game over screen)
    PAUSE_BTN_LEFT = 15
    PAUSE_BTN_TOP = 95
    PAUSE_BTN_TITLE_TOP = 6
    PAUSE_BTN_INNER_PAD_X = 12
    PAUSE_BTN_HEX_CENTER_Y = 46

    # Boss warn / entity rendering
    BOSS_WARN_Y_TOP = 20
    BOSS_WARN_Y_HIGH = 50
    BOSS_WARN_Y_LOW = 86


class SceneLayout:
    """Menu/pause/settings/login scene layout — positions and insets."""

    PANEL_TOP = 110
    BACK_BUTTON_BOTTOM_OFFSET = 130
    BOTTOM_HINT_OFFSET = 50
    BOTTOM_HINT_OFFSET_ALT = 40
    BOTTOM_MESSAGE_OFFSET = 75
    BOTTOM_ESC_OFFSET = 50
    FULLSCREEN_BTN_INSET = 30
    FULLSCREEN_BTN_W = 160
    FULLSCREEN_BTN_H = 38
    MSG_Y = 88
    BOTTOM_HINT_Y_OFFSET = 60

    # Death scene midline offsets (added to height // 2)
    DEATH_SCORE_OFFSET = 45
    DEATH_KILLS_OFFSET = 5
    DEATH_BOSS_OFFSET = 40
    DEATH_OPTIONS_OFFSET = 100
    DEATH_BOTTOM_HINT_OFFSET = 100
    DEATH_BOTTOM_CONTROLS_OFFSET = 70

    # Exit confirm
    EXIT_INDICATOR_OFFSET = 50
    EXIT_OPTIONS_OFFSET = 30
    EXIT_HINT_OFFSET = 120
    EXIT_CONTROLS_OFFSET = 80
    EXIT_ESC_OFFSET = 50

    # Pause scene
    PAUSE_OPTIONS_OFFSET = 20
    PAUSE_HINT_OFFSET = 120
    PAUSE_CONTROLS_OFFSET = 80
    PAUSE_ESC_OFFSET = 50

    # Welcome scene
    WELCOME_BOTTOM_HINT_OFFSET = 40
    WELCOME_BOTTOM_HINT_OFFSET_ALT = 75

    # Leaderboard
    LEADERBOARD_TITLE_TOP = 50
    LEADERBOARD_SEPARATOR_Y = 96
    LEADERBOARD_FOOTER_BOTTOM_PAD = 30

    # Welcome sub-panels
    PANEL_TITLE_TOP_PAD = 32
    PANEL_SEPARATOR_Y = 58
    PANEL_TUTORIAL_Y = 80
    PANEL_DIFF_LIST_TOP_PAD = 26
    PANEL_BUTTON_BOTTOM_PAD = 12
    PANEL_TIPS_TITLE_GAP = 18
    PANEL_TIPS_ROW_GAP = 26
    PANEL_TUTORIAL_CTA_TEXT_INSET = 112


class Modals:
    """Modal dialog dimensions — used by welcome, exit, confirm, etc."""

    # Guest confirm
    GUEST_CONFIRM_W = 560
    GUEST_CONFIRM_H = 300

    # Delete confirm
    DELETE_CONFIRM_W = 620
    DELETE_CONFIRM_H = 280

    # Shared
    TITLE_TOP_PAD = 50
    BODY_TOP_PAD = 112
    BODY_INSET_X = 80
    BUTTON_W = 190
    BUTTON_H = 46
    BUTTON_BOTTOM_PAD = 70
    BUTTON_GAP = 20
    DIM_ALPHA = 160


class ButtonInset:
    """Button/input/control inner padding values."""

    INSET_X = 32          # standard button text inset from edges
    INSET_X_SMALL = 28    # smaller button text inset
    INSET_Y = 16
    HOVER_OUTSET = 4
    HOVER_OUTSET_X2 = 8   # 2 * HOVER_OUTSET
    FOCUS_OUTSET = 3
    FOCUS_OUTSET_X2 = 6
    TRAIL_PAD = 6         # text right-trailing pad inside input

    # Input field
    INPUT_TEXT_PAD_X = 16
    INPUT_FOCUS_OUTSET = 3
    INPUT_FOCUS_OUTSET_X2 = 6

    # Dropdown
    DROPDOWN_ITEM_INSET = 4
    DROPDOWN_ITEM_INSET_X2 = 8
    DROPDOWN_TEXT_INSET_X = 24
    DROPDOWN_TEXT_PAD_X = 12
    CURSOR_VERTICAL_PAD = 12
    CURSOR_PAD = 3

    # Welcome scene
    WELCOME_TUTORIAL_INNER_INSET = 112


class GameOverLayout:
    """Game over screen layout — scaled reference dimensions (BASE_REF_WIDTH)."""

    BASE_REF_WIDTH = 800
    BASE_BTN_LABEL_W = 280
    BUTTON_SIDE_MARGIN = 120
    BUTTON_BASE_H = 60
    MENU_BTN_Y = 480
    QUIT_BTN_Y = 560
    TITLE_Y = 150
    SCORE_Y = 280
    KILLS_Y = 330
    HS_Y = 400
    BUTTON_TEXT_PAD = 48

    # Difficulty coefficient panel
    DIFF_PANEL_LABEL_TOP = 18
    DIFF_PANEL_VALUE_TOP = 45
    DIFF_PANEL_DELTA_TOP = 68

    # Hangar panel
    HANGAR_REF_W = 420


class TutorialLayout:
    """Tutorial scene layout — stage card and renderer positions."""

    BADGE_NUM_OFFSET_Y = 12
    COUNTER_LABEL_TOP_PAD = 5
    COUNTER_LABEL_BOTTOM_PAD = 4

    SUMMARY_TITLE_Y = 54
    SUMMARY_PROGRESS_Y = 98
    SUMMARY_LIST_TOP = 142
    SUMMARY_LIST_INDENT_X = 72
    SUMMARY_LIST_ROW_H = 36
    SUMMARY_WRAP_INSET_X = 112
    SUMMARY_WRAP_INDENT = 56
    SUMMARY_WRAP_LINE_H = 26
    SUMMARY_BUTTON_W = 240
    SUMMARY_BUTTON_H = 48
    SUMMARY_BUTTON_BOTTOM_PAD = 74

    CARD_STAGE_Y = 34
    CARD_TITLE_Y = 76
    HINT_TEXT_Y = 250


class RewardLayout:
    """Reward selector card layout — box text and desc insets."""

    BOX_TEXT_INSET_X = 50
    BOX_DESC_INSET_X = 70
    BOTTOM_CENTER_DY = 50


class LeaderboardLayout:
    """Leaderboard view layout."""

    TITLE_TOP = 50
    SEPARATOR_Y = 96
    FOOTER_BOTTOM_PAD = 30


class SegmentedBarLayout:
    """Segmented bar (health/difficulty) layout — label/bar insets."""

    LABEL_INSET = 24
    BAR_VPAD = 8
    BAR_PADDING = 16
    SEG_VERTICAL_INSET_TOP = 4
    SEG_VERTICAL_INSET_BOTTOM = 16
    LABEL_TRAIL_PAD = 10


class HangarSilhouette:
    """Hangar panel ship silhouette — scaled offsets (multiplied by `scale`)."""

    @staticmethod
    def scaled(value: float, scale: float) -> int:
        return int(value * scale)

    WING_TIP_X = 62
    WING_TIP_Y = 34
    WING_INSET_X = 13
    WING_INSET_Y = 18
    WING_INNER_X = 8
    COCKPIT_OFFSET_Y = 38
    ENGINE_OFFSET_Y = 58



# ─── DesignTokens singleton ───────────────────────────────────────────────


class DesignTokens:
    """Design tokens singleton — centralized visual design system."""

    def __init__(self) -> None:
        self.colors: type[Colors] = Colors
        self.typography: type[Typography] = Typography
        self.spacing: type[Spacing] = Spacing
        self.animation: type[Animation] = Animation
        self.components: type[UIComponents] = UIComponents
        self.system: type[SystemColors] = SystemColors
        self.system_ui: type[SystemUI] = SystemUI
        self.scene: type[SceneColors] = SceneColors
        # Layout tokens (added 2026-06-09 — see STRUCTURE.md)
        self.anchors: type[Anchors] = Anchors
        self.system_layout: type[SystemLayout] = SystemLayout
        self.scene_layout: type[SceneLayout] = SceneLayout
        self.modals: type[Modals] = Modals
        self.button_inset: type[ButtonInset] = ButtonInset
        self.game_over_layout: type[GameOverLayout] = GameOverLayout
        self.tutorial_layout: type[TutorialLayout] = TutorialLayout
        self.reward_layout: type[RewardLayout] = RewardLayout
        self.leaderboard_layout: type[LeaderboardLayout] = LeaderboardLayout
        self.segmented_bar_layout: type[SegmentedBarLayout] = SegmentedBarLayout
        self.hangar_silhouette: type[HangarSilhouette] = HangarSilhouette
        # Backward-compatible aliases
        self.military: type[SystemColors] = SystemColors
        self.military_ui: type[SystemUI] = SystemUI
        self.forest: type[SceneColors] = SceneColors

    def get_font(self, size: int) -> pygame.font.Font:
        return get_cjk_font(size)

    def get_scaled_font(self, base_size: int, scale: float) -> pygame.font.Font:
        return get_cjk_font(int(base_size * scale))


_tokens_instance: DesignTokens | None = None


def get_design_tokens() -> DesignTokens:
    global _tokens_instance
    if _tokens_instance is None:
        _tokens_instance = DesignTokens()
    return _tokens_instance


def get_colors() -> type[Colors]:
    return Colors
