"""SQLite-backed storage for the remote leaderboard server."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from airwar.leaderboard.models import LeaderboardEntry


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leaderboard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    score INTEGER NOT NULL,
    timestamp TEXT NOT NULL
)
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_leaderboard_score ON leaderboard(score DESC)
"""


class SQLiteLeaderboardStore:
    """Persistent leaderboard storage using SQLite.

    The store keeps every submitted score and returns the top N on query.
    Submission returns the 1-indexed rank within the top cap, or 0 if the
    score did not make the cut.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_dir()
        self._init_schema()

    def _ensure_dir(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.execute(_CREATE_INDEX_SQL)

    def submit_score(self, player_name: str, score: int, *, cap: int = 10) -> int:
        """Insert a score and return its 1-indexed rank, or 0 if not in top cap.

        Args:
            player_name: Display name for the entry.
            score: Non-negative score value.
            cap: Number of entries considered for ranking.

        Returns:
            1-indexed rank if the score made the top ``cap``, otherwise 0.
        """
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO leaderboard (player_name, score, timestamp) VALUES (?, ?, ?)",
                (player_name, score, timestamp),
            )
            conn.commit()
            rank = self._rank_of_score(conn, score, timestamp)
            return rank if rank <= cap else 0

    def _rank_of_score(self, conn: sqlite3.Connection, score: int, timestamp: str) -> int:
        """Return the 1-indexed rank of a score with the given timestamp.

        Ties are broken by earlier timestamp.
        """
        cursor = conn.execute(
            "SELECT score, timestamp FROM leaderboard ORDER BY score DESC, timestamp ASC"
        )
        for index, row in enumerate(cursor.fetchall(), start=1):
            if row["score"] == score and row["timestamp"] == timestamp:
                return index
        return 0

    def get_leaderboard(self, limit: int = 10) -> list[LeaderboardEntry]:
        """Return the top ``limit`` entries sorted by score descending."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT player_name, score, timestamp FROM leaderboard "
                "ORDER BY score DESC, timestamp ASC LIMIT ?",
                (limit,),
            )
            return [
                LeaderboardEntry(
                    player_name=row["player_name"],
                    score=row["score"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                for row in cursor.fetchall()
            ]

    def count(self) -> int:
        """Return the total number of stored entries."""
        with self._connect() as conn:
            row: sqlite3.Row | None = conn.execute(
                "SELECT COUNT(*) AS total FROM leaderboard"
            ).fetchone()
            return int(row["total"]) if row else 0

    def clear(self) -> None:
        """Remove all entries. Intended for tests."""
        with self._connect() as conn:
            conn.execute("DELETE FROM leaderboard")
            conn.commit()
