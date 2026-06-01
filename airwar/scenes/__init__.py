"""Game scenes package -- welcome, game, tutorial, pause, death, exit, settings."""

from .death_scene import DeathScene
from .exit_confirm_scene import ExitConfirmScene
from .game_scene import GameScene
from .pause_scene import PauseScene
from .scene import Scene, SceneManager
from .settings_scene import SettingsScene
from .tutorial_scene import TutorialScene
from .welcome_scene import WelcomeScene

__all__ = [
    "DeathScene",
    "ExitConfirmScene",
    "GameScene",
    "PauseScene",
    "Scene",
    "SceneManager",
    "SettingsScene",
    "TutorialScene",
    "WelcomeScene",
]
