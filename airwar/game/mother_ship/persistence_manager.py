"""Persistence manager — JSON save/load for full game state."""
import json
import os
import logging
from typing import Optional
from .interfaces import IPersistenceManager
from .mother_ship_state import GameSaveData, SaveDataCorruptedError


logger = logging.getLogger(__name__)

_AIRWAR_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_SAVE_DIRECTORY = os.path.join(_AIRWAR_DIR, "data")


class PersistenceManager(IPersistenceManager):
    """Persistence manager — JSON save/load for full game state.

        Serializes and deserializes game state including player stats, buffs,
        and difficulty progression to/from JSON files.
        """
    DEFAULT_SAVE_FILE_NAME = "user_docking_save.json"
    DEFAULT_SAVE_DIRECTORY = _DEFAULT_SAVE_DIRECTORY

    def __init__(
        self,
        save_dir: Optional[str] = None,
        save_file: Optional[str] = None
    ):
        self.SAVE_DIRECTORY = save_dir or self.DEFAULT_SAVE_DIRECTORY
        self.SAVE_FILE_NAME = save_file or self.DEFAULT_SAVE_FILE_NAME
        self._save_path = os.path.join(self.SAVE_DIRECTORY, self.SAVE_FILE_NAME)

    @property
    def save_path(self) -> str:
        return self._save_path

    def save_game(self, data: GameSaveData) -> bool:
        logger.info(f"Saving game for user: {data.username}")

        try:
            os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)

            save_dict = data.to_dict()
            save_dict['timestamp'] = __import__('time').time()

            self._validate_save_dict(save_dict)

            tmp_path = self._save_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._save_path)

            logger.info(f"Game saved successfully to {self._save_path}")
            return True

        except PermissionError as e:
            logger.error(f"Permission denied to save file: {self._save_path}")
            return False
        except OSError as e:
            logger.error(f"IO error while saving game: {e}")
            return False
        except SaveDataCorruptedError as e:
            logger.error(f"Save data validation failed: {e}")
            return False
        except Exception as e:
            logger.critical(f"Unexpected error saving game: {e}")
            return False

    def _validate_save_dict(self, data: dict) -> None:
        required_keys = {'version', 'score', 'username'}
        type_checks = {
            'version': int,
            'score': int,
            'cycle_count': int,
            'kill_count': int,
            'boss_kill_count': int,
            'unlocked_buffs': list,
            'buff_levels': dict,
            'player_health': int,
            'player_max_health': int,
            'difficulty': str,
            'timestamp': (int, float),
            'is_in_mothership': bool,
            'username': str,
        }
        for key in required_keys:
            if key not in data:
                raise SaveDataCorruptedError(f"Missing required field: {key}")
        for key, expected_type in type_checks.items():
            if key in data and not isinstance(data[key], expected_type):
                raise SaveDataCorruptedError(
                    f"Field '{key}' has wrong type: expected {expected_type.__name__}, "
                    f"got {type(data[key]).__name__}"
                )

    def load_game(self) -> Optional[GameSaveData]:
        if not self.has_saved_game():
            logger.debug("No saved game found")
            return None

        logger.info(f"Loading game from {self._save_path}")

        try:
            with open(self._save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            save_data = GameSaveData.from_dict(data)
            logger.info(f"Game loaded successfully for user: {save_data.username}")
            return save_data

        except SaveDataCorruptedError as e:
            logger.error(f"Save data corrupted: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied to load file: {self._save_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in save file: {e}")
            return None
        except OSError as e:
            logger.error(f"IO error while loading game: {e}")
            return None
        except Exception as e:
            logger.critical(f"Unexpected error loading game: {e}")
            return None

    def has_saved_game(self) -> bool:
        return os.path.exists(self._save_path)

    def delete_save(self) -> bool:
        logger.info(f"Deleting saved game at {self._save_path}")

        try:
            if os.path.exists(self._save_path):
                os.remove(self._save_path)
                logger.info("Saved game deleted successfully")
            return True
        except PermissionError as e:
            logger.error(f"Permission denied to delete save: {self._save_path}")
            return False
        except OSError as e:
            logger.error(f"IO error while deleting save: {e}")
            return False
        except Exception as e:
            logger.critical(f"Unexpected error deleting save: {e}")
            return False
