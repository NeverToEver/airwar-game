"""Synchronous HTTP client for the remote leaderboard server."""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class RemoteLeaderboardError(Exception):
    """Raised when a leaderboard request fails due to network, HTTP, or parse errors."""


class RemoteLeaderboardClient:
    """Thin sync client that talks to the FastAPI leaderboard server.

    Uses only ``urllib.request`` from the standard library so the game
    runtime does not depend on ``httpx`` or ``requests``. All methods
    swallow network failures and return safe default values so the game
    loop is never interrupted by a remote outage.
    """

    def __init__(self, base_url: str, timeout: float = 3.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        """Perform a JSON request and return (status, parsed_body).

        Raises:
            RemoteLeaderboardError: On transport, HTTP, or JSON parse failures.
        """
        url = f"{self._base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                return resp.status, json.loads(resp_body) if resp_body else None
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, TimeoutError) as exc:
            raise RemoteLeaderboardError(f"{method} {url} failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RemoteLeaderboardError(f"{method} {url} returned invalid JSON: {exc}") from exc

    def health_check(self) -> bool:
        """Return True if the server responds with HTTP 200 on /health."""
        status, _ = self._request("GET", "/health")
        return status == 200

    def submit_score(self, player_name: str, score: int) -> int:
        """Submit a score and return its 1-indexed rank."""
        status, body = self._request(
            "POST",
            "/leaderboard",
            data={"player_name": player_name, "score": score},
        )
        if status == 200 and isinstance(body, dict):
            return int(body.get("rank", 0))
        raise RemoteLeaderboardError(
            f"Unexpected response from /leaderboard: status={status}, body={body!r}"
        )

    def get_leaderboard(self) -> list[dict]:
        """Fetch the top leaderboard entries."""
        status, body = self._request("GET", "/leaderboard")
        if status == 200 and isinstance(body, dict):
            entries = body.get("entries", [])
            if isinstance(entries, list):
                return entries
        raise RemoteLeaderboardError(
            f"Unexpected response from /leaderboard: status={status}, body={body!r}"
        )
