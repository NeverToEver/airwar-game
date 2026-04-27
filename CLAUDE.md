# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Air War (飞机大战)** is a 2D space shooter game built with Python + Pygame. Players control a spaceship, fight enemies, collect buffs, and dock with a mothership to save progress. Rust extension module (`airwar_core`) provides performance-critical computation.

### Tech Stack

- Python 3.x + Pygame + Pillow
- Rust (PyO3 0.22 / maturin 1.0) — `airwar_core` extension module
- Architecture: Scene Pattern, Manager Pattern, Observer Pattern

---

## Commands

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Run the Game

```bash
python3 main.py
```

### Test

```bash
# All tests
python3 -m pytest

# Smoke tests (core functionality)
python3 -m pytest -m smoke

# Exclude slow tests
python3 -m pytest -m "not slow"

# Specific test file
python3 -m pytest airwar/tests/test_entities.py

# Specific test class/method
python3 -m pytest airwar/tests/test_entities.py::TestPlayer -v

# Rust binding tests
python3 -m pytest airwar/tests/test_vector2_bindings.py airwar/tests/test_collision_bindings.py airwar/tests/test_movement_bindings.py airwar/tests/test_particle_bindings.py
```

### Build Rust Extension

```bash
cd airwar_core && maturin develop --release
```

### Test Configuration

Config at `airwar/tests/pytest.ini` — defaults: `-v --tb=short -ra`. Markers: `smoke` (core), `slow` (integration/performance). Fixtures: `temp_db`, `clean_imports`. Some tests require `pygame.init()`.

**Note:** Tests must be run from the project root directory, not from within the `airwar/` subdirectory.

### Validation Commands

```bash
# Check Python syntax on all files
python3 -m py_compile airwar/**/*.py

# Verify imports work
python3 -c "from airwar.game import Game; from airwar.entities import Player, Enemy"

# Check for prohibited local imports in methods (should return 0 results)
grep -rn "^\s\+from airwar\." airwar/ --include="*.py" \
  | grep -v "core_bindings" | grep -v "from airwar.core_bindings"
```

---

## Rust Extension (`airwar_core/`)

PyO3 extension module providing performance-critical computation with graceful Python fallback.

**Location:** `airwar_core/` — Rust workspace with Cargo.

**Modules:**

| Module | Functions | Python binding |
|--------|-----------|----------------|
| `vector2.rs` | vec2_length, normalize, add, sub, dot, cross, scale, distance, angle, lerp, clamp_length | `core_bindings.py` |
| `collision.rs` | spatial_hash_collide, spatial_hash_collide_single | `core_bindings.py` |
| `movement.rs` | update_movement (8 types: straight, sine, zigzag, dive, hover, spiral, noise, aggressive) | `core_bindings.py` |
| `particles.rs` | update_particle, batch_update_particles, generate_explosion_particles | `core_bindings.py` |
| `sprites.rs` | create_single_bullet_glow, create_spread_bullet_glow, create_laser_bullet_glow, create_explosive_missile_glow | `core_bindings.py` |
| `bullets.rs` | batch_update_bullets | `core_bindings.py` |

**Note:** `draw_glow_circle` uses pygame fallback only (Rust version has visual differences). Rust sprites acceleration covers bullet glow surfaces; enemy core glow uses pygame.

**Fallback mechanism** (`airwar/core_bindings.py`):
```python
try:
    from airwar_core import vec2_length, ...
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False  # Callers handle with pure Python fallback
```

**Build:** `maturin develop --release` (requires Rust toolchain via rustup).  
**Tests:** Python tests at `tests/test_*_bindings.py` exercise the Rust module (vector2, collision, movement, particles, sprites). No Rust-side test framework configured.

---

## Architecture

### Package Structure

Source code lives under `airwar/` (Python package). Entry point: `main.py` (project root).

