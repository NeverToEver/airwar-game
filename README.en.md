# Air War

[中文版](./README.md) | **English**

A 2D space-shooter built with Python + Pygame, with an optional Rust extension for performance-critical paths.

## Features

- **Optional Rust acceleration** — `airwar_core/` uses PyO3 + maturin to provide native implementations for hot paths (vector math, collision detection, batch movement, particles, bullet updates, glow-surface generation). Falls back to pure Python automatically with zero configuration.
- **Scene architecture** — `SceneManager` manages the full lifecycle: Welcome → Tutorial → Game → Pause/Death/Settings/Exit. Each scene encapsulates `enter/exit/handle_events/update/render`.
- **HSM state machines** — Player and Boss both use hierarchical state machines: Player uses `_ALIVE_TRANSITIONS` + `IllegalPlayerTransition`; Boss uses 8-state `_BOSS_TRANSITIONS` + enrage sub-machine.
- **LockManager priority arbitration** — 6 priority layers (HOMECOMING 100 / MOTHERSHIP 80 / BOSS_ENRAGE 60 / PHASE_DASH 40 / GIVE_UP 20 / GAME_PAUSE 10) unify invincibility, control-lock, and pause conflicts.
- **15-step update pipeline** — `GameScene.update()` executes in strict order: tick_hit_stop → input/animation/pause-gate → collision detection → dead-entity cleanup → milestone check.
- **i18n internationalization** — Supports zh_CN / en_US, 134 translation keys, `t(key, **kwargs)` public API.
- **Runtime asset cache** — First-run sprite/font surfaces are generated and cached locally; subsequent launches reuse cached images.
- **924 test cases** — pytest-driven, supports headless SDL environments, 40% coverage gate.

## Technical Approach

This project follows a **Pygame-native** approach:

```
Python 3.11+ + Pygame (core)
       ↓
Rust + PyO3 (optional performance layer)
       ↓
maturin (build tool)
```

- **Core layer**: Python + Pygame handles game logic, rendering, input processing
- **Performance layer**: Rust via PyO3 bindings accelerates hot-path computation (collision, vectors, particles, batch updates)
- **Fallback strategy**: `core_bindings.py` uses `try: from airwar_core import ... except (ImportError, OSError)` for graceful degradation; `RUST_AVAILABLE` flag for consumer checks
- **No external engine dependency**: Pure Pygame implementation, no Godot/Unity migration

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.11+ | Game logic, config, tests |
| **Game engine** | Pygame 2.6+ | Rendering, event loop, audio |
| **Image processing** | Pillow 12+ | Sprite scaling, format conversion |
| **Native extension** | Rust + PyO3 0.22 | Performance hot-path acceleration |
| **Build tool** | maturin 1.0 | Rust → Python binding compilation |
| **Packaging** | PyInstaller 6+ | Standalone executable generation |
| **Testing** | pytest 8+ | Unit tests, property tests |
| **Linting** | ruff 0.8+ | Code style checking (E/W/F rules) |

## Detailed Description

### Gameplay

Players pilot a spacecraft through space, fighting enemies and bosses to earn scores and buffs, ultimately challenging Bosses to complete stages.

**Core Systems:**

- **Auto-fire + mouse aim assist** — Ship fires continuously; mouse controls aim direction. `AimAssistSystem` implements two-layer target selection (auto-lock nearest enemy / large mouse movement overrides to cursor-direction target). Raw input has short-delay smoothing.
- **Boost system** — Hold Shift to engage, 1.7× speed, fuel consumption with delayed recovery; 270° arc-gauge UI.
- **Phase Dash** — Requires talent unlock. Press and release Shift to trigger: 25% fuel cost, 250px invincible dash.
- **Weapon modes** — Spread Shot (3-bullet fan at -10°/0°/+10°) and Laser (single high-damage shot, 35 dmg). The two modifiers stack to produce Spread Laser.
- **13 buffs** — Cover HP, offense, defense, and utility. Includes two-route talent system (Offense/Support) with mutually exclusive options within each route.
- **Milestone rewards** — Score thresholds trigger reward selection; talent route and selected option persist in save data.

### Mothership & Base

- **Mothership system** — Hold H to dock and save progress. Mothership can move and provides explosive missile support (250 dmg / 80px AoE), 10-round magazine limit.
- **Home base** — Hold B for FTL return to landing pad. Use Requisition Points (RP) for repair (-2RP), resupply (-2RP), and talent route switching. RP earned by killing bosses (+5) and completing base missions (+3).
- **Orbital Strike** — Triggers full-screen bullet clear when departing from base, providing a safe sortie window.

