# Air War · 空战

**English** | [中文](./README.md)

[![CI](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml/badge.svg)](https://github.com/NeverToEver/airwar-game/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Rust](https://img.shields.io/badge/rust-PyO3-orange?logo=rust)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

A 2D space shooter built with Python + Pygame, with an optional Rust extension for performance-critical paths.

---

## Overview

- **Stack**: Python 3.11+, Pygame, Pillow; optional Rust + PyO3 extension (`airwar_core/`).
- **Architecture**: Scene-based, covering Welcome, Tutorial, Game, Pause, Death, Settings, and Exit scenes.
- **State management**: Player and Boss are driven by hierarchical state machines (HSM); complex interactions are arbitrated by a priority `LockManager`.
- **i18n**: Simplified Chinese (zh_CN) and English (en_US).
- **Leaderboard**: Local JSON leaderboard plus an optional FastAPI + SQLite remote server, with automatic fallback when the server is unreachable.
- **Tests**: 970+ automated tests, headless SDL support, GitHub Actions CI.

## Features

- **Optional Rust acceleration**: hot paths such as collision detection, vector math, batch movement, particles, and bullet updates can run in Rust; falls back to pure Python when the extension is unavailable.
- **Scene-based lifecycle**: every scene owns `enter/exit/update/render`, making state transitions explicit.
- **Priority lock system**: `HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > GIVE_UP > GAME_PAUSE` unifies invincibility, control locks, and pause handling.
- **Update pipeline**: `GameScene.update()` runs hit-stop, input, animation, pause gate, collision, cleanup, and milestone checks in a fixed order to avoid state races.
- **Tutorial**: 7-stage tutorial reusing the real game UI and systems.
- **Runtime asset cache**: fonts, glow surfaces, and similar assets are generated once and cached for faster subsequent launches.

## Quick Start

### One-click launcher (recommended)

The launcher auto-detects the environment, creates a virtualenv, installs dependencies, builds the Rust extension, and starts the game.

| Platform | Command |
|----------|---------|
| Windows | Double-click `run.bat` |
| Linux / macOS | `chmod +x run.sh && ./run.sh` |

To also start the local leaderboard server:

| Platform | Command |
|----------|---------|
| Windows | Double-click `run_with_server.bat` |
| Linux / macOS | `chmod +x run_with_server.sh && ./run_with_server.sh` |
| macOS (double-click) | `run_with_server.command` |

> To clean local build artifacts and the virtualenv, run `uninstall.bat` on Windows or `./uninstall.sh` on Linux / macOS. Source code, saves, and config files are preserved.

### Manual launch

```bash
cd airwar-game
pip install -r requirements.txt

# Optional: build the Rust extension
cd airwar_core && maturin develop --release && cd ..

python3 main.py
```

> Building Rust on Windows requires Visual C++ Build Tools; the launcher prints a download link if the build fails.

## Controls

| Key / Input | Action |
|-------------|--------|
| Arrow keys / WASD | Move the ship |
| Ctrl (hold) | Precision mode — speed drops to 35% |
| Mouse | Aim — with auto-aim assist |
| Shift (hold) | Boost — 1.7× speed, consumes fuel |
| Shift (press-release) | Phase Dash (requires talent unlock) — invincible dash |
| Auto | Ship fires continuously |
| ESC | Pause |
| B (hold 2.4 s) | Homecoming — return to base for resupply |
| H (hold 3 s) | Dock with the mothership and save progress |
| K (hold 3 s) | Surrender the current sortie |
| L | Toggle HUD expanded / collapsed |

## Leaderboard

The leaderboard subsystem is optional and runs locally by default. The remote server simulates a client-server architecture.

- **Local-first fallback**: scores are always written to the local `UserDB`; the leaderboard falls back to local data when the remote server is unreachable.
- **Modes**: `auto` (default) / `remote` / `local`, set via `AIRWAR_LEADERBOARD_MODE`.
- **Start the server manually**:

```bash
pip install -e ".[server]"
python -m airwar.leaderboard.server --port 8000 --db-path ./leaderboard.db
```

| Variable | Default | Description |
|----------|---------|-------------|
| `AIRWAR_LEADERBOARD_URL` | `http://localhost:8000` | Remote server URL |
| `AIRWAR_LEADERBOARD_MODE` | `auto` | `auto` / `remote` / `local` |
| `AIRWAR_LEADERBOARD_TIMEOUT` | `3.0` | HTTP timeout (seconds) |
| `AIRWAR_LEADERBOARD_DB_PATH` | Platform data directory | Server SQLite path |

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Full test suite
python3 -m pytest

# Quick smoke tests
python3 -m pytest -m smoke

# Lint
python3 -m ruff check .

# Bytecode check
python3 -m compileall -q airwar main.py
```

Run tests from the project root, not from inside `airwar/`.

## Architecture

```text
WelcomeScene → TutorialScene → GameScene
                    ├─ PauseScene
                    ├─ DeathScene
                    ├─ SettingsScene
                    └─ ExitConfirmScene
```

Core modules:

- `airwar/entities/` — Player, enemies, Boss, bullets, etc.
- `airwar/game/managers/` — Collision, spawn, bullet, Boss, milestone managers.
- `airwar/game/systems/` — Health, reward, difficulty, notification, talent systems.
- `airwar/scenes/` — Scene implementations.
- `airwar/leaderboard/` — Leaderboard client, service layer, FastAPI server.
- `airwar_core/` — Rust native extension.

For more details see [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).

## Packaging

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

Output goes to `dist/AirWar`. Packaging requires Python 3.11+, the Rust toolchain, and a platform compiler; end users of the packaged binary do not need Python or Rust installed.

## Contributing

- Before opening a PR, please run `python3 -m ruff check .` and `python3 -m pytest`.
- See [`LICENSE`](./LICENSE) for licensing details.

---

*Air War is a hobby project maintained in spare time. Feedback and bug reports are welcome.*
