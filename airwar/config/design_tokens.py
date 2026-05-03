"""Design tokens — color themes, typography, spacing, and animation values."""
from typing import Tuple
import pygame


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
    def star_color(brightness: int) -> Tuple[int, int, int]:
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
SystemColors.AMBER_PRIMARY = SystemColors.ACCENT_PRIMARY
SystemColors.AMBER_DIM = SystemColors.ACCENT_DIM
SystemColors.AMBER_BRIGHT = SystemColors.ACCENT_BRIGHT
SystemColors.AMBER_GLOW = SystemColors.ACCENT_GLOW
SystemColors.MILITARY_GREEN = SystemColors.ACCENT_TEAL
SystemColors.MILITARY_GREEN_DIM = SystemColors.ACCENT_TEAL_DIM
SystemColors.WARNING_AMBER = SystemColors.WARNING_ACCENT
SystemColors.MILITARY_LABEL_SIZE = SystemUI.HUD_LABEL_SIZE
SystemColors.MILITARY_VALUE_SIZE = SystemUI.HUD_VALUE_SIZE
SystemColors.MILITARY_TITLE_SIZE = SystemUI.HUD_TITLE_SIZE
SystemColors.MILITARY_SMALL_SIZE = SystemUI.HUD_SMALL_SIZE

# Legacy constant aliases on SceneColors
SceneColors.GOLD_PRIMARY = SceneColors.ACCENT_PRIMARY
SceneColors.GOLD_DIM = SceneColors.ACCENT_DIM
SceneColors.GOLD_BRIGHT = SceneColors.ACCENT_BRIGHT
SceneColors.GOLD_GLOW = SceneColors.ACCENT_GLOW
SceneColors.FOREST_GREEN = SceneColors.ACCENT_TEAL
SceneColors.FOREST_GREEN_DIM = SceneColors.ACCENT_TEAL_DIM
SceneColors.FOREST_GREEN_BRIGHT = SceneColors.ACCENT_TEAL_BRIGHT
SceneColors.BORDER_FOREST = SceneColors.BORDER_TEAL
SceneColors.WARNING_AMBER = SceneColors.WARNING_ACCENT

# Legacy constant aliases on SystemUI
SystemUI.MILITARY_LABEL_SIZE = SystemUI.HUD_LABEL_SIZE
SystemUI.MILITARY_VALUE_SIZE = SystemUI.HUD_VALUE_SIZE
SystemUI.MILITARY_TITLE_SIZE = SystemUI.HUD_TITLE_SIZE
SystemUI.MILITARY_SMALL_SIZE = SystemUI.HUD_SMALL_SIZE


# ─── DesignTokens singleton ───────────────────────────────────────────────

class DesignTokens:
    """Design tokens singleton — centralized visual design system."""

    def __init__(self):
        self.colors = Colors
        self.typography = Typography
        self.spacing = Spacing
        self.animation = Animation
        self.components = UIComponents
        self.system = SystemColors
        self.system_ui = SystemUI
        self.scene = SceneColors
        # Backward-compatible aliases
        self.military = SystemColors
        self.military_ui = SystemUI
        self.forest = SceneColors

    def get_font(self, size: int):
        return pygame.font.Font(pygame.font.get_default_font(), size)

    def get_scaled_font(self, base_size: int, scale: float):
        return pygame.font.Font(pygame.font.get_default_font(), int(base_size * scale))


_tokens_instance = None


def get_design_tokens() -> DesignTokens:
    global _tokens_instance
    if _tokens_instance is None:
        _tokens_instance = DesignTokens()
    return _tokens_instance


def get_colors() -> type:
    return Colors