### Boss Fights

- Multi-phase movement and attack patterns (Patrol/Sweep/Hover/Chase)
- Boss HP drops below 30% triggers Core Overload: 6-second enrage sequence with faster attack pacing and muzzle flash frequency
- Enrage visuals: Boss diffusion aura + screen-edge vignette + distortion overlay
- Hit-response bullet clear: Player damage triggers brief invincibility and clears ordinary enemy bullets; Boss enrage bullets are not cleared

### Tutorial

Main menu opens a 7-stage tutorial:
1. Movement & Aim
2. Boost
3. Combat Basics
4. Mothership Docking (3-phase demo: ghost appearance, fire support, ejection)
5. Home Base (with resupply flow)
6. Boss Encounter

Tutorial reuses real game UI components for authentic experience.

## Architecture

### Scene System

```
WelcomeScene → TutorialScene (first play) → GameScene
     │                                      ├─ PauseScene (ESC)
     │                                      ├─ DeathScene (player death)
     │                                      ├─ ExitConfirmScene (quit)
     │                                      ├─ SettingsScene (settings)
     └─ GameScene (returning player)
```

### Entity Hierarchy

```
Entity (base) — rect, collision_rect, active
  ├─ Player — HSM-driven, _ALIVE_TRANSITIONS
  ├─ Enemy — 8 movement patterns
  │    └─ Boss — 4-component coordinator
  │         ├─ BossStateMachine (8-state HSM + enrage sub-machine)
  │         ├─ BossMovement (Patrol/Sweep/Hover/Chase)
  │         ├─ BossAttackPatterns (Spread/Aim/Wave/Snapshot)
  │         └─ BossRenderer (Sprite/facing/enrage trail)
  └─ Bullet
```

### Manager Split

| Manager | Responsibility |
|---------|----------------|
| `CollisionController` | Collision detection (Rust batch collision support) |
| `SpawnManager` | Enemy spawning & wave management |
| `BulletManager` | Bullet lifecycle management |
| `BossManager` | Boss appearance & behavior coordination |
| `MilestoneManager` | Milestone triggers & reward selection |
| `InputCoordinator` | Input event distribution |

### LockManager Priority

| Layer | Priority | Trigger |
|-------|----------|---------|
| `HOMECOMING` | 100 | FTL return to base |
| `MOTHERSHIP` | 80 | Mothership docking |
| `BOSS_ENRAGE` | 60 | Boss HP < 30% |
| `PHASE_DASH` | 40 | Phase Dash |
| `GIVE_UP` | 20 | Surrender |
| `GAME_PAUSE` | 10 | ESC pause / reward selector |

## Quick Start

**Recommended — one-click launcher** (auto-detects Python, creates a virtualenv, installs deps, builds the Rust extension, launches the game):

- **Windows:** double-click `run.bat`
- **Linux / macOS:** `chmod +x run.sh && ./run.sh`

On first run the launcher will create a virtualenv and install Python dependencies. The Rust toolchain and SDL2 system headers are only installed when you pass `--install-deps` or set `AIRWAR_INSTALL_DEPS=1`; the game runs fine on the pure-Python fallback if you skip them.

**Local cleanup:** double-click `uninstall.bat` (Windows) or run `./uninstall.sh` (Linux/macOS) to remove the local virtualenv, build artefacts, and caches. Source, save data, account data, and config files are left untouched.

> Windows note: the Rust build step requires Visual C++ Build Tools. If the build fails, the script will print the download link. Install the "Desktop development with C++" workload.

**Manual launch:**

```bash
cd airwar-game
pip install -r requirements.txt
cd airwar_core && maturin develop --release && cd ..
python3 main.py
```

## Controls

| Key / Input | Action |
|-------------|--------|
| Arrow keys / WASD | Move the ship |
| Ctrl (hold) | Precision mode — speed drops to 35%, blue indicator ring for fine dodging |
| Mouse | Aim — auto-aim assist with smooth input delay |
| Shift (hold) | Boost — consumes boost energy, +70% speed |
| Shift (press-release) | Phase Dash (requires talent unlock) — costs 25% boost energy, 250px invincible dash |
| Auto-fire | Ship fires automatically |
| ESC | Pause |
| B (hold 2.4 s) | Homecoming — FTL return to the home base |
| H (hold 3 s) | Dock with the mothership and save progress |
| K (hold 3 s) | Surrender the current sortie |
| L | Toggle HUD expanded / collapsed |

