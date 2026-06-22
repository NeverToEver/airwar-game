"""Remote leaderboard client, service, and optional FastAPI server.

The server submodule is deliberately not imported here so that the game
client can import this package without requiring FastAPI/uvicorn.
"""

from __future__ import annotations

from airwar.leaderboard.client import RemoteLeaderboardClient, RemoteLeaderboardError
from airwar.leaderboard.config import LeaderboardConfig
from airwar.leaderboard.service import LeaderboardService

__all__ = [
    "LeaderboardConfig",
    "LeaderboardService",
    "RemoteLeaderboardClient",
    "RemoteLeaderboardError",
]
