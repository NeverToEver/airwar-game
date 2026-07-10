#!/usr/bin/env python3
"""Launch AirWar with a local leaderboard server in the prepared venv."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
HEALTH_TIMEOUT_SECONDS = 20

_server_process: subprocess.Popen | None = None
_game_process: subprocess.Popen | None = None


def log(message: str) -> None:
    print(f"[airwar-server] {message}", flush=True)


def _is_supported_python(python: str | Path) -> bool:
    return subprocess.run(
        [str(python), "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"],
        capture_output=True,
        text=True,
    ).returncode == 0


def find_python() -> Path:
    """Return a Python 3.11+ interpreter, preferring the project venv."""
    venv_python = VENV_DIR / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    candidates = [venv_python, Path(sys.executable)]

    for name in ("python3.13", "python3.12", "python3.11", "python3"):
        executable = shutil.which(name)
        if executable:
            candidates.append(Path(executable))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.exists() and shutil.which(str(candidate)) is None:
            continue
        seen.add(candidate)
        if _is_supported_python(candidate):
            return candidate

    raise RuntimeError("Python 3.11 or newer was not found.")


def ensure_dependencies(python: Path) -> None:
    """Install runtime and server dependencies only when their imports are absent."""
    check = subprocess.run(
        [str(python), "-c", "import fastapi, numpy, PIL, pygame, uvicorn"],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        return

    log("Installing runtime and leaderboard dependencies...")
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "-r",
            "requirements.txt",
            "-e",
            ".[server]",
        ],
        check=True,
    )


def validate_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def ensure_port_available(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
    except OSError as exc:
        raise RuntimeError(f"{host}:{port} is unavailable: {exc}") from exc


def _server_url(host: str, port: int) -> str:
    request_host = "127.0.0.1" if host == "0.0.0.0" else host
    if ":" in request_host and not request_host.startswith("["):
        request_host = f"[{request_host}]"
    return f"http://{request_host}:{port}"


def wait_for_health(url: str, process: subprocess.Popen, timeout: float) -> bool:
    """Wait until the server responds or the spawned process exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            time.sleep(0.2)
    return False


def _terminate(process: subprocess.Popen | None, label: str) -> None:
    if process is None or process.poll() is not None:
        return
    log(f"Stopping {label}...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _terminate_server() -> None:
    global _server_process
    _terminate(_server_process, "leaderboard server")


def _terminate_game() -> None:
    global _game_process
    _terminate(_game_process, "AirWar")


def _signal_handler(signum: int, _frame) -> None:
    log(f"Received signal {signum}; shutting down...")
    _terminate_game()
    _terminate_server()
    raise SystemExit(128 + signum)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch AirWar with a local leaderboard server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server bind host (default: {DEFAULT_HOST})")
    parser.add_argument(
        "--port",
        type=validate_port,
        default=DEFAULT_PORT,
        help=f"Server port (default: {DEFAULT_PORT})",
    )
    parser.add_argument("--debug", action="store_true", help="Forward --debug to AirWar.")
    parser.add_argument(
        "--game-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Forward one additional argument to AirWar; use --game-arg=VALUE.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    os.chdir(PROJECT_ROOT)

    python = find_python()
    log(f"Python: {python}")
    ensure_dependencies(python)
    log("Runtime and server dependencies: satisfied")

    ensure_port_available(args.host, args.port)
    server_url = _server_url(args.host, args.port)
    log(f"Starting leaderboard server at {server_url}...")

    global _server_process
    _server_process = subprocess.Popen(
        [
            str(python),
            "-m",
            "airwar.leaderboard.server",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_health(f"{server_url}/health", _server_process, HEALTH_TIMEOUT_SECONDS):
            log("ERROR: leaderboard server did not become ready.")
            return 1

        game_args = [*args.game_arg]
        if args.debug:
            game_args.append("--debug")

        env = os.environ.copy()
        env["AIRWAR_LEADERBOARD_URL"] = server_url
        env["AIRWAR_LEADERBOARD_MODE"] = "remote"
        log("Launching AirWar...")
        global _game_process
        _game_process = subprocess.Popen([str(python), "main.py", *game_args], env=env)
        _game_process.wait()
        return _game_process.returncode or 0
    finally:
        _terminate_game()
        _terminate_server()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _signal_handler)
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1) from exc
