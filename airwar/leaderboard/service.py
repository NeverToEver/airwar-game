"""Leaderboard service layer — coordinates local UserDB and remote server."""

from __future__ import annotations

import logging
import time
from typing import Any

from airwar.leaderboard.client import RemoteLeaderboardClient, RemoteLeaderboardError
from airwar.leaderboard.config import LeaderboardConfig
from airwar.utils.database import DatabaseError, UserDB

logger = logging.getLogger(__name__)

_HEALTH_CACHE_TTL = 10.0


class LeaderboardService:
    """High-level leaderboard API used by scenes.

    In ``auto`` mode the remote result is preferred when the server is
    healthy; the local ``UserDB`` is still written so offline history is
    preserved. In ``local`` mode only the local DB is used. In ``remote``
    mode only the remote server is used and failures return ``0``.
    """

    def __init__(
        self,
        local_db: UserDB,
        remote_client: RemoteLeaderboardClient | None = None,
        config: LeaderboardConfig | None = None,
    ) -> None:
        self._local_db = local_db
        self._config = config or LeaderboardConfig()
        self._remote = remote_client or RemoteLeaderboardClient(
            self._config.url,
            timeout=self._config.timeout,
        )
        self._remote_available: bool | None = None
        self._health_checked_at: float = 0.0

    def _is_remote_enabled(self) -> bool:
        """Return True if remote should be used based on mode and health."""
        if self._config.is_local_mode:
            return False
        if self._config.is_remote_mode:
            return True
        return self._check_remote_health()

    def _check_remote_health(self) -> bool:
        """Return cached remote health, refreshing if the TTL has expired."""
        now = time.monotonic()
        if self._remote_available is None or now - self._health_checked_at > _HEALTH_CACHE_TTL:
            try:
                self._remote_available = self._remote.health_check()
            except RemoteLeaderboardError:
                logger.debug(
                    "Remote leaderboard health check failed (mode=%s, url=%s)",
                    self._config.mode,
                    self._config.url,
                    exc_info=True,
                )
                self._remote_available = False
            self._health_checked_at = now
            logger.debug("Remote leaderboard health: %s", self._remote_available)
        return self._remote_available

    def is_remote_active(self) -> bool:
        """Return True when the UI should display the global leaderboard."""
        if self._config.is_local_mode:
            return False
        if self._config.is_remote_mode:
            return True
        return self._check_remote_health()

    def is_local_only(self) -> bool:
        """Return True when the service is forced to local-only mode."""
        return self._config.is_local_mode

    def submit_score(self, name: str, score: Any) -> int:
        """Submit a score locally and, if enabled, remotely.

        Args:
            name: Player display name.
            score: Final score value.

        Returns:
            The best 1-indexed rank obtained. In remote-only mode the
            remote rank is returned (0 on failure). In auto mode the
            remote rank is preferred when healthy, falling back to the
            local rank on remote failure. In local-only mode only the
            local rank is returned.
        """
        try:
            score_value = int(score)
        except (TypeError, ValueError):
            logger.warning("Invalid score submitted for %r: %r", name, score)
            return 0
        if score_value < 0:
            logger.warning("Negative score submitted for %r: %s", name, score_value)
            return 0

        if self._config.is_remote_mode:
            try:
                return self._remote.submit_score(name, score_value)
            except RemoteLeaderboardError:
                logger.warning(
                    "Failed to submit score to remote leaderboard "
                    "(mode=%s, url=%s, player=%s, score=%s)",
                    self._config.mode,
                    self._config.url,
                    name,
                    score_value,
                    exc_info=True,
                )
                self._remote_available = False
                return 0

        remote_rank = 0
        remote_succeeded = False
        if not self._config.is_local_mode and self._is_remote_enabled():
            try:
                remote_rank = self._remote.submit_score(name, score_value)
                remote_succeeded = True
            except RemoteLeaderboardError:
                logger.warning(
                    "Failed to submit score to remote leaderboard "
                    "(mode=%s, url=%s, player=%s, score=%s)",
                    self._config.mode,
                    self._config.url,
                    name,
                    score_value,
                    exc_info=True,
                )
                self._remote_available = False

        try:
            local_rank = self._local_db.submit_score(name, score_value)
        except DatabaseError:
            logger.warning(
                "Failed to submit score to local leaderboard "
                "(db_path=%s, player=%s, score=%s)",
                self._local_db.db_path,
                name,
                score_value,
                exc_info=True,
            )
            local_rank = 0

        return remote_rank if remote_succeeded else local_rank

    def get_leaderboard(self) -> list[dict]:
        """Return the current top leaderboard entries.

        Prefers remote when active; falls back to local on failure.
        An empty remote list is a valid state and is returned as-is.
        """
        if self._is_remote_enabled():
            try:
                return self._remote.get_leaderboard()
            except RemoteLeaderboardError:
                logger.warning(
                    "Failed to fetch remote leaderboard (mode=%s, url=%s)",
                    self._config.mode,
                    self._config.url,
                    exc_info=True,
                )
                self._remote_available = False

        try:
            return self._local_db.get_leaderboard()
        except DatabaseError:
            logger.warning(
                "Failed to fetch local leaderboard (db_path=%s)",
                self._local_db.db_path,
                exc_info=True,
            )
            return []
