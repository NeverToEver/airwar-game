"""Persistence manager — JSON save/load for full game state."""
import json
import os
import logging
import time
import re
import hashlib
import shutil
from typing import Optional

from airwar.utils.platform_paths import user_data_dir

from .interfaces import IPersistenceManager
from .mother_ship_state import GameSaveData, SaveDataCorruptedError, normalize_save_data


logger = logging.getLogger(__name__)

_DEFAULT_SAVE_DIRECTORY = user_data_dir()
_AIRWAR_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LEGACY_SAVE_DIRECTORY = os.path.join(_AIRWAR_DIR, "data")


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
        save_file: Optional[str] = None,
        username: Optional[str] = None,
    ):
        self.SAVE_DIRECTORY = save_dir or self.DEFAULT_SAVE_DIRECTORY
        self.SAVE_FILE_NAME = save_file or self._save_file_for_user(username)
        self._save_path = os.path.join(self.SAVE_DIRECTORY, self.SAVE_FILE_NAME)
        self._migrate_legacy_save_if_needed()

    @property
    def save_path(self) -> str:
        return self._save_path

    def _migrate_legacy_save_if_needed(self) -> None:
        if self.SAVE_DIRECTORY != self.DEFAULT_SAVE_DIRECTORY:
            return
        if os.path.exists(self._save_path):
            return
        legacy_path = os.path.join(_LEGACY_SAVE_DIRECTORY, self.SAVE_FILE_NAME)
        if not os.path.exists(legacy_path):
            return
        os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)
        shutil.copy2(legacy_path, self._save_path)

    @classmethod
    def _save_file_for_user(cls, username: Optional[str]) -> str:
        if not username:
            return cls.DEFAULT_SAVE_FILE_NAME
        safe_username = re.sub(r"[^A-Za-z0-9_.-]+", "_", username.strip())
        safe_username = safe_username.strip("._-") or "user"
        digest = hashlib.sha256(username.encode("utf-8")).hexdigest()[:12]
        return f"user_docking_save_{safe_username}_{digest}.json"

    def save_game(self, data: GameSaveData) -> bool:
        logger.info(f"Saving game for user: {data.username}")

        try:
            os.makedirs(self.SAVE_DIRECTORY, exist_ok=True)

            save_dict = data.to_dict()
            save_dict['timestamp'] = time.time()
            save_dict = normalize_save_data(save_dict)

            self._validate_save_dict(save_dict)

            tmp_path = self._save_path + ".tmp"
            if os.path.exists(tmp_path):
                logger.warning(f"Found stale temp file {tmp_path}, cleaning up")
                try:
                    os.remove(tmp_path)
                except OSError as e:
                    logger.error(f"Failed to remove stale temp file {tmp_path}: {e}")
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._save_path)

            logger.info(f"Game saved successfully to {self._save_path}")
            return True

        except PermissionError:
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
        data = normalize_save_data(data)
        required_keys = {'version', 'score', 'username'}
        type_checks = {
            'version': int,
            'score': int,
            'cycle_count': int,
            'kill_count': int,
            'boss_kill_count': int,
            'unlocked_buffs': list,
            'buff_levels': dict,
            'earned_buff_levels': dict,
            'talent_loadout': dict,
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

        # Semantic validation
        if 'player_max_health' in data and data['player_max_health'] <= 0:
            raise SaveDataCorruptedError(
                f"player_max_health must be > 0, got {data['player_max_health']}"
            )
        if 'player_health' in data and 'player_max_health' in data:
            if not (1 <= data['player_health'] <= data['player_max_health']):
                raise SaveDataCorruptedError(
                    f"player_health must be between 1 and player_max_health "
                    f"({data['player_max_health']}), got {data['player_health']}"
                )
        for key in ('score', 'kill_count', 'boss_kill_count', 'cycle_count'):
            if key in data and data[key] < 0:
                raise SaveDataCorruptedError(
                    f"{key} must be >= 0, got {data[key]}"
                )
        if 'difficulty' in data and data['difficulty'] not in ('easy', 'medium', 'hard'):
            raise SaveDataCorruptedError(
                f"difficulty must be one of 'easy', 'medium', 'hard', "
                f"got '{data['difficulty']}'"
            )
        if 'version' in data and data['version'] < 1:
            raise SaveDataCorruptedError(
                f"version must be >= 1, got {data['version']}"
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
            self.delete_save()
            return None
        except PermissionError:
            logger.error(f"Permission denied to load file: {self._save_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in save file: {e}")
            self.delete_save()
            return None
        except OSError as e:
            logger.error(f"IO error while loading game: {e}")
            return None
        except Exception as e:
            logger.critical(f"Unexpected error loading game: {e}")
            self.delete_save()
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
        except PermissionError:
            logger.error(f"Permission denied to delete save: {self._save_path}")
            return False
        except OSError as e:
            logger.error(f"IO error while deleting save: {e}")
            return False
        except Exception as e:
            logger.critical(f"Unexpected error deleting save: {e}")
            return False
