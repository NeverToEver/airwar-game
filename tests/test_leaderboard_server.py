"""Tests for the FastAPI leaderboard server security boundaries."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

from fastapi.testclient import TestClient  # noqa: E402

from airwar.leaderboard.server import create_app  # noqa: E402
from airwar.leaderboard.store import SQLiteLeaderboardStore  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return SQLiteLeaderboardStore(str(tmp_path / "leaderboard.db"))


@pytest.fixture
def client(store):
    return TestClient(create_app(store=store))


class TestLeaderboardLimit:
    def test_limit_within_range_returns_entries(self, client):
        response = client.get("/leaderboard?limit=50")
        assert response.status_code == 200
        assert response.json()["entries"] == []

    def test_limit_too_large_returns_422(self, client):
        response = client.get("/leaderboard?limit=101")
        assert response.status_code == 422

    def test_limit_zero_returns_422(self, client):
        response = client.get("/leaderboard?limit=0")
        assert response.status_code == 422

    def test_limit_negative_returns_422(self, client):
        response = client.get("/leaderboard?limit=-1")
        assert response.status_code == 422


class TestLeaderboardCors:
    def test_allowed_origin_preflight_succeeds(self, client):
        response = client.options(
            "/leaderboard",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_disallowed_origin_preflight_is_rejected(self, client):
        response = client.options(
            "/leaderboard",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code != 200

    def test_allowed_origin_get_includes_allow_origin(self, client):
        response = client.get("/leaderboard", headers={"Origin": "http://127.0.0.1"})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1"

    def test_disallowed_origin_get_omits_allow_origin(self, client):
        response = client.get("/leaderboard", headers={"Origin": "http://evil.example.com"})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers


class TestLeaderboardSubmit:
    def test_submit_valid_score(self, client):
        response = client.post("/leaderboard", json={"player_name": "Alice", "score": 100})
        assert response.status_code == 200
        body = response.json()
        assert body["rank"] == 1

    def test_submit_name_too_long_returns_422(self, client):
        response = client.post(
            "/leaderboard",
            json={"player_name": "A" * 33, "score": 100},
        )
        assert response.status_code == 422

    def test_submit_negative_score_returns_422(self, client):
        response = client.post("/leaderboard", json={"player_name": "Alice", "score": -1})
        assert response.status_code == 422
