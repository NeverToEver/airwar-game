"""Tests for the LeaderboardService fallback/coordination layer."""

from __future__ import annotations

from unittest import mock

import pytest

from airwar.leaderboard.client import RemoteLeaderboardError
from airwar.leaderboard.config import LeaderboardConfig
from airwar.leaderboard.service import LeaderboardService
from airwar.utils.database import UserDB


@pytest.fixture
def temp_db(tmp_path):
    db = UserDB(str(tmp_path / "users.json"))
    yield db


class FakeRemoteClient:
    """In-memory remote client for deterministic service tests."""

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.entries: list[dict] = []
        self.submitted: list[tuple[str, int]] = []

    def health_check(self) -> bool:
        return self.available

    def submit_score(self, player_name: str, score: int) -> int:
        if not self.available:
            raise RemoteLeaderboardError("remote unavailable")
        self.submitted.append((player_name, score))
        self.entries.append({"player_name": player_name, "score": score, "timestamp": "2026-06-22T00:00:00+00:00"})
        self.entries.sort(key=lambda e: -e["score"])
        for rank, entry in enumerate(self.entries, start=1):
            if entry["player_name"] == player_name and entry["score"] == score:
                return rank
        return 0

    def get_leaderboard(self) -> list[dict]:
        if not self.available:
            raise RemoteLeaderboardError("remote unavailable")
        return self.entries


class TestLeaderboardServiceLocalMode:
    def test_local_mode_ignores_remote(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=True)
        config = LeaderboardConfig()
        config.mode = "local"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert remote.submitted == []
        assert service.is_remote_active() is False


class TestLeaderboardServiceRemoteMode:
    def test_remote_mode_uses_remote_rank(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=True)
        config = LeaderboardConfig()
        config.mode = "remote"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert remote.submitted == [("Alice", 5000)]

    def test_remote_mode_returns_zero_when_remote_down(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=False)
        config = LeaderboardConfig()
        config.mode = "remote"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 0


class TestLeaderboardServiceAutoMode:
    def test_auto_uses_remote_when_healthy(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=True)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert remote.submitted == [("Alice", 5000)]
        assert service.is_remote_active() is True

    def test_auto_falls_back_to_local_when_remote_down(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=False)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert remote.submitted == []
        assert service.is_remote_active() is False

    def test_auto_falls_back_to_local_when_remote_raises(self, temp_db: UserDB) -> None:
        """Auto mode falls back to local rank when the remote call raises."""
        remote = FakeRemoteClient(available=True)
        remote.submit_score = lambda _name, _score: (_ for _ in ()).throw(
            RemoteLeaderboardError("boom")
        )
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert len(temp_db.get_leaderboard()) == 1

    def test_get_leaderboard_prefers_remote(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=True)
        remote.entries = [
            {"player_name": "Remote", "score": 9000, "timestamp": "2026-06-22T00:00:00+00:00"},
        ]
        temp_db.submit_score("Local", 1000)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        entries = service.get_leaderboard()
        assert len(entries) == 1
        assert entries[0]["player_name"] == "Remote"

    def test_get_leaderboard_falls_back_to_local(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=False)
        temp_db.submit_score("Local", 1000)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        entries = service.get_leaderboard()
        assert len(entries) == 1
        assert entries[0]["player_name"] == "Local"

    def test_get_leaderboard_falls_back_on_remote_exception(self, temp_db: UserDB) -> None:
        """Auto mode falls back to local entries when remote fetch raises."""
        remote = FakeRemoteClient(available=True)
        remote.get_leaderboard = lambda: (_ for _ in ()).throw(
            RemoteLeaderboardError("boom")
        )
        temp_db.submit_score("Local", 1000)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        entries = service.get_leaderboard()
        assert len(entries) == 1
        assert entries[0]["player_name"] == "Local"

    def test_auto_get_leaderboard_empty_remote_returns_empty(self, temp_db: UserDB) -> None:
        """Empty remote list is a valid global-leaderboard state."""
        remote = FakeRemoteClient(available=True)
        remote.entries = []
        temp_db.submit_score("Local", 1000)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.get_leaderboard() == []

    def test_auto_submit_prefers_remote_rank(self, temp_db: UserDB) -> None:
        """Auto mode returns remote rank when remote is healthy."""
        remote = FakeRemoteClient(available=True)
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 1
        assert remote.submitted == [("Alice", 5000)]

    def test_auto_submit_remote_zero_returns_zero(self, temp_db: UserDB) -> None:
        """Remote rank 0 (not in top 10) is returned when remote succeeds."""
        remote = FakeRemoteClient(available=True)
        remote.submit_score = lambda _name, _score: 0
        config = LeaderboardConfig()
        config.mode = "auto"
        service = LeaderboardService(temp_db, remote_client=remote, config=config)

        assert service.submit_score("Alice", 5000) == 0
        # Local history is still preserved.
        assert len(temp_db.get_leaderboard()) == 1


class TestLeaderboardServiceHealthCache:
    def test_health_check_is_cached(self, temp_db: UserDB) -> None:
        remote = FakeRemoteClient(available=True)
        service = LeaderboardService(temp_db, remote_client=remote)

        with mock.patch.object(remote, "health_check") as health_check:
            health_check.return_value = True
            assert service.is_remote_active() is True
            assert service.is_remote_active() is True
            health_check.assert_called_once()
