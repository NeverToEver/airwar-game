"""Config package — game settings, design tokens, and difficulty configuration."""

from .design_tokens import get_colors, get_design_tokens
from .difficulty_config import BASE_ENEMY_PARAMS, DIFFICULTY_CONFIGS, MOVEMENT_PATTERNS
from .game_config import (
    GameConfig,
    get_display_height,
    get_display_width,
    get_screen_height,
    get_screen_width,
    set_display_size,
)
from .settings import *
from .tutorial import TUTORIAL_PAGES, TUTORIAL_STAGES, TutorialStage

__all__ = [
    "BASE_ENEMY_PARAMS",
    "BOOST_CONFIG",
    "DIFFICULTY_CONFIGS",
    "DIFFICULTY_SETTINGS",
    "ENEMY_COLLISION_SCALE",
    "ENEMY_HITBOX_PADDING",
    "ENEMY_HITBOX_SIZE",
    "ENEMY_VISUAL_SCALE",
    "FPS",
    "HEALTH_REGEN",
    "HITBOX_INDICATOR_ALPHA_MAX",
    "HITBOX_INDICATOR_ALPHA_MIN",
    "HITBOX_INDICATOR_FREQUENCY",
    "HITBOX_INDICATOR_PADDING",
    "MOVEMENT_PATTERNS",
    "RIPPLE_FADE_SPEED",
    "SCREEN_HEIGHT",
    "SCREEN_WIDTH",
    "TUTORIAL_PAGES",
    "TUTORIAL_STAGES",
    "VALID_DIFFICULTIES",
    "GameConfig",
    "TutorialStage",
    "get_colors",
    "get_design_tokens",
    "get_display_height",
    "get_display_width",
    "get_screen_height",
    "get_screen_width",
    "set_display_size",
]