```
airwar-game/                  # Project root
├── main.py                  # Entry: python3 main.py
├── airwar/                  # Python package (all source)
│   ├── config/              # Settings, game_config, design_tokens, difficulty_config, tutorial/
│   ├── entities/            # Entity base, Player, Enemy (+ Boss subclass), Bullet
│   ├── game/
│   │   ├── game.py          # Game class — window, SceneManager, SceneDirector, scene registration
│   │   ├── scene_director.py # Login→Menu→Game orchestration
│   │   ├── constants.py     # GameConstants dataclass (all tuning constants)
│   │   ├── managers/        # GameController, SpawnController, CollisionController, BulletManager,
│   │   │                    # BossManager, MilestoneManager, InputCoordinator, UIManager, GameLoopManager
│   │   ├── controllers/     # Reserved for subsystem controllers (currently unused)
│   │   ├── spawners/        # EnemyBulletSpawner
│   │   ├── systems/         # HealthSystem, RewardSystem, NotificationManager, DifficultyManager,
│   │   │                    # MovementPatternGenerator
│   │   ├── rendering/       # GameRenderer, HUDRenderer
│   │   ├── buffs/           # 12 buff types (health, offense, defense, utility)
│   │   ├── mother_ship/     # Dock/save: state machine, persistence (JSON), event bus, interfaces, GameIntegrator
│   │   ├── give_up/         # Surrender system (hold-K detector)
│   │   ├── explosion_animation/
│   │   └── death_animation/
│   ├── scenes/              # Scene base, 7 scenes: login, menu, game, pause, death, exit_confirm, tutorial
│   ├── ui/                  # GameHUD (integrated HUD), reward_selector, buff_stats, chamfered_panel,
│   │                        # hex_icon, segmented_bar, game_over_screen, give_up_ui, effects, menu_background
│   ├── input/               # PygameInputHandler
│   ├── utils/               # UserDB, mouse_interaction mixins, sprites, responsive
│   ├── window/              # Resizable window management
│   ├── data/                # Runtime save files (users.json, user_docking_save.json)
│   ├── tests/               # pytest suite
│   └── core_bindings.py     # Rust→Python bridge with fallback
├── airwar_core/             # Rust PyO3 extension (maturin)
├── docs/                    # Rust perf plan, superpower specs, audit reports, REFACTORING_GUIDE
├── plans/                   # Implementation plans
└── requirements.txt
```

### Scene Flow

```
LoginScene → MenuScene → GameScene
                           ├── PauseScene (ESC)
                           ├── DeathScene (player death)
                           ├── ExitConfirmScene (quit)
                           └── TutorialScene
```

`SceneDirector` orchestrates transitions and state preservation. `SceneManager` supports `save_scene_state(name, state)` / `get_scene_state(name)`.

### Scene Base (`scenes/scene.py`)

```python
enter(**kwargs)      # Called when scene becomes active
exit()               # Called when leaving a scene
handle_events(event) # Process pygame events
update(*args)        # Update game state
render(surface)      # Draw to screen
```

### Entity System

```
Entity (entities/base.py)  — rect, collision_rect, active
  +-- Player (player.py)
  +-- Enemy (enemy.py) — 6 movement patterns: straight, sine, zigzag, dive, hover, spiral
        +-- Boss (enemy.py) — phase-based attacks
  +-- Bullet (bullet.py)
```

### Data Flow: Input → Game Loop

```
PygameInputHandler → InputCoordinator → GameScene.handle_events()
                                             ↓
                              GameController (gameplay state machine)
                                             ↓
                              Managers → Systems → Rendering
```

### Game State Machine

```
PLAYING → DYING → GAME_OVER
   ^        |
   |________|  (on death animation complete)
```

### Important Design Decisions

- **`game/constants.py`** — All tuning values in a single `GameConstants` dataclass (player stats, damage values, timing, animation, balance). Edit here for game balance.
- **`config/design_tokens.py`** — Visual design system: color themes (`Colors`, `SystemColors`, `SceneColors`), typography, spacing.
- **`config/game_config.py`** — `GameConfig` singleton with adaptive screen sizing.
- **Rust native code always has a pure-Python fallback** — checked via `RUST_AVAILABLE` flag in `core_bindings.py`.
- **Coding standards** — Full guide at `docs/REFACTORING_GUIDE.md`: naming conventions, import conventions, class method ordering, and docstring requirements.

### Game Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move ship |
| Space | Fire |
| ESC | Pause |
| H (hold) | Dock with mothership to save progress |
| K (hold 3s) | Surrender |

### Coding Standards

See `docs/REFACTORING_GUIDE.md` for full conventions and `docs/MAINTENANCE_GUIDE.md` for maintenance procedures. Key rules:

**Imports (priority order):**
1. Same package, same layer → relative: `from .base import Entity`
2. Same package, different layer → relative: `from ..config import settings`
3. Different package (including airwar subpackages) → absolute: `from airwar.config import SCREEN_WIDTH`
4. Stdlib/third-party → absolute: `import pygame`

