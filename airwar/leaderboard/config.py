"""Leaderboard configuration loaded from environment variables."""

from __future__ import annotations

import os

from airwar.utils.platform_paths import user_data_dir


_DEFAULT_URL = "http://localhost:8000"
_DEFAULT_MODE = "auto"
_DEFAULT_TIMEOUT = "3.0"
_DEFAULT_DB_PATH = os.path.join(user_data_dir(), "leaderboard.db")


class LeaderboardConfig:
    """Runtime configuration for the remote leaderboard client/server."""

    def __init__(self) -> None:
        self.url = os.environ.get("AIRWAR_LEADERBOARD_URL", _DEFAULT_URL).rstrip("/")
        self.mode = os.environ.get("AIRWAR_LEADERBOARD_MODE", _DEFAULT_MODE).lower()
        self.timeout = float(os.environ.get("AIRWAR_LEADERBOARD_TIMEOUT", _DEFAULT_TIMEOUT))
        self.db_path = os.environ.get("AIRWAR_LEADERBOARD_DB_PATH", _DEFAULT_DB_PATH)

    @property
    def is_local_mode(self) -> bool:
        """Return True when the service is forced to local-only."""
        return self.mode == "local"

    @property
    def is_remote_mode(self) -> bool:
        """Return True when the service is forced to remote-only."""
        return self.mode == "remote"

    @property
    def is_auto_mode(self) -> bool:
        """Return True when the service should auto-detect remote availability."""
        return self.mode == "auto"
