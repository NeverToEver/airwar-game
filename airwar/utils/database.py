"""Database — SimpleDB and UserDB for player statistics persistence."""
import json
import os
import hashlib
import secrets
from typing import Optional

_AIRWAR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_AIRWAR_DIR, "data", "users.json")

_HASH_ITERATIONS = 100_000


class DatabaseError(RuntimeError):
    """Raised when account data cannot be safely loaded or saved."""


class SimpleDB:
    """Simple key-value database backed by a JSON file."""
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path is not None else _DEFAULT_DB_PATH
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        try:
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        except OSError as e:
            raise DatabaseError(f"Failed to create account database directory: {db_dir}") from e
        if not os.path.exists(self.db_path):
            self._save({})

    def _load(self) -> dict:
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise DatabaseError(f"Account database is corrupted: {self.db_path}") from e
        except OSError as e:
            raise DatabaseError(f"Failed to load account database: {self.db_path}") from e

    def _save(self, data: dict) -> None:
        tmp_path = self.db_path + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.db_path)
        except (OSError, TypeError) as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise DatabaseError(f"Failed to save account database: {self.db_path}") from e

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
    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)

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
            'games_played': 0,
            'last_login_order': 0
        }
        self._save(data)
        return True

    def verify_user(self, user_id: str, password: str) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        stored = data[user_id].get('password')
        if not stored:
            return False
        salt = data[user_id].get('salt', user_id)
        return secrets.compare_digest(stored, self._hash_password(password, salt))

    def user_exists(self, user_id: str) -> bool:
        data = self._load()
        return user_id in data

    def list_usernames(self) -> list[str]:
        data = self._load()
        users = [
            (user_id, record.get('last_login_order', 0))
            for user_id, record in data.items()
            if isinstance(record, dict) and record.get('password')
        ]
        users.sort(key=lambda item: (-item[1], item[0].lower()))
        return [user_id for user_id, _ in users]

    def get_last_login_user(self) -> Optional[str]:
        data = self._load()
        users = [
            (user_id, record.get('last_login_order', 0))
            for user_id, record in data.items()
            if isinstance(record, dict) and record.get('password') and record.get('last_login_order', 0) > 0
        ]
        if not users:
            return None
        return max(users, key=lambda item: item[1])[0]

    def record_login(self, user_id: str) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        max_order = max(
            (
                record.get('last_login_order', 0)
                for record in data.values()
                if isinstance(record, dict)
            ),
            default=0,
        )
        data[user_id]['last_login_order'] = max_order + 1
        self._save(data)
        return True

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

        Args:
            user_id: Username to delete.
            password: Current password required for verification.

        Returns:
            True if user was deleted, False if missing, not found, or verification failed.
        """
        if not password:
            return False
        if not self.verify_user(user_id, password):
            return False
        data = self._load()
        if user_id not in data:
            return False
        del data[user_id]
        self._save(data)
        return True
