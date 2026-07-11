# Air War · 空战

**English** | [中文](./README.md)

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Pygame](https://img.shields.io/badge/pygame-2.6%2B-2e8b57)
![Rust](https://img.shields.io/badge/rust-PyO3-orange?logo=rust)
[![Release](https://img.shields.io/github/v/release/NeverToEver/airwar-game)](https://github.com/NeverToEver/airwar-game/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
![Tests](https://img.shields.io/badge/tests-61%20passed-brightgreen)

![Air War gameplay](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/gameplay.png)

> A 2D space shooter built with Python + Pygame, with an optional Rust extension for performance-critical paths.

---

## Table of Contents

- [✨ Highlights](#-highlights)
- [🖼️ Screenshots](#-screenshots)
- [🎮 Controls](#-controls)
- [🚀 Quick Start](#-quick-start)
  - [One-click launcher](#one-click-launcher)
  - [Manual launch](#manual-launch)
  - [Run tests](#run-tests)
- [🏆 Leaderboard](#-leaderboard)
- [🛠️ Tech Stack](#-tech-stack)
- [🏗️ Architecture](#-architecture)
- [📦 Packaging](#-packaging)
- [🗺️ Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## ✨ Highlights

- **Optional Rust acceleration**: hot paths such as collision detection, vector math, batch movement, particles, and bullet updates can run in Rust; falls back to pure Python when the extension is unavailable.
- **Scene-based lifecycle**: every scene owns `enter/exit/update/render`, making state transitions explicit.
- **Hierarchical state machines**: player and Boss behaviors are driven by HSMs.
- **Priority lock system**: `HOMECOMING > MOTHERSHIP > BOSS_ENRAGE > PHASE_DASH > GIVE_UP > GAME_PAUSE` unifies invincibility, control locks, and pause handling.
- **Tutorial**: 7-stage tutorial reusing the real game UI and systems.
- **Runtime asset cache**: fonts, glow surfaces, and similar assets are generated once and cached for faster subsequent launches.

## 🖼️ Screenshots

All screenshots are rendered from real game scenes in a headless environment by `scripts/capture_screenshots.py`.

| Main Menu | Gameplay | Pause Menu |
|-----------|----------|------------|
| ![Main Menu](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/welcome.png) | ![Gameplay](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/gameplay.png) | ![Pause Menu](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/pause.png) |

| Settings | Game Over |
|----------|-----------|
| ![Settings](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/settings.png) | ![Game Over](https://raw.githubusercontent.com/NeverToEver/airwar-game/master/.github/screenshots/death.png) |

## 🎮 Controls

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

## 🚀 Quick Start

### One-click launcher

The launcher auto-detects the environment, creates a virtualenv, installs dependencies, builds the Rust extension, and starts the game.

| Platform | Command |
|----------|---------|
| Windows | Double-click `run.bat` |
| Linux / macOS | `chmod +x run.sh && ./run.sh` |

Common options:

```bash
./run.sh --prepare-only             # Prepare the runtime only
./run.sh --skip-rust                # Start with the Python fallback
./run.sh --rebuild-rust             # Force an optional Rust rebuild
./run.sh -- --debug                 # Forward an argument to the game
```

To also start the local leaderboard server:

| Platform | Command |
|----------|---------|
| Windows | Double-click `run_with_server.bat` |
| Linux / macOS | `chmod +x run_with_server.sh && ./run_with_server.sh` |
| macOS (double-click) | `run_with_server.command` |

Use `./run_with_server.sh --port 8001 --debug` to choose a port and launch the game in debug mode.

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

### Run tests

```bash
python3 -m pytest tests/
```

Tests cover core architectural components only (frame timing, lock arbitration, scene management, save persistence, viewport coordinates). Rendering and gameplay logic are not tested.

## 🏆 Leaderboard

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

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Game engine | Python 3.11+, Pygame 2.6+, Pillow 12.2+ |
| Native extension | Rust 2021 + PyO3 0.22 (optional) |
| Backend service | FastAPI 0.115+, uvicorn 0.34+, SQLite |
| Build tools | PyInstaller 6+, maturin |
| Code quality | ruff, mypy, pytest |

## 🏗️ Architecture

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

## 📦 Packaging

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

Output goes to `dist/AirWar`. Packaging requires Python 3.11+, the Rust toolchain, and a platform compiler; end users of the packaged binary do not need Python or Rust installed.

## 🗺️ Roadmap

- [x] Scene-driven game loop
- [x] Player and Boss hierarchical state machines
- [x] Priority locks and pause arbitration
- [x] Local JSON user database and leaderboard
- [x] Optional Rust native extension
- [ ] More Boss and enemy types
- [ ] Enhanced online leaderboard (accounts, seasons)
- [ ] Steam / itch.io page
- [ ] Mod and custom level support

## 🤝 Contributing

PRs, issues, and feedback are welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) first.

Before submitting:

```bash
python3 -m ruff check .
python3 -m compileall -q airwar main.py
python3 -m pytest tests/
```

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

---

*Air War is a hobby project maintained in spare time. Feedback and bug reports are welcome.*
