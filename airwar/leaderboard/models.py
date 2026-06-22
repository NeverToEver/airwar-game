"""Shared Pydantic models for the leaderboard client and server."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Self

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """A single leaderboard score entry."""

    player_name: str = Field(..., min_length=1, max_length=32)
    score: int = Field(..., ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialize to a plain dict matching the legacy UserDB entry shape."""
        return {
            "player_name": self.player_name,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Reconstruct an entry from the legacy UserDB entry shape."""
        return cls(
            player_name=data["player_name"],
            score=int(data["score"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class LeaderboardSubmitRequest(BaseModel):
    """Request body for submitting a new score."""

    player_name: str = Field(..., min_length=1, max_length=32)
    score: int = Field(..., ge=0)


class LeaderboardRankResponse(BaseModel):
    """Response containing the 1-indexed rank of a submitted score."""

    rank: int


class LeaderboardResponse(BaseModel):
    """Response containing the current top leaderboard entries."""

    entries: list[LeaderboardEntry]
    total: int
