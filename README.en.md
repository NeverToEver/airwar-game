# Air War

[中文版](./README.md) | **English**

A 2D space-shooter built with Python + Pygame, with an optional Rust
extension for performance-critical paths. Includes a 7-stage tutorial, boss
fights, a home base with a requisition-point economy, mouse-driven aim
assist, and a local cache for runtime-generated assets.

> Air War is a hobby project, currently in pre-1.0 development. APIs and
> file formats may change between commits. If you are looking for a stable
> release, please pin to a tagged commit.

## Quick Start

**Recommended — one-click launcher** (auto-detects Python, creates a
virtualenv, installs deps, builds the Rust extension, launches the game):

- **Windows:** double-click `run.bat`
- **Linux / macOS:** `chmod +x run.sh && ./run.sh`

On first run the launcher will create a virtualenv and install Python
dependencies. The Rust toolchain and SDL2 system headers are only installed
when you pass `--install-deps` or set `AIRWAR_INSTALL_DEPS=1`; the game
runs fine on the pure-Python fallback if you skip them.

**Local cleanup:** double-click `uninstall.bat` (Windows) or run
`./uninstall.sh` (Linux/macOS) to remove the local virtualenv, build
artefacts, and caches. Source, save data, account data, and config files
are left untouched.

> Windows note: the Rust build step requires Visual C++ Build Tools. If
> the build fails, the script will print the download link. Install the
> "Desktop development with C++" workload.

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
| Ctrl (hold) | Precision mode — speed drops to 35 %, blue indicator ring around the ship for fine dodging through dense bullet patterns |
| Mouse | Aim — auto-aim assist snaps to the nearest enemy; large mouse movements override the assist |
| Shift (hold) | Boost — consumes boost energy, +70 % speed |
| Shift (press-release) | Phase Dash (requires talent unlock) — costs 25 % boost energy, 250 px invincible dash |
| Auto-fire | Ship fires automatically (no fire key) |
| ESC | Pause |
| B (hold 2.4 s) | Homecoming — FTL return to the home base |
| H (hold 3 s) | Dock with the mothership and save progress |
| K (hold 3 s) | Surrender the current sortie |
| L | Toggle HUD expanded / collapsed |

## Project Overview

- **Default resolution:** 1920×1080, 60 FPS, with adaptive window scaling.
- **Three difficulty modes:** Easy / Medium / Hard with dynamic in-run
  difficulty growth.
- **Auto-fire + mouse aim assist** with two-layer target selection
  (auto-snap to nearest enemy, large mouse movement overrides to the
  enemy nearest the cursor direction). Raw mouse input is smoothed to
  remove the jerk at assist transitions.
- **Boost system:** hold Shift to engage, 1.7× speed multiplier, fuel
  consumption with delayed recovery, 270° arc-gauge UI. Pressing Shift
  and releasing within the input window triggers Phase Dash (talent
  unlock required): 25 % fuel cost, 250 px invincible dash.
- **Weapon modes:** Spread Shot (3-bullet fan at -10° / 0° / +10°) and
  Laser (single high-damage shot, 35 dmg). The two modifiers stack to
  produce a Spread Laser.
- **13 buffs** across HP, offense, defense, and utility, including a
  two-route talent system (Offense / Support) with mutually exclusive
  options inside each route.
- **Milestone reward system:** score thresholds trigger reward picks;
  talent route and selected option persist in save data.
- **Mothership system:** hold H to dock and save; the mothership can
  move under WASD/arrow control during the docked window and fires
  explosive missiles (250 dmg, 80 px AoE) until a 10-round magazine is
  empty, at which point an "AMMO DEPLETED" warning banner slides in.
- **Home base:** hold B to FTL back to a landing pad, then use the base
  talent console to repair (-2 RP), resupply (-2 RP), or switch talent
  routes. RP is earned by killing bosses (+5) and completing base
  objectives (+3). Press B again or click "Continue" to depart with an
  Orbital Strike that clears the screen.
- **Boss fight:** multi-phase movement and attack patterns. When boss
  HP drops below 30 % a 6-second Enrage sequence triggers: denser
  patterns, faster muzzle flashes, expanding boss aura, edge vignette,
  and screen-distortion overlay. Player controls are locked during the
  enrage activation.
