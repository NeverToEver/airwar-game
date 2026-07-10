"""Single persistence boundary for gameplay save operations."""

from __future__ import annotations

from airwar.game.mother_ship import GameSaveData, PersistenceManager


class GameSaveService:
    """Own the save-directory and per-user persistence policy for one game run."""

    def __init__(self, save_dir: str | None = None) -> None:
        self._save_dir = save_dir

    def save(self, data: GameSaveData, *, force_outside_mothership: bool = False) -> bool:
        if force_outside_mothership:
            data.is_in_mothership = False
        return PersistenceManager(save_dir=self._save_dir, username=data.username).save_game(data)

    def load(self, username: str) -> GameSaveData | None:
        if not username:
            return None
        for manager in self.candidate_managers(username):
            save_data = manager.load_game()
            if save_data and save_data.username == username:
                return save_data
        return None

    def clear(self, username: str | None) -> None:
        for manager in self.candidate_managers(username):
            save_data = manager.load_game()
            if save_data and save_data.username == username:
                manager.delete_save()

    def candidate_managers(self, username: str | None) -> list[PersistenceManager]:
        return [
            PersistenceManager(save_dir=self._save_dir, username=username),
            PersistenceManager(save_dir=self._save_dir),
        ]


__all__ = ["GameSaveService"]
