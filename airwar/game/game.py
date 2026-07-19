"""Game bootstrap -- window creation, scene registration, and main loop."""

from ..config import SCREEN_HEIGHT, SCREEN_WIDTH
from ..scenes import (
    DeathScene,
    ExitConfirmScene,
    GameScene,
    PauseScene,
    SceneManager,
    SettingsScene,
    TutorialScene,
    WelcomeScene,
)
from ..utils.database import UserDB
from ..utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches
from ..window import create_window
from .scaled_viewport import ScaledViewport
from .scene_director import SceneDirector


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
        from airwar.i18n import set_locale

        # H-10: apply the user's persisted language preference. The
        # default (no stored preference, no logged-in user yet) is
        # ``zh_CN`` — same as the pre-H-10 behaviour — so a first-launch
        # user sees the historically-Chinese UI. The Welcome scene
        # re-applies the language after login, once the username is
        # known, so this initial read only matters for the first few
        # frames before login.
        set_locale("zh_CN")
        self._window = create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Air War - Sky Combat", resizable=True)
        # Fixed logical resolution (P2): the viewport's logical surface
        # is always the design-time 1920x1080, no matter what size the
        # OS window is. Windowed scaling is done by SDL2 SCALED; the
        # viewport letterboxes in fullscreen. Mouse coordinates are
        # mapped back via ScaledViewport.screen_to_logical().
        self._viewport = ScaledViewport(SCREEN_WIDTH, SCREEN_HEIGHT)
        self._viewport.update(*self._window.get_size())
        self._scene_manager = SceneManager()
        self._db = UserDB()
        self._director = SceneDirector(self._window, self._scene_manager, self._db, self._viewport)
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
