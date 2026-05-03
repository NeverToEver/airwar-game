"""Database — SimpleDB and UserDB for player statistics persistence."""
import json
import os
import hashlib
import secrets

_AIRWAR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_AIRWAR_DIR, "data", "users.json")

_HASH_ITERATIONS = 100_000


class SimpleDB:
    """Simple key-value database backed by a JSON file."""
    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path is not None else _DEFAULT_DB_PATH
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save({})

    def _load(self) -> dict:
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        try:
            tmp_path = self.db_path + ".tmp"
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.db_path)
        except (OSError, TypeError) as e:
            import logging
            logging.error(f"Failed to save database: {e}")

    def _hash_password(self, password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(),
            _HASH_ITERATIONS,
        ).hex()


class UserDB(SimpleDB):
    """User database — persists player stats (high score, kills, games played).
    
        Wraps SimpleDB with user-specific operations for tracking statistics
        across game sessions.
        """
    def __init__(self):
        super().__init__()

    def create_user(self, user_id: str, password: str) -> bool:
        data = self._load()
        if user_id in data:
            return False
        salt = secrets.token_hex(16)
        data[user_id] = {
            'password': self._hash_password(password, salt),
            'salt': salt,
            'high_score': 0,
            'total_kills': 0,
            'games_played': 0
        }
        self._save(data)
        return True

    def verify_user(self, user_id: str, password: str) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        stored = data[user_id]['password']
        salt = data[user_id].get('salt', user_id)
        return stored == self._hash_password(password, salt)

    def user_exists(self, user_id: str) -> bool:
        data = self._load()
        return user_id in data

    def get_user_data(self, user_id: str) -> dict:
        data = self._load()
        return data.get(user_id, {})

    def update_user_data(self, user_id: str, updates: dict) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        data[user_id].update(updates)
        self._save(data)
        return True

    def update_high_score(self, user_id: str, score: int) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        if score > data[user_id].get('high_score', 0):
            data[user_id]['high_score'] = score
            self._save(data)
            return True
        return False
    def delete_user(self, user_id: str, password: str = None) -> bool:
        """Delete a user account.

        If password is provided, it will be verified before deletion.
        If password is None, deletes the user without verification
        (for forgotten-password recovery).

        Args:
            user_id: Username to delete.
            password: Optional password for verification.

        Returns:
            True if user was deleted, False if not found or verification failed.
        """
        if password is not None and not self.verify_user(user_id, password):
            return False
        data = self._load()
        if user_id not in data:
            return False
        del data[user_id]
        self._save(data)
        return True

