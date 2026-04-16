import json
import os
from typing import Optional
from .interfaces import IPersistenceManager
from .mother_ship_state import GameSaveData


class PersistenceManager(IPersistenceManager):
    SAVE_FILE_NAME = "user_docking_save.json"
    SAVE_DIRECTORY = "airwar/data"

    def __init__(self):
        self._save_path = os.path.join(self.SAVE_DIRECTORY, self.SAVE_FILE_NAME)

    def save_game(self, data: GameSaveData) -> bool:
        try:
            os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)

            save_dict = data.to_dict()
            save_dict['timestamp'] = __import__('time').time()

            with open(self._save_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Failed to save game: {e}")
            return False

    def load_game(self) -> Optional[GameSaveData]:
        if not self.has_saved_game():
            return None

        try:
            with open(self._save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return GameSaveData.from_dict(data)
        except Exception as e:
            print(f"Failed to load game: {e}")
            return None

    def has_saved_game(self) -> bool:
        return os.path.exists(self._save_path)

    def delete_save(self) -> bool:
        try:
            if os.path.exists(self._save_path):
                os.remove(self._save_path)
            return True
        except Exception as e:
            print(f"Failed to delete save: {e}")
            return False