## Rust Native Extension

`airwar_core/` uses PyO3 + maturin to provide optional performance acceleration. Modules include:

| Module | Function |
|--------|----------|
| `vector2.rs` | Vector math (add/sub/mul/div, normalize, dot product, lerp, angle) |
| `collision.rs` | Spatial-hash collision detection |
| `movement.rs` | Enemy/Boss movement calculation (batch updates) |
| `particles.rs` | Particle system update & rendering |
| `bullets.rs` | Batch bullet updates |
| `sprites.rs` | Glow-surface generation (bullet halos, explosion circles) |
| `starfield.rs` | Starfield background calculation |

### Build

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd airwar_core
maturin develop --release
```

### Verify

```bash
python3 -c "from airwar.core_bindings import batch_update_bullets; print('Rust native extension: installed')"
```

## Project Structure

```text
airwar-game/
├── main.py                    # Game entry point
├── airwar/                    # Python game source
│   ├── config/                # Settings, design tokens, difficulty parameters
│   ├── entities/              # Player, enemies, Boss, bullets
│   ├── game/                  # Game loop, managers, systems, rendering, mothership, animations
│   │   ├── managers/          # Collision, spawn, bullet, Boss, milestone managers
│   │   ├── systems/           # Health, reward, difficulty, notification, talent systems
│   │   └── homecoming/        # Homecoming sequence
│   ├── scenes/                # Welcome, tutorial, gameplay, pause, death, exit, settings
│   ├── ui/                    # HUD, reward selector, base console, crosshair, gauges
│   ├── i18n/                  # Internationalization translator
│   ├── locales/               # Language files (zh_CN.json, en_US.json)
│   ├── input/                 # Input handling
│   ├── utils/                 # Database, font, sprite-draw and cache helpers
│   ├── window/                # Window creation and scaling
│   ├── tests/                 # Python tests
│   └── core_bindings.py       # Rust-extension binding entry
├── airwar_core/               # Rust native extension
│   └── src/
│       ├── lib.rs             # Module entry
│       ├── vector2.rs         # Vector math
│       ├── collision.rs       # Spatial-hash collision
│       ├── movement.rs        # Enemy / Boss movement math
│       ├── particles.rs       # Particle update and spawn
│       ├── bullets.rs         # Batch bullet update
│       ├── sprites.rs         # Glow-surface generation
│       └── starfield.rs       # Starfield background calculation
├── scripts/                   # Developer helper scripts
├── tests/                     # Root-level tests
├── docs/                      # Documentation and ADRs
├── build_linux.sh             # Linux packaging
├── build_macos.sh             # macOS packaging
├── build_windows.bat          # Windows packaging
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── pyproject.toml
```

## Testing & Linting

Run tests from the project root, not from `airwar/`.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Full test suite
python3 -m pytest

# Smoke tests (quick core functionality verification)
python3 -m pytest -m smoke

# Lint
python3 -m ruff check .

# Specific test file
python3 -m pytest airwar/tests/test_core.py

# Specific test class
python3 -m pytest airwar/tests/test_core.py::TestPlayer -v
```

## CI (GitHub Actions)

Triggered on every `push` and `pull_request`, single job on `ubuntu-latest`:

1. Python 3.11+ + Rust stable + `libsdl2-dev`
2. `pip install` + `maturin build` + `ruff check` + `compileall` + `shellcheck` + `pytest`

Local CI simulation:

```bash
python3 -m ruff check . && python3 -m compileall -q airwar main.py && python3 -m pytest
```

## Build Standalone Executable

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows
build_windows.bat
```

The build output is written to `dist/AirWar`. The build step requires Python 3.11+, the Rust toolchain, and a platform compiler; end users of the packaged binary do not need to install Python or Rust.

## Contributing & Security

- **Pull requests:** please use the [PR template](./.github/PULL_REQUEST_TEMPLATE.md) and link a `docs/ROADMAP.md` item or an issue.
- **Vulnerability reports:** see [SECURITY.md](./SECURITY.md). The project is maintained by a single hobbyist, so expect a 5-business-day acknowledgement and 30-day initial triage.
- **License:** see [LICENSE](./LICENSE).
