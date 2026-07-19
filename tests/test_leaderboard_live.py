"""Live end-to-end tests for the remote leaderboard chain.

Unlike ``test_leaderboard_server.py`` (in-process ASGI TestClient), these
tests boot a real uvicorn server on an ephemeral port and talk to it through
the game's production ``RemoteLeaderboardClient`` (urllib) and
``LeaderboardService`` — the exact code path exercised at runtime by
``run_with_server.py``.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

from airwar.leaderboard.client import RemoteLeaderboardClient  # noqa: E402
from airwar.leaderboard.config import LeaderboardConfig  # noqa: E402
from airwar.leaderboard.server import create_app  # noqa: E402
from airwar.leaderboard.service import LeaderboardService  # noqa: E402
from airwar.leaderboard.store import SQLiteLeaderboardStore  # noqa: E402
from airwar.utils.database import UserDB  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"leaderboard server did not become ready at {url}")


@pytest.fixture
def live_server(tmp_path):
    """Run a real uvicorn server with a fresh temp SQLite DB per test."""
    app = create_app(store=SQLiteLeaderboardStore(str(tmp_path / "leaderboard.db")))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base_url)
    except BaseException:
        server.should_exit = True
        thread.join(timeout=5)
        raise
    yield base_url
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def local_db(tmp_path):
    return UserDB(str(tmp_path / "users.json"))


def _make_config(monkeypatch: pytest.MonkeyPatch, url: str, mode: str, timeout: str = "1.0") -> LeaderboardConfig:
    monkeypatch.setenv("AIRWAR_LEADERBOARD_URL", url)
    monkeypatch.setenv("AIRWAR_LEADERBOARD_MODE", mode)
    monkeypatch.setenv("AIRWAR_LEADERBOARD_TIMEOUT", timeout)
    return LeaderboardConfig()


class TestLiveClient:
    def test_health_check(self, live_server):
        assert RemoteLeaderboardClient(live_server, timeout=1.0).health_check() is True

    def test_submit_fetch_roundtrip_and_entry_shape(self, live_server):
        client = RemoteLeaderboardClient(live_server, timeout=2.0)
        assert client.submit_score("Alice", 100) == 1
        assert client.submit_score("Bob", 200) == 1
        assert client.submit_score("Carol", 50) == 3

        entries = client.get_leaderboard()
        assert [(entry["player_name"], entry["score"]) for entry in entries] == [
            ("Bob", 200),
            ("Alice", 100),
            ("Carol", 50),
        ]
        # The UI layer (LeaderboardView) reads these keys directly.
        for entry in entries:
            assert set(entry) >= {"player_name", "score", "timestamp"}


class TestLiveServerCli:
    def test_module_entry_point_serves_requests(self, tmp_path):
        """``python -m airwar.leaderboard.server`` is the deployment path used by run_with_server."""
        port = _free_port()
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "airwar.leaderboard.server",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--db-path",
                str(tmp_path / "cli.db"),
            ],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            _wait_for_health(url)
            client = RemoteLeaderboardClient(url, timeout=2.0)
            assert client.submit_score("Cli", 7) == 1
            assert client.get_leaderboard()[0]["player_name"] == "Cli"
        finally:
            proc.terminate()
            proc.wait(timeout=5)


class TestLiveService:
    def test_remote_mode_roundtrip_and_skips_local(self, live_server, local_db, monkeypatch):
        service = LeaderboardService(local_db, config=_make_config(monkeypatch, live_server, "remote"))
        assert service.is_remote_active() is True
        assert service.submit_score("Dora", 1234) == 1
        entries = service.get_leaderboard()
        assert entries[0]["player_name"] == "Dora"
        assert entries[0]["score"] == 1234
        # Remote-only mode must not touch the local DB.
        assert local_db.get_leaderboard() == []

    def test_auto_mode_prefers_remote_and_mirrors_local(self, live_server, local_db, monkeypatch):
        service = LeaderboardService(local_db, config=_make_config(monkeypatch, live_server, "auto"))
        assert service.submit_score("Eve", 300) == 1
        # Remote preferred for reads ...
        remote_entries = service.get_leaderboard()
        assert [(e["player_name"], e["score"]) for e in remote_entries] == [("Eve", 300)]
        # ... while the local DB keeps an offline copy of the submission.
        assert [(e["player_name"], e["score"]) for e in local_db.get_leaderboard()] == [("Eve", 300)]

    def test_local_mode_ignores_remote(self, live_server, local_db, monkeypatch):
        service = LeaderboardService(local_db, config=_make_config(monkeypatch, live_server, "local"))
        assert service.is_remote_active() is False
        assert service.submit_score("Frank", 64) == 1
        assert [(e["player_name"], e["score"]) for e in service.get_leaderboard()] == [("Frank", 64)]
        # The live server must have seen nothing.
        assert RemoteLeaderboardClient(live_server, timeout=1.0).get_leaderboard() == []

    def test_auto_mode_falls_back_to_local_when_server_down(self, local_db, monkeypatch):
        dead_url = f"http://127.0.0.1:{_free_port()}"
        service = LeaderboardService(local_db, config=_make_config(monkeypatch, dead_url, "auto", timeout="0.5"))
        assert service.is_remote_active() is False
        assert service.submit_score("Grace", 42) == 1
        assert [(e["player_name"], e["score"]) for e in service.get_leaderboard()] == [("Grace", 42)]


class TestLiveView:
    def test_view_fetches_live_entries_and_remote_footer(self, live_server, local_db, monkeypatch):
        from airwar.ui.leaderboard_view import LeaderboardView

        service = LeaderboardService(local_db, config=_make_config(monkeypatch, live_server, "remote"))
        service.submit_score("Hank", 900)
        view = LeaderboardView(service)

        entries = view.fetch_entries()
        assert [(e["player_name"], e["score"]) for e in entries] == [("Hank", 900)]
        footer = view._footer_text()
        # A missing i18n key would fall back to the raw key string.
        assert "leaderboard.footer" not in footer
        assert footer.startswith("Top ")
