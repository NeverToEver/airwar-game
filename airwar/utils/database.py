"""Database — SimpleDB and UserDB for player statistics persistence."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

from airwar.utils.platform_paths import redact_home_path, user_data_dir

logger = logging.getLogger(__name__)

if sys.platform.startswith("win"):
    _fcntl: Any = None
else:
    try:
        import fcntl

        _fcntl = fcntl
    except ImportError:
        _fcntl = None


@contextmanager
def _file_lock(lock_path: str) -> Generator[None, None, None]:
    """Advisory file lock for load-modify-save sequences.

    On POSIX systems ``fcntl.flock`` is used. On Windows or platforms without
    ``fcntl`` the lock is a no-op and a warning is logged once.
    """
    if _fcntl is None:
        logger.warning("File locking is not available on this platform (%s)", sys.platform)
        yield
        return

    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        _fcntl.flock(fd, _fcntl.LOCK_EX)
        yield
    finally:
        if fd is not None:
            try:
                _fcntl.flock(fd, _fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass

_DEFAULT_DB_PATH = os.path.join(user_data_dir(), "users.json")
_AIRWAR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_DB_PATH = os.path.join(_AIRWAR_DIR, "data", "users.json")

_HASH_ITERATIONS = 100_000

LEADERBOARD_CAP = 10
_LEADERBOARD_KEY = "_leaderboard"
_MAX_NAME_LEN = 32

# Shape aliases. The on-disk JSON is a free-form mapping, so we keep the
# leaf type loose (``Any``) where the value is genuinely heterogeneous
# (user records, leaderboard entries). For container slots we still
# prefer concrete generics over bare ``dict``/``list`` for clarity.
UserRecord = dict[str, Any]
LeaderboardEntry = dict[str, Any]
UserData = dict[str, UserRecord]
Leaderboard = list[LeaderboardEntry]


class DatabaseError(RuntimeError):
    """Raised when account data cannot be safely loaded or saved."""


class _AbortOperation(Exception):
    """Internal signal used to abort a locked modifier without saving."""


def _safe_score(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("score", 0))
    except (TypeError, ValueError):
        return 0


class SimpleDB:
    """Simple key-value database backed by a JSON file."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path if db_path is not None else _DEFAULT_DB_PATH
        if os.path.exists(self.db_path) and os.path.isdir(self.db_path):
            raise DatabaseError(f"Database path is a directory: {self.db_path}")
        self._lock_path = f"{self.db_path}.lock"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        db_dir = os.path.dirname(self.db_path)
        try:
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            self._migrate_legacy_db_if_needed()
        except OSError as e:
            raise DatabaseError(f"Failed to create account database directory: {db_dir}") from e
        if not os.path.exists(self.db_path):
            self._save({})

    def _migrate_legacy_db_if_needed(self) -> None:
        if self.db_path != _DEFAULT_DB_PATH:
            return
        if os.path.exists(self.db_path) or not os.path.exists(_LEGACY_DB_PATH):
            return
        shutil.copy2(_LEGACY_DB_PATH, self.db_path)

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.db_path, encoding="utf-8") as f:
                result: dict[str, Any] = json.load(f)
                return result
        except json.JSONDecodeError:
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 0:
                backup_path = f"{self.db_path}.corrupted.{int(time.time())}.bak"
                try:
                    os.replace(self.db_path, backup_path)
                    logger.error("Account database corrupted; backed up to %s", backup_path)
                except OSError as move_err:
                    logger.error("Failed to backup corrupted database: %s", move_err)
                    try:
                        os.remove(self.db_path)
                    except OSError:
                        pass
            logger.error("Account database corrupted; resetting to empty: %s", redact_home_path(self.db_path))
            self._save({})
            return {}
        except OSError as e:
            raise DatabaseError(f"Failed to load account database: {self.db_path}") from e

    def _save(self, data: dict[str, Any]) -> None:
        db_dir = os.path.dirname(self.db_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=db_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.db_path)
        except (OSError, TypeError) as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                logger.warning("Failed to remove temporary account database file: %s", tmp_path, exc_info=True)
            raise DatabaseError(f"Failed to save account database: {self.db_path}") from e

    def _load_locked(self) -> dict[str, Any]:
        """Load the database while holding the advisory file lock."""
        with _file_lock(self._lock_path):
            return self._load()

    def _atomic_load_modify_save(self, modifier: Any) -> None:
        """Execute ``modifier(data)`` under the advisory file lock and persist.

        This serialises read-modify-write cycles across processes so that
        concurrent writes do not overwrite each other.
        """
        with _file_lock(self._lock_path):
            data = self._load()
            modifier(data)
            self._save(data)

    def _hash_password(self, password: str, salt: str) -> str:
        if not isinstance(password, str) or not isinstance(salt, str):
            raise TypeError("password and salt must be strings")
        if not password or not salt:
            raise ValueError("password and salt cannot be empty")
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            _HASH_ITERATIONS,
        ).hex()


