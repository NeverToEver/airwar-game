from typing import Tuple, Dict, Any
import pygame


class Colors:
    BACKGROUND_PRIMARY = (5, 5, 8)
    BACKGROUND_SECONDARY = (12, 10, 8)
    BACKGROUND_PANEL = (8, 6, 5)
    BACKGROUND_OVERLAY = (0, 0, 0, 200)

    HUD_AMBER = (255, 180, 50)
    HUD_AMBER_BRIGHT = (255, 200, 80)
    HUD_ORANGE = (255, 140, 0)
    HUD_ORANGE_DEEP = (200, 100, 0)

    PARTICLE_PRIMARY = (255, 150, 50)
    PARTICLE_ALT = (255, 100, 80)

    TEXT_PRIMARY = (255, 220, 180)
    TEXT_SECONDARY = (220, 180, 150)
    TEXT_MUTED = (150, 120, 100)
    TEXT_HINT = (120, 100, 80)

    HEALTH_NORMAL = (255, 180, 80)
    HEALTH_DANGER = (255, 80, 60)
    SCORE_COLOR = (255, 220, 180)
    PROGRESS_COLOR = (255, 160, 80)
    KILLS_COLOR = (220, 180, 150)
    BOSS_COLOR = (255, 100, 80)

    BUTTON_SELECTED_BG = (50, 35, 25)
    BUTTON_UNSELECTED_BG = (30, 20, 15)
    PANEL_BORDER = (150, 110, 80)

    BUTTON_SELECTED_PRIMARY = (255, 160, 60)
    BUTTON_SELECTED_GLOW = (255, 200, 100)
    BUTTON_SELECTED_TEXT = (255, 240, 220)

    BUTTON_UNSELECTED_PRIMARY = (180, 130, 80)
    BUTTON_UNSELECTED_GLOW = (220, 170, 100)
    BUTTON_UNSELECTED_TEXT = (200, 170, 140)

    DANGER_BUTTON_SELECTED_PRIMARY = (255, 100, 60)
    DANGER_BUTTON_SELECTED_GLOW = (255, 140, 100)
    DANGER_BUTTON_UNSELECTED_PRIMARY = (180, 60, 40)
    DANGER_BUTTON_UNSELECTED_GLOW = (220, 80, 60)

    BOSS_HEALTH_HIGH = (255, 140, 60)
    BOSS_HEALTH_MED = (255, 100, 60)
    BOSS_HEALTH_LOW = (255, 80, 60)

    WARNING = (255, 100, 80)
    SUCCESS = (255, 180, 100)
    INFO = (255, 200, 120)

    @staticmethod
    def star_color(brightness: int) -> Tuple[int, int, int]:
        return (brightness + 20, brightness + 10, brightness)


class Typography:
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


class UIComponents:
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


class DesignTokens:
    def __init__(self):
        self.colors = Colors
        self.typography = Typography
        self.spacing = Spacing
        self.animation = Animation
        self.components = UIComponents

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


def get_typography() -> type:
    return Typography


def get_spacing() -> type:
    return Spacing


def get_animation() -> type:
    return Animation
