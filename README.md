# Air War

A 2D space shooter built with Python + Pygame, with optional Rust native acceleration.

## Quick Start

```bash
# Enter project directory
cd airwar-game

# Install dependencies
pip install -r requirements.txt

# Run the game
python3 main.py
```

## Game Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move ship |
| Shift (hold) | Boost -- consumes energy, +70% speed |
| Auto-fire | Ship fires automatically |
| ESC | Pause game |
| H (hold 3s) | Dock with mothership to save |
| K (hold 3s) | Surrender (give up current run) |
| L | Toggle HUD panel |

## Features

- **1920x1080 default resolution**, adaptive screen scaling
- Three difficulty modes (Easy / Medium / Hard), dynamic difficulty scaling
- **Boost system**: hold Shift to activate, energy bar with consumption/recovery, 270-degree arc gauge UI, difficulty-based capacity
- **13 buff types** (including Boost Recovery), 4 categories: Health / Offense / Defense / Utility
- **Mothership save system**: capital-class mothership, explosive missile AoE attack (5 targets), two-phase dock/undock animation, WASD movement
- **Full save restore**: player position, health, buff levels and effects fully saved and restored
- 8 enemy movement patterns (straight, sine, zigzag, dive, hover, spiral, noise, aggressive), Rust batch acceleration
- **Boss battles**: 4-phase omni-directional movement (Patrol / Sweep / Hover / Chase), multi-phase attacks, forced enemy clear on spawn
- **Boss escape timer**: panel-style countdown, color transitions over time (steel-blue -> amber -> red), pulse flash warning
- **Hit bullet clear**: all enemy bullets cleared when player takes damage and triggers invincibility
- Milestone reward system, periodic buff selection triggers
- Integrated HUD panel (collapsible), discrete battery-style health indicator
- Fullscreen mode (FULLSCREEN), cold-steel-blue military cockpit visual theme

## Architecture

### Core Patterns
- **Scene Pattern**: scene-based architecture with lifecycle management (enter/exit/handle_events/update/render)
- **Manager Pattern**: independent subsystem managers (spawn, collision, bullets, boss, etc.)
- **Observer Pattern**: event bus for cross-system communication (mothership docking, etc.)

### Tech Stack
- Python 3.x + Pygame + Pillow
- Rust (PyO3 0.22 / maturin 1.0) -- `airwar_core` native extension module

### Key Modules

| Module | Location | Description |
|--------|----------|-------------|
| Scenes | `airwar/scenes/` | welcome, game, pause, death, exit_confirm (5 scenes) |
| Entities | `airwar/entities/` | Player, Enemy, Boss, Bullet |
| Managers | `airwar/game/managers/` | GameController, SpawnController, CollisionController, etc. |
| Rendering | `airwar/game/rendering/` | GameRenderer, HUDRenderer |
| Systems | `airwar/game/systems/` | HealthSystem, RewardSystem, DifficultyManager, etc. |
| Buffs | `airwar/game/buffs/` | 13 buff types (including Boost Recovery) |
| UI | `airwar/ui/` | IntegratedHUD, BoostGauge, DiscreteBattery, AmmoMagazine, WarningBanner, reward_selector, segmented_bar, etc. |
| Save | `airwar/game/mother_ship/` | Mothership dock/save (state machine, interfaces, event bus, GameIntegrator) |
| Surrender | `airwar/game/give_up/` | Hold-K surrender detector |
| Rust Extension | `airwar_core/` | Native acceleration for performance hotspots (vectors, collision, batch movement, particles, sprite glow) |

## Project Structure