class UserDB(SimpleDB):
    """User database — persists player stats (high score, kills, games played).

    Wraps SimpleDB with user-specific operations for tracking statistics
    across game sessions.
    """

    def __init__(self, db_path: str | None = None):
        super().__init__(db_path)

    def create_user(self, user_id: str, password: str) -> bool:
        if not isinstance(password, str) or len(password) < 1:
            return False

        def _create(data: dict[str, Any]) -> None:
            if user_id in data:
                raise _AbortOperation()
            salt = secrets.token_hex(16)
            data[user_id] = {
                "password": self._hash_password(password, salt),
                "salt": salt,
                "high_score": 0,
                "total_kills": 0,
                "games_played": 0,
                "last_login_order": 0,
            }

        try:
            self._atomic_load_modify_save(_create)
        except _AbortOperation:
            return False
        return True

    def verify_user(self, user_id: str, password: str) -> bool:
        data = self._load_locked()
        if user_id not in data:
            return False
        stored = data[user_id].get("password")
        if not stored:
            return False
        salt = data[user_id].get("salt")
        if not isinstance(salt, str) or not salt:
            logger.error("User %r is missing a valid salt; refusing verification", user_id)
            return False
        return secrets.compare_digest(stored, self._hash_password(password, salt))

    def user_exists(self, user_id: str) -> bool:
        data = self._load_locked()
        return user_id in data

    def list_usernames(self) -> list[str]:
        data = self._load_locked()
        users = [
            (user_id, record.get("last_login_order", 0))
            for user_id, record in data.items()
            if isinstance(record, dict) and record.get("password")
        ]
        users.sort(key=lambda item: (-item[1], item[0].lower()))
        return [user_id for user_id, _ in users]

    def get_last_login_user(self) -> str | None:
        data = self._load_locked()
        users = [
            (user_id, record.get("last_login_order", 0))
            for user_id, record in data.items()
            if isinstance(record, dict) and record.get("password") and record.get("last_login_order", 0) > 0
        ]
        if not users:
            return None
        return max(users, key=lambda item: item[1])[0]

    def record_login(self, user_id: str) -> bool:
        def _record(data: dict[str, Any]) -> None:
            if user_id not in data:
                raise _AbortOperation()
            max_order = max(
                (record.get("last_login_order", 0) for record in data.values() if isinstance(record, dict)),
                default=0,
            )
            data[user_id]["last_login_order"] = max_order + 1

        try:
            self._atomic_load_modify_save(_record)
        except _AbortOperation:
            return False
        return True

    def get_user_data(self, user_id: str) -> UserRecord:
        data = self._load_locked()
        record: UserRecord = data.get(user_id, {})
        return record

    def update_user_data(self, user_id: str, updates: dict[str, Any]) -> bool:
        def _update(data: dict[str, Any]) -> None:
            if user_id not in data:
                raise _AbortOperation()
            data[user_id].update(updates)

        try:
            self._atomic_load_modify_save(_update)
        except _AbortOperation:
            return False
        return True

    def update_high_score(self, user_id: str, score: int) -> bool:
        def _update(data: dict[str, Any]) -> None:
            if user_id not in data:
                raise _AbortOperation()
            if score <= data[user_id].get("high_score", 0):
                raise _AbortOperation()
            data[user_id]["high_score"] = score

        try:
            self._atomic_load_modify_save(_update)
        except _AbortOperation:
            return False
        return True

    # -- Leaderboard ---------------------------------------------------

    def _get_or_init_leaderboard(self, data: dict[str, Any]) -> Leaderboard:
        """Return the leaderboard list from data, creating it if missing.

        Args:
            data: The full user-database dict (will be mutated in place).

        Returns:
            The list of leaderboard entries (may be empty).
        """
        entries = data.get(_LEADERBOARD_KEY)
        if not isinstance(entries, list):
            entries = []
            data[_LEADERBOARD_KEY] = entries
        return entries

    def get_leaderboard(self) -> list[LeaderboardEntry]:
        """Return the top ``LEADERBOARD_CAP`` scores sorted by score desc.

        Returns:
            A new list of ``{player_name, score, timestamp}`` dicts. Ties
            break by earlier timestamp. Empty list if no scores recorded.
        """
        data = self._load_locked()
        entries = data.get(_LEADERBOARD_KEY, [])
        if not isinstance(entries, list):
            return []
        return sorted(
            (entry for entry in entries if isinstance(entry, dict)),
            key=lambda entry: (-_safe_score(entry), entry.get("timestamp", "")),
        )[:LEADERBOARD_CAP]

    def submit_score(self, name: str, score: int) -> int:
        """Record a score and return its 1-indexed rank (0 if not in top 10).

        Args:
            name: Player display name. Falsy or non-string values default to
                ``"Guest"``.
            score: Non-negative integer score. Negatives are clamped to zero.

        Returns:
            1-indexed rank within the post-insert leaderboard, or ``0`` if
            the score did not make the top 10.
        """
        if isinstance(score, bool):
            return 0
        if not isinstance(score, int):
            try:
                score = int(score)
            except (TypeError, ValueError):
                return 0
        if score < 0:
            score = 0
        player_name = name if isinstance(name, str) and name else "Guest"
        player_name = player_name[:_MAX_NAME_LEN]

        result: list[int] = []

        def _submit(data: dict[str, Any]) -> None:
            entries = self._get_or_init_leaderboard(data)
            entry: LeaderboardEntry = {
                "player_name": player_name,
                "score": score,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017
            }
            entries.append(entry)
            data[_LEADERBOARD_KEY] = sorted(
                (item for item in entries if isinstance(item, dict)),
                key=lambda item: (-_safe_score(item), item.get("timestamp", "")),
            )[:LEADERBOARD_CAP]
            for rank, item in enumerate(data[_LEADERBOARD_KEY], start=1):
                if item is entry:
                    result.append(rank)
                    return
            result.append(0)

        self._atomic_load_modify_save(_submit)
        return result[0]

    DEFAULT_SETTINGS: dict[str, str] = {
        "ctrl_mode": "hold",
        "shift_boost_mode": "hold",
    }

    def get_user_settings(self, user_id: str) -> dict[str, str]:
        data = self._load_locked()
        if user_id not in data:
            return dict(self.DEFAULT_SETTINGS)
        saved = data[user_id].get("settings", {})
        return {**self.DEFAULT_SETTINGS, **saved}

    def update_user_settings(self, user_id: str, settings: dict[str, str]) -> bool:
        return self.update_user_data(user_id, {"settings": settings})

    def delete_user(self, user_id: str, password: str | None = None) -> bool:
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

        def _delete(data: dict[str, Any]) -> None:
            if user_id not in data:
                raise _AbortOperation()
            del data[user_id]

        try:
            self._atomic_load_modify_save(_delete)
        except _AbortOperation:
            return False
        return True