- **Hit-response bullet clear:** player damage triggers a brief
  invincibility window and clears ordinary enemy bullets. Boss enrage
  bullets are not cleared (player is still invincible, however).
- **Runtime asset cache:** first-run sprite and font surfaces are
  generated and cached locally to avoid re-rasterising them on every
  launch.
- **Rust extension:** optional PyO3 module accelerating vector math,
  collision, batch movement, particles, bullets, and glow-surface
  generation. A pure-Python fallback is used automatically if the
  extension is not built.
- **7-stage tutorial:** main menu opens a tutorial covering movement /
  aim, boost, combat basics, mothership docking (3-phase demo), home
  base, and boss encounter. The tutorial reuses the real game UI so
  the experience matches normal play.

## Tech Stack

- Python 3.11+
- Pygame
- Pillow
- Pytest, Ruff
- Rust + PyO3 + maturin (optional acceleration)

## Project Structure

```text
airwar-game/
|-- main.py                    # Game entry point
|-- airwar/                    # Python source
|   |-- config/                # Settings, design tokens, difficulty parameters
|   |-- entities/              # Player, enemies, Boss, bullets
|   |-- game/                  # Game loop, managers, systems, rendering, mothership, animations
|   |-- scenes/                # Welcome, tutorial, gameplay, pause, death, exit, settings
|   |-- ui/                    # HUD, reward selector, base console, crosshair, gauges
|   |-- input/                 # Input handling
|   |-- utils/                 # Database, font, sprite-draw and cache helpers
|   |-- window/                # Window creation and scaling
|   |-- tests/                 # Python tests
|   `-- core_bindings.py       # Rust-extension binding entry
|-- airwar_core/               # Rust native extension
|   `-- src/
|       |-- lib.rs             # Module entry
|       |-- vector2.rs         # Vector math
|       |-- collision.rs       # Spatial-hash collision
|       |-- movement.rs        # Enemy / Boss movement math
|       |-- particles.rs       # Particle update and spawn
|       |-- bullets.rs         # Batch bullet update
|       `-- sprites.rs         # Glow-surface generation
|-- scripts/                   # Developer helper scripts
|-- tests/                     # Root-level tests
|-- docs/                      # Documentation and ADRs
|-- build_linux.sh             # Linux packaging
|-- build_macos.sh             # macOS packaging
|-- build_windows.bat          # Windows packaging
|-- requirements.txt
|-- requirements-dev.txt
|-- pytest.ini
`-- pyproject.toml
```

## Rust Native Extension

`airwar_core/` provides optional PyO3 + maturin acceleration. The game
falls back to pure Python automatically if the extension is not built.

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

## Asset Cache & Profiling

The game caches first-run generated surfaces to a local directory so
subsequent launches do not re-rasterise the same sprites. Inspect the
cache with:

```bash
python3 scripts/profile_generated_assets.py
```

## CI (GitHub Actions)

Triggered on every `push` and `pull_request`, single job on `ubuntu-latest`:

1. Python 3.11+ + Rust stable + `libsdl2-dev`
2. `pip install` + `maturin build` + `ruff check` + `compileall` + `shellcheck` + `pytest`

Local CI simulation:

```bash
python3 -m ruff check . && python3 -m compileall -q airwar main.py && python3 -m pytest
```

## Testing & Linting

Run tests from the project root, not from `airwar/`.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Full test suite
python3 -m pytest

# Lint
python3 -m ruff check .

# Specific test file
python3 -m pytest airwar/tests/test_core.py

# Specific test class
python3 -m pytest airwar/tests/test_core.py::TestPlayer -v
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

The build output is written to `dist/AirWar`. The build step requires
Python 3.11+, the Rust toolchain, and a platform compiler; end users of
the packaged binary do not need to install Python or Rust.

## Contributing & Security

- **Pull requests:** please use the
  [PR template](./.github/PULL_REQUEST_TEMPLATE.md) and link a
  `docs/ROADMAP.md` item or an issue.
- **Vulnerability reports:** see [SECURITY.md](./SECURITY.md). The
  project is maintained by a single hobbyist, so expect a 5-business-day
  acknowledgement and 30-day initial triage.
- **License:** see [LICENSE](./LICENSE).
