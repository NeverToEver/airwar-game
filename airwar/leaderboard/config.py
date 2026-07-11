"""Leaderboard configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from airwar.utils.platform_paths import user_data_dir

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:8000"
_DEFAULT_MODE = "auto"
_DEFAULT_TIMEOUT = "3.0"
_DEFAULT_DB_PATH = os.path.join(user_data_dir(), "leaderboard.db")
_DEFAULT_CORS_ORIGINS = "http://localhost,http://127.0.0.1"
_MAX_TIMEOUT = 30.0


class LeaderboardConfig:
    """Runtime configuration for the remote leaderboard client/server."""

    def __init__(self) -> None:
        url = os.environ.get("AIRWAR_LEADERBOARD_URL", _DEFAULT_URL).rstrip("/")
        self.url = self._validated_url(url)

        self.timeout = self._validated_timeout(
            os.environ.get("AIRWAR_LEADERBOARD_TIMEOUT", _DEFAULT_TIMEOUT)
        )

        self.mode = os.environ.get("AIRWAR_LEADERBOARD_MODE", _DEFAULT_MODE).lower()
        if self.mode not in {"auto", "local", "remote"}:
            logger.warning("Unknown leaderboard mode %r, defaulting to auto", self.mode)
            self.mode = "auto"

        self.db_path = os.environ.get("AIRWAR_LEADERBOARD_DB_PATH", _DEFAULT_DB_PATH)

        raw_origins = os.environ.get("AIRWAR_LEADERBOARD_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
        self.cors_origins = self._validated_cors_origins(raw_origins)

    @staticmethod
    def _validated_url(url: str) -> str:
        parsed = urlparse(url)
        if not url or parsed.scheme not in ("http", "https") or not parsed.hostname:
            logger.warning("Invalid AIRWAR_LEADERBOARD_URL, using default %s", _DEFAULT_URL)
            return _DEFAULT_URL
        return url

    @staticmethod
    def _validated_timeout(raw: str) -> float:
        try:
            timeout = float(raw)
        except ValueError:
            logger.warning("Invalid AIRWAR_LEADERBOARD_TIMEOUT %r, using default %s", raw, _DEFAULT_TIMEOUT)
            return float(_DEFAULT_TIMEOUT)
        if not (0 < timeout <= _MAX_TIMEOUT):
            logger.warning(
                "AIRWAR_LEADERBOARD_TIMEOUT %s out of range, clamping to default %s",
                timeout,
                _DEFAULT_TIMEOUT,
            )
            return float(_DEFAULT_TIMEOUT)
        return timeout

    @staticmethod
    def _validated_cors_origins(raw: str) -> list[str]:
        stripped = raw.strip()
        if stripped == "*" or stripped == "":
            return ["*"]
        origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
        return origins if origins else ["http://localhost"]

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
