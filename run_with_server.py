#!/usr/bin/env python3
"""Cross-platform launcher for AirWar + leaderboard server.

Starts the FastAPI leaderboard server in a background process, waits for
it to become healthy, then launches the game. The server is terminated
when the game exits.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
DEFAULT_PORT = 8000
HEALTH_TIMEOUT_SECONDS = 30

_server_process: subprocess.Popen | None = None
_game_process: subprocess.Popen | None = None


def _terminate_server() -> None:
    """Terminate the background leaderboard server if it is still running."""
    global _server_process
    proc = _server_process
    if proc is None or proc.poll() is not None:
        return
    log("Stopping leaderboard server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _terminate_game() -> None:
    """Terminate the AirWar game process if it is still running."""
    global _game_process
    proc = _game_process
    if proc is None or proc.poll() is not None:
        return
    log("Stopping AirWar...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _signal_handler(signum: int, _frame) -> None:
    """Handle termination signals by cleaning up the game, server, and exiting."""
    log(f"Received signal {signum}; shutting down...")
    _terminate_game()
    _terminate_server()
    sys.exit(128 + signum)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
if hasattr(signal, "SIGHUP"):
    signal.signal(signal.SIGHUP, _signal_handler)


def log(message: str) -> None:
    print(f"[airwar-server] {message}")


def find_python() -> Path:
    """Return the preferred Python interpreter (venv first, then system)."""
    if sys.platform == "win32":
        venv_python = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_python = VENV_DIR / "bin" / "python"
    if venv_python.exists():
        return venv_python

    for candidate in ("python3.13", "python3.12", "python3.11", "python3"):
        exe = shutil.which(candidate)
        if exe:
            proc = subprocess.run(
                [exe, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                return Path(exe)
    raise RuntimeError("Python >= 3.11 not found.")


def ensure_dependencies(python: Path) -> None:
    """Install runtime and server dependencies if any are missing."""
    check_script = "import pygame, PIL, fastapi, uvicorn"
    proc = subprocess.run([str(python), "-c", check_script], capture_output=True, text=True)
    if proc.returncode == 0:
        return

    log("Installing dependencies (including leaderboard server extras)...")
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", "-r", "requirements.txt"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--quiet", "-e", ".[server]"], check=True)


def wait_for_health(url: str, timeout: float) -> bool:
    """Poll the server health endpoint until it responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        time.sleep(0.2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch AirWar with the leaderboard server.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Leaderboard server port")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)

    python = find_python()
    log(f"Python: {python}")

    ensure_dependencies(python)
    log("Dependencies: satisfied")

    server_url = f"http://127.0.0.1:{args.port}"

    log(f"Starting leaderboard server on port {args.port}...")
    global _server_process
    _server_process = subprocess.Popen(
        [
            str(python),
            "-m",
            "airwar.leaderboard.server",
            "--port",
            str(args.port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        if not wait_for_health(f"{server_url}/health", HEALTH_TIMEOUT_SECONDS):
            log("ERROR: Leaderboard server did not become ready in time.")
            return 1
        log(f"Leaderboard server ready at {server_url}")

        log("Launching AirWar...")
        env = os.environ.copy()
        env["AIRWAR_LEADERBOARD_URL"] = server_url
        env["AIRWAR_LEADERBOARD_MODE"] = "auto"

        global _game_process
        _game_process = subprocess.Popen(
            [str(python), "main.py"],
            env=env,
        )
        _game_process.wait()
        return _game_process.returncode or 0
    finally:
        _terminate_game()
        _terminate_server()


if __name__ == "__main__":
    sys.exit(main())
