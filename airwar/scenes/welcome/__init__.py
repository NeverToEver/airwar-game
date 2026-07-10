"""Welcome-scene panel split: layout, login, difficulty, modals, leaderboard.

These widgets are private components of the welcome scene -- they are
intentionally not re-exported through :mod:`airwar.scenes` because the
public entry point remains ``airwar.scenes.welcome_scene.WelcomeScene``.
The split keeps each panel's responsibility small without altering the
welcome-scene entry point.
"""

from . import layout  # re-exported via WelcomeScene class attributes
from .difficulty_panel import DifficultyPanel
from .leaderboard_overlay import LeaderboardOverlay
from .login_panel import LoginPanel
from .welcome_modals import WelcomeModals

__all__ = [
    "DifficultyPanel",
    "LeaderboardOverlay",
    "LoginPanel",
    "WelcomeModals",
    "layout",
]
