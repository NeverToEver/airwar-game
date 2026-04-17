from airwar.scenes import SceneManager, GameScene, MenuScene, PauseScene, LoginScene
from airwar.utils.database import UserDB
from airwar.window import create_window
from airwar.ui import GameOverScreen
from airwar.game.scene_director import SceneDirector
from airwar.config import SCREEN_WIDTH, SCREEN_HEIGHT


class Game:
    def __init__(self):
        self._window = create_window(
            SCREEN_WIDTH, 
            SCREEN_HEIGHT, 
            'Air War - 飞机大战', 
            resizable=True
        )
        self._scene_manager = SceneManager()
        self._db = UserDB()
        self._game_over_screen = GameOverScreen(self._window)
        self._director = SceneDirector(
            self._window,
            self._scene_manager,
            self._game_over_screen,
            self._db
        )
        self._register_scenes()

    def _register_scenes(self) -> None:
        self._scene_manager.register("login", LoginScene())
        self._scene_manager.register("menu", MenuScene())
        self._scene_manager.register("game", GameScene())
        self._scene_manager.register("pause", PauseScene())

    def run(self) -> None:
        try:
            self._director.run()
        finally:
            self._window.close()