```
airwar-game/                  # Project root
|-- main.py                  # Entry point: python3 main.py
|-- airwar/                  # Python source package
|??   |-- config/              Config / design tokens / difficulty params
|??   |-- entities/            Game entities (Player, Enemy, Boss, Bullet)
|??   |-- game/
|??   |??   |-- game.py          Game bootstrap
|??   |??   |-- scene_director.py Scene orchestration (Welcome -> Game)
|??   |??   |-- constants.py     Global constants (GameConstants dataclass)
|??   |??   |-- managers/        Core managers
|??   |??   |-- systems/         Game systems (difficulty, reward, notification, etc.)
|??   |??   |-- rendering/       Renderers
|??   |??   |-- buffs/           Buff system (13 types)
|??   |??   |-- mother_ship/     Mothership save (state machine, interfaces, event bus, GameIntegrator)
|??   |??   |-- give_up/         Surrender detector
|??   |??   |-- explosion_animation/ Explosion effects
|??   |??   |-- death_animation/     Death animation
|??   |-- scenes/              Scene management (5 scenes: welcome, game, pause, death, exit_confirm)
|??   |-- ui/                  UI components (IntegratedHUD, BoostGauge, DiscreteBattery, AmmoMagazine, WarningBanner, reward_selector, segmented_bar, etc.)
|??   |-- input/               Input handling
|??   |-- utils/               Utilities (database, sprite rendering, mouse interaction)
|??   |-- window/              Window management
|??   |-- data/                Runtime save files
|??   |-- tests/               Test suite (~695 tests)
|??   |-- core_bindings.py     Rust <-> Python bridge
|-- airwar_core/              Rust native extension (maturin + PyO3)
|??   |-- src/
|??       |-- lib.rs            Module entry, exports all functions
|??       |-- vector2.rs        Vector math (14 functions)
|??       |-- collision.rs      Spatial hash collision + batch collision detection
|??       |-- movement.rs       Enemy movement (8 patterns) + batch movement + Boss attack math
|??       |-- particles.rs      Particle system
|??       |-- bullets.rs        Batch bullet updates
|??       |-- sprites.rs        Sprite glow surface creation
|-- tests/                    Root-level Rust binding tests (test_bullet_bindings.py)
|-- docs/                     Documentation (audit reports, refactoring guide, maintenance guide)
|-- plans/                    Implementation plans
```

## Rust Native Extension (Optional)

`airwar_core/` uses PyO3 + maturin to provide Rust acceleration for performance hotspots like collision detection, movement computation, and boss attack math. **This is optional** -- when not installed, the game falls back to pure Python and runs normally.

### Accelerated Computations

| Module | Functions | Description |
|--------|-----------|-------------|
| `vector2.rs` | 14 vector functions | length, normalize, add/sub, dot, cross, distance, angle, lerp |
| `collision.rs` | spatial_hash_collide, spatial_hash_collide_single, batch_collide_bullets_vs_entities | Spatial hash collision, batch bullet-enemy collision |
| `movement.rs` | update_movement, batch_update_movements, compute_boss_attack | Single/batch enemy movement, boss attack math |
| `particles.rs` | update_particle, batch_update_particles, generate_explosion_particles | Particle update and generation |
| `bullets.rs` | batch_update_bullets | Batch bullet position updates |
| `sprites.rs` | 5 glow creation functions | Bullet glow surface pre-rendering |

### Prerequisites

- [Rust toolchain](https://rustup.rs/) (via `rustup`)
- Python virtual environment (`.venv` recommended)

### Installation

```bash
# Method 1: Install directly in virtual env (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd airwar_core && maturin develop --release

# Method 2: Build wheel then install (no virtualenv needed)
cd airwar_core
maturin build --release
pip install --force-reinstall target/wheels/airwar_core-*.whl
```

### Verification

```bash
python3 -c "from airwar.core_bindings import RUST_AVAILABLE; print('Rust acceleration:', 'Enabled' if RUST_AVAILABLE else 'Not installed (pure Python fallback)')"
```

## Build Standalone Executable

No Python or Rust installation required to play. One-command cross-platform build.

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows (in command prompt)
build_windows.bat
```

Output at `dist/AirWar` (~40MB standalone executable with Python runtime + Rust extension + all dependencies). Double-click to run, no environment setup needed.

**Prerequisites (build-time only):**
- Python 3.12+ and PyInstaller (auto-installed by script)
- Rust toolchain (for compiling the acceleration extension; falls back to pure Python on failure)
- Platform C compiler (Linux: gcc, macOS: Xcode CLT, Windows: VS Build Tools)

## Tests

Tests must be run from the project root directory, not the `airwar/` subdirectory.

```bash
# Run all tests
python3 -m pytest

# Smoke tests only (core functionality)
python3 -m pytest -m smoke

# Specific test file
python3 -m pytest airwar/tests/test_entities.py

# Specific test class/method
python3 -m pytest airwar/tests/test_entities.py::TestPlayer -v

# Rust binding tests
python3 -m pytest airwar/tests/test_vector2_bindings.py airwar/tests/test_collision_bindings.py airwar/tests/test_movement_bindings.py airwar/tests/test_particle_bindings.py
```
