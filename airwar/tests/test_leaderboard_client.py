"""Tests for the synchronous leaderboard HTTP client."""

from __future__ import annotations

import json
import socket
import urllib.error
from unittest import mock

import pytest

from airwar.leaderboard.client import RemoteLeaderboardClient, RemoteLeaderboardError


@pytest.fixture
def client():
    return RemoteLeaderboardClient("http://localhost:9999", timeout=1.0)


class TestRemoteLeaderboardClientHealth:
    def test_health_check_success(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.status = 200
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"status":"ok"}'
            assert client.health_check() is True

    def test_health_check_failure(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.side_effect = urllib.error.URLError("connection refused")
            with pytest.raises(RemoteLeaderboardError):
                client.health_check()


class TestRemoteLeaderboardClientSubmit:
    def test_submit_score_success(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            response = mock.Mock()
            response.status = 200
            response.read.return_value = json.dumps({"rank": 3}).encode()
            urlopen.return_value.__enter__.return_value = response
            assert client.submit_score("Alice", 5000) == 3

    def test_submit_score_timeout(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.side_effect = socket.timeout()
            with pytest.raises(RemoteLeaderboardError):
                client.submit_score("Alice", 5000)

    def test_submit_score_http_error(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.side_effect = urllib.error.HTTPError(
                "http://localhost:9999/leaderboard",
                422,
                "Unprocessable Entity",
                {},
                None,
            )
            with pytest.raises(RemoteLeaderboardError):
                client.submit_score("Alice", 5000)

    def test_submit_score_invalid_json(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            response = mock.Mock()
            response.status = 200
            response.read.return_value = b"not-json"
            urlopen.return_value.__enter__.return_value = response
            with pytest.raises(RemoteLeaderboardError):
                client.submit_score("Alice", 5000)


class TestRemoteLeaderboardClientGet:
    def test_get_leaderboard_success(self, client: RemoteLeaderboardClient) -> None:
        entries = [
            {"player_name": "Alice", "score": 5000, "timestamp": "2026-06-22T00:00:00+00:00"},
        ]
        with mock.patch("urllib.request.urlopen") as urlopen:
            response = mock.Mock()
            response.status = 200
            response.read.return_value = json.dumps({"entries": entries, "total": 1}).encode()
            urlopen.return_value.__enter__.return_value = response
            assert client.get_leaderboard() == entries

    def test_get_leaderboard_failure_raises(self, client: RemoteLeaderboardClient) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.side_effect = urllib.error.URLError("connection refused")
            with pytest.raises(RemoteLeaderboardError):
                client.get_leaderboard()
