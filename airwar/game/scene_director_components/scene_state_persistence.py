"""Scene state persistence -- save/restore game state for the current user.

Extracted from :class:`airwar.game.scene_director.SceneDirector` (Phase 4 W-β).
Wraps the :class:`PersistenceManager` and provides legacy-global-save
fallback so the same behaviour is preserved across all call sites.
"""

from __future__ import annotations

from ...scenes import GameScene
from ..mother_ship import GameSaveData, PersistenceManager
from ..systems.game_save_service import GameSaveService


class SceneStatePersistence:
    """Save/load/clear game state for the director's current user.

    All public attributes are read or mutated by the parent
    :class:`SceneDirector`; the director holds a reference to a single
    instance and forwards each persistence method to it.
    """

    def __init__(self, director) -> None:
        self._director = director
        self._save_service = GameSaveService(director._save_dir)

    @property
    def save_service(self) -> GameSaveService:
        return self._save_service

    def check_and_get_saved_game(self, username: str) -> GameSaveData | None:
        return self._save_service.load(username)

    def perform_save(self, game_scene: GameScene) -> bool:
        if not game_scene:
            return False
        save_data = game_scene.create_save_data()
        if not save_data:
            return False
        return self._save_service.save(
            save_data,
            force_outside_mothership=not game_scene.is_mothership_docked(),
        )

    def save_game_on_quit(self, game_scene: GameScene) -> None:
        if not self.perform_save(game_scene):
            self._director._logger.warning("Failed to save game during quit")

    def clear_saved_game(self) -> None:
        self._save_service.clear(self._director._current_user)

    def save_and_quit(self, game_scene: GameScene) -> bool:
        saved = self.perform_save(game_scene)
        if not saved:
            self._director._logger.warning("Failed to save game before quitting")
        return saved

    def quit_without_saving(self) -> None:
        self.clear_saved_game()

    def _candidate_persistence_managers(self, username: str) -> list[PersistenceManager]:
        return self._save_service.candidate_managers(username)