**Class method order:**
```
1. Special methods (__init__, __repr__)
2. Properties (@property)
3. Lifecycle methods (enter, exit, update, render)
4. Public behavior (fire, take_damage)
5. Private lifecycle (_init_movement, _setup_weapons)
6. Private behavior (_update_movement)
7. Helper methods (_calculate_damage)
```

**Docstrings:** English, Google style, required for all public classes and methods.

**Local imports in methods:** Prohibited except for optional dependencies or breaking circular imports.

**Glow circle rendering:** `draw_glow_circle` uses pygame fallback only. Rust `create_glow_circle` exists in `sprites.rs` but is not used for rendering.

### MotherShip Subsystem — Interface-Driven Architecture

The mothership docking/save system uses an interface-driven design with 6 ABCs in `game/mother_ship/interfaces.py`:

| Interface | Role |
|-----------|------|
| `IInputDetector` | Docking input detection (hold-H) |
| `IMotherShipUI` | Mothership visual state display |
| `IEventBus` | Publish/subscribe for cross-system events |
| `IPersistenceManager` | Save/load game state (JSON) |
| `IMotherShipStateMachine` | Docking state machine (`IDLE → PRESSING → DOCKING → DOCKED → UNDOCKING → COOLDOWN`) |
| `IGameScene` | Contract for `GameIntegrator` to access `GameScene` without layer violations (30+ methods: score, health, buffs, enemies, etc.) |

**Mothership visual:** Large capital-class vessel (cold-steel-blue, ~430px wingspan), swept-back wings, bridge tower with cyan glass canopy, underside docking bay with pulsing guide lights. Rendered via `draw_glow_circle` and multi-layer polygon hull.

**Docking flow:**
1. Hold H 3s → `DOCKING` animation (90f ease-in-out-cubic) — player smoothly pulled to docking bay, silent invincibility + controls locked
2. `DOCKED` (20s) — player rides inside mothership, mothership fires **explosive missiles** (250 damage, 80px AoE radius, 5 targets, ~3.3 shots/sec), full game loop continues (enemies spawn, boss timer advances)
3. Stay expired → `UNDOCKING` two-phase: Phase 1 ejects player backward (30f), Phase 2 mothership accelerates upward off-screen (60+f)

**Mothership movement:** WASD/arrows, only during DOCKED state. No inertial friction — direct response. Starts fixed at screen center.

**Invincibility:** Uses `silent_invincible` flag during docking to suppress the standard damage-blink visual effect. Player `controls_locked` prevents movement and auto-fire while docked.

### Other Key Subsystems

| Subsystem | Location | Responsibility |
|-----------|----------|----------------|
| GameController | `game/managers/game_controller.py` | Game state, scoring, milestones, difficulty level |
| SpawnController | `game/managers/spawn_controller.py` | Enemy wave spawning |
| CollisionController | `game/managers/collision_controller.py` | Entity collision (can use Rust spatial hash) |
| BulletManager | `game/managers/bullet_manager.py` | Player/enemy bullet pools |
| BossManager | `game/managers/boss_manager.py` | Boss spawn and phase transitions |
| MilestoneManager | `game/managers/milestone_manager.py` | Score thresholds → reward triggers |
| GiveUp | `game/give_up/` | Hold-K-3s surrender flow |
| UserDB | `utils/database.py` | User stats (high score, kills, games played) |

### Rendering Pipeline

Pure pygame rendering (no GPU/ModernGL). The rendering pipeline draws in order:
Parallax starfield background → Entities → Bullets → HUD → Notifications → Pause button → MotherShip → Explosions → GiveUp UI → **Reward Selector (topmost)**

### Enemy Movement

8 movement patterns in `entities/movement_strategies.py` and `airwar_core/src/movement.rs`:
- **Entry:** Ease-out quad deceleration into position
- **Active transition:** First 15 frames blend from static target to full pattern amplitude (ease-in quad)
- **Zigzag fix:** Y-axis oscillation uses `_lifetime` (non-resetting timer) instead of `zigzag_timer` to prevent 6-25px frame jumps
- Python `_smooth_noise` corrected to match Rust interpolation (`int_x + 1` ceiling, not `int_x + frac_x`)

### Window / Fullscreen

`window/window.py` — `pygame.FULLSCREEN` (without `SCALED`) for fullscreen mode. `SCALED` causes cropped viewport on pygame 2.6+ X11/Wayland backends. `SCALED` retained for windowed resize mode.

---

## 语言偏好

- **所有回复使用中文** — 代码注释、文档、审查报告等所有面向人类的文字输出均使用中文
