"""Game scenes package -- welcome, game, tutorial, pause, death, exit, settings."""
from .scene import Scene, SceneManager
from .game_scene import GameScene
from .tutorial_scene import TutorialScene
from .welcome_scene import WelcomeScene
from .pause_scene import PauseScene
from .death_scene import DeathScene
from .exit_confirm_scene import ExitConfirmScene
from .settings_scene import SettingsScene

__all__ = [
    'Scene',
    'SceneManager',
    'GameScene',
    'TutorialScene',
    'WelcomeScene',
    'PauseScene',
    'DeathScene',
    'ExitConfirmScene',
    'SettingsScene',
]
