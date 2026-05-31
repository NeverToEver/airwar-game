"""UI package — panels, particles, effects, and interactive components."""
from .buff_stats_panel import BuffStatsPanel
from .difficulty_coefficient_panel import DifficultyCoefficientPanel
from .effects import EffectsRenderer
from .game_over_screen import GameOverScreen, ScreenAction
from .give_up_ui import GiveUpUI
from .menu_background import MenuBackground
from .particles import ParticleSystem
from .reward_selector import RewardSelector

__all__ = [
    'GameOverScreen', 'ScreenAction',
    'RewardSelector',
    'BuffStatsPanel',
    'MenuBackground',
    'ParticleSystem',
    'EffectsRenderer',
    'GiveUpUI',
    'DifficultyCoefficientPanel',
]
