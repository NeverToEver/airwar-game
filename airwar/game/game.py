"""Game bootstrap -- window creation, scene registration, and main loop."""
from ..scenes import SceneManager, GameScene, TutorialScene, WelcomeScene, PauseScene, DeathScene, ExitConfirmScene, SettingsScene
from ..utils.database import UserDB
from ..window import create_window
from .scene_director import SceneDirector
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT
from ..utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches
from .scaled_viewport import ScaledViewport


class Game:
    """Game bootstrap -- window creation, scene registration, and main loop.

        Creates the pygame window, registers all scenes, and runs the main
        event loop. Delegates rendering to the active scene.

        Attributes:
            window: Pygame display surface.
            scene_manager: SceneManager handling active scene.
            scene_director: SceneDirector for scene orchestration.
        """
    def __init__(self):
        self._window = create_window(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            'Air War - Sky Combat',
            resizable=True
        )
        self._viewport = ScaledViewport(SCREEN_WIDTH, SCREEN_HEIGHT)
        self._viewport.update(*self._window.get_size())
        self._scene_manager = SceneManager()
        self._db = UserDB()
        self._director = SceneDirector(
            self._window,
            self._scene_manager,
            self._db,
            self._viewport
        )
        self._register_scenes()

    def _register_scenes(self) -> None:
        self._scene_manager.register("welcome", WelcomeScene())
        self._scene_manager.register("game", GameScene())
        self._scene_manager.register("tutorial", TutorialScene())
        self._scene_manager.register("pause", PauseScene())
        self._scene_manager.register("settings", SettingsScene())
        self._scene_manager.register("death", DeathScene())
        self._scene_manager.register("exit_confirm", ExitConfirmScene())

    def run(self) -> None:
        try:
            # Pre-warm sprite glow caches for optimal performance
            prewarm_glow_caches()
            prewarm_ship_sprite_caches()
            self._director.run()
        finally:
            self._window.close()
