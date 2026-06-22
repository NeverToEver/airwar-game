"""Integration tests for the FastAPI leaderboard server."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from airwar.leaderboard.server import create_app
from airwar.leaderboard.store import SQLiteLeaderboardStore


@pytest.fixture
def client():
    """Return a TestClient backed by a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteLeaderboardStore(str(Path(tmp) / "leaderboard.db"))
        app = create_app(store)
        yield TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSubmitScore:
    def test_submit_score_returns_rank(self, client: TestClient) -> None:
        response = client.post("/leaderboard", json={"player_name": "Alice", "score": 5000})
        assert response.status_code == 200
        assert response.json() == {"rank": 1}

    def test_submit_rejects_negative_score(self, client: TestClient) -> None:
        response = client.post("/leaderboard", json={"player_name": "Alice", "score": -1})
        assert response.status_code == 422

    def test_submit_rejects_empty_name(self, client: TestClient) -> None:
        response = client.post("/leaderboard", json={"player_name": "", "score": 100})
        assert response.status_code == 422

    def test_submit_outside_top_ten_returns_zero(self, client: TestClient) -> None:
        for index in range(11):
            response = client.post("/leaderboard", json={"player_name": f"P{index}", "score": index * 100})
            assert response.status_code == 200
        low_score_response = client.post("/leaderboard", json={"player_name": "Losers", "score": 1})
        assert low_score_response.status_code == 200
        assert low_score_response.json() == {"rank": 0}


class TestGetLeaderboard:
    def test_get_leaderboard_sorted_descending(self, client: TestClient) -> None:
        client.post("/leaderboard", json={"player_name": "Bob", "score": 3000})
        client.post("/leaderboard", json={"player_name": "Alice", "score": 5000})

        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        entries = data["entries"]
        assert len(entries) == 2
        assert entries[0]["player_name"] == "Alice"
        assert entries[0]["score"] == 5000
        assert entries[1]["player_name"] == "Bob"
        assert entries[1]["score"] == 3000

    def test_get_leaderboard_respects_limit(self, client: TestClient) -> None:
        for index in range(5):
            client.post("/leaderboard", json={"player_name": f"P{index}", "score": index * 100})
        response = client.get("/leaderboard?limit=3")
        assert response.status_code == 200
        assert len(response.json()["entries"]) == 3

    def test_get_leaderboard_empty(self, client: TestClient) -> None:
        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert response.json() == {"entries": [], "total": 0}
