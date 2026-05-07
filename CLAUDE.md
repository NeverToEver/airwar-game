# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Air War** is a 2D space shooter game built with Python + Pygame. Players control a spaceship, fight enemies, collect buffs, and dock with a mothership to save progress. Rust extension module (`airwar_core`) provides performance-critical computation.

### Tech Stack

- Python 3.x + Pygame + Pillow
- Rust (PyO3 0.22 / maturin 1.0) -- `airwar_core` extension module
- Architecture: Scene Pattern, Manager Pattern, Observer Pattern

### Key Numbers

- Default resolution: 1920x1080, FPS=60
- Player speed: 7 (base), ~12 with boost
- Player bullet speed: 14
- Test suite: ~200 test cases across 25 files, <2s runtime

---

## Commands

### Python Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # tests/build tooling
```

### Run the Game

```bash
python3 main.py
```

### Test

```bash
# All tests
python3 -m pytest

# Lint
python3 -m ruff check .

# Smoke tests (core functionality)
python3 -m pytest -m smoke

# Exclude slow tests
python3 -m pytest -m "not slow"

# Specific test file
python3 -m pytest airwar/tests/test_core.py

# Specific test class/method
python3 -m pytest airwar/tests/test_core.py::TestPlayer -v

# Rust binding tests
python3 -m pytest tests/test_bullet_bindings.py
```

### Build Rust Extension

```bash
# Requires Rust toolchain (rustup) + virtualenv for maturin develop
cd airwar_core && maturin develop --release

# Fallback: build wheel then pip install (no virtualenv needed)
cd airwar_core && maturin build --release
pip install --force-reinstall target/wheels/airwar_core-*.whl
```

### Build Standalone Executable

```bash
# Linux
bash build_linux.sh

# macOS
bash build_macos.sh

# Windows (in command prompt)
build_windows.bat
```

Build output at `dist/AirWar` (~40MB standalone executable with Python runtime + Rust extension when available). Requires Python 3.11+ and a platform compiler. Build scripts use `.venv-build/` during packaging and remove it by default unless `AIRWAR_KEEP_BUILD_VENV=1` is set.

### Test Configuration

Config at `pytest.ini` -- defaults: `-q --tb=short`. Markers: `smoke` (core), `slow` (integration/performance). Fixtures live under `airwar/tests/conftest.py`. Some tests require `pygame.init()`.

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

**Location:** `airwar_core/` -- Rust workspace with Cargo.

**Modules:**

| Module | Functions | Python binding |
|--------|-----------|----------------|
| `vector2.rs` | vec2_length, normalize, add, sub, dot, cross, scale, distance, angle, lerp, clamp_length (14 functions) | `core_bindings.py` |
| `collision.rs` | spatial_hash_collide, spatial_hash_collide_single, batch_collide_bullets_vs_entities, PersistentSpatialHash | `core_bindings.py` |
| `movement.rs` | update_movement, batch_update_movements, compute_boss_attack (8 types: straight, sine, zigzag, dive, hover, spiral, noise, aggressive) | `core_bindings.py` |
| `particles.rs` | update_particle, batch_update_particles, generate_explosion_particles | `core_bindings.py` |
| `sprites.rs` | create_single_bullet_glow, create_spread_bullet_glow, create_laser_bullet_glow, create_explosive_missile_glow, create_glow_circle | `core_bindings.py` |
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
**Tests:** Python tests at `tests/test_*_bindings.py` exercise installed Rust bindings. The current checkout includes bullet binding coverage; no Rust-side test framework is configured.

---

## Architecture

### Package Structure

Source code lives under `airwar/` (Python package). Entry point: `main.py` (project root).

```
airwar-game/                  # Project root
|-- main.py                  # Entry: python3 main.py
|-- airwar/                  # Python package (all source)
|??   |-- config/              # Settings, game_config, design_tokens, difficulty_config
|??   |-- entities/            # Entity base, Player, Enemy (+ Boss subclass), Bullet
|??   |-- game/
|??   |??   |-- game.py          # Game class -- window, SceneManager, SceneDirector, scene registration
|??   |??   |-- scene_director.py # Welcome->Game orchestration
|??   |??   |-- constants.py     # GameConstants dataclass (all tuning constants)
|??   |??   |-- managers/        # GameController, SpawnController, CollisionController, BulletManager,
|??   |??   |??                    # BossManager, MilestoneManager, InputCoordinator, UIManager, GameLoopManager
|??   |??   |-- controllers/     # Reserved for subsystem controllers (currently unused)
|??   |??   |-- spawners/        # EnemyBulletSpawner
|??   |??   |-- systems/         # HealthSystem, RewardSystem, NotificationManager, DifficultyManager,
|??   |??   |??                    # MovementPatternGenerator, TalentBalanceManager, DifficultyStrategies
|??   |??   |-- rendering/       # GameRenderer, HUDRenderer, IntegratedHUD
|??   |??   |-- buffs/           # 13 buff types (health, offense, defense, utility)
|??   |??   |-- mother_ship/     # Dock/save: state machine, persistence (JSON), event bus, interfaces, GameIntegrator
|??   |??   |-- give_up/         # Surrender system (hold-K detector)
|??   |??   |-- homecoming/      # Return-to-base: detector, animated sequence (FTL->base->orbital strike)
|??   |??   |-- explosion_animation/
|??   |??   |-- death_animation/
|??   |-- scenes/              # Scene base, 5 scenes: welcome, game, pause, death, exit_confirm
|??   |-- ui/                  # GameHUD (integrated HUD), reward_selector, buff_stats, chamfered_panel,
|??   |??                        # hex_icon, segmented_bar, game_over_screen, give_up_ui, effects, menu_background,
|??   |??                        # discrete_battery, liquid_health_tank, ammo_magazine, warning_banner, boost_gauge,
|??   |??                        # aim_crosshair, homecoming_ui, base_talent_console, difficulty_coefficient_panel
|??   |-- input/               # PygameInputHandler
|??   |-- utils/               # UserDB, mouse_interaction mixins, sprites, responsive
|??   |-- window/              # Resizable window management
|??   |-- data/                # Legacy runtime data location; current saves use platform user data dirs
|??   |-- tests/               # pytest suite
|??   |-- core_bindings.py     # Rust->Python bridge with fallback
|-- airwar_core/             # Rust PyO3 extension (maturin)
|-- tests/                   # Root-level Rust binding tests (test_bullet_bindings.py)
|-- docs/                    # Rust perf plan, superpower specs, audit reports, REFACTORING_GUIDE
|-- plans/                   # Implementation plans
|-- requirements.txt
```

### Scene Flow

```
WelcomeScene -> GameScene
                 |-- PauseScene (ESC)
                 |-- DeathScene (player death)
                 |-- ExitConfirmScene (quit)
```

`WelcomeScene` combines login, difficulty selection, and quick controls reference in a single side-by-side page, replacing the previous separate LoginScene + MenuScene + TutorialScene flow. `SceneDirector` orchestrates transitions and state preservation. `SceneManager` supports `save_scene_state(name, state)` / `get_scene_state(name)`.

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
Entity (entities/base.py)  -- rect, collision_rect, active
  +-- Player (player.py)
  +-- Enemy (enemy.py) -- 6 movement patterns: straight, sine, zigzag, dive, hover, spiral
        +-- Boss (enemy.py) -- phase-based attacks
  +-- Bullet (bullet.py)
```

### Data Flow: Input -> Game Loop

```
PygameInputHandler -> InputCoordinator -> GameScene.handle_events()
                                             v
                              GameController (gameplay state machine)
                                             v
                              Managers -> Systems -> Rendering
```

### Game State Machine

```
PLAYING -> DYING -> GAME_OVER
   ^        |
   |________|  (on death animation complete)
```

### Game Loop Update Order

Exact per-frame execution order in `GameScene.update()`:

1. Reward selector update, talent console update (if at base)
2. Raw mouse position capture + aim assist + crosshair update
3. **Homecoming system update** (detector + sequence)
4. HUD scroll/health update
5. **Early return if homecoming active** -- skips all gameplay logic
6. Entrance animation (if playing) -- mothership update only
7. Death animation (if dying) -- game loop update + mothership update only
8. Warning banner scroll animation
9. **Pause check** -- skip remaining if paused or reward selector visible
10. Mothership integrator update + ammo warning
11. GiveUp detector update
12. **GameLogic update** (`_update_core`): GameController -> death anim -> explosion -> player (with boss-enrage control lock) -> bullets -> enemy spawn -> entities -> boss -> cleanup
13. Docking position lock (if docked)
14. Phase dash invincibility sync
15. **Collision detection** (`check_collisions`): player bullets vs enemies/boss, enemy bullets vs player, boss vs player
16. **Post-collision cleanup**: ensures entities killed during collision are removed before milestone check
17. **Milestone check** (`check_and_trigger`)
18. Auto-save (periodic, when not docked)

**Key design:** The post-collision cleanup (step 16) prevents entities from persisting during pause -- if a boss is killed during collision and immediately triggers reward pause, the dead boss would linger until next frame's cleanup, causing it to "vanish" after unpausing.

### Important Design Decisions

- **`game/constants.py`** -- All tuning values in a single `GameConstants` dataclass (player stats, damage values, timing, animation, balance). Edit here for game balance.
- **`config/design_tokens.py`** -- Visual design system: color themes (`Colors`, `SystemColors`, `SceneColors`), typography, spacing.
- **`config/game_config.py`** -- `GameConfig` singleton with adaptive screen sizing.
- **Rust native code always has a pure-Python fallback** -- checked via `RUST_AVAILABLE` flag in `core_bindings.py`.
- **Coding standards** -- Full guide at `docs/REFACTORING_GUIDE.md`: naming conventions, import conventions, class method ordering, and docstring requirements.

### Game Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move ship (speed 7 base, ~12 with boost) |
| Mouse | Aim control -- auto-aim assist snaps to nearest enemy; large mouse movements override |
| Shift (hold) | Boost -- consumes energy, +70% speed; press-release activates Phase Dash (if unlocked) |
| Auto-fire | Ship fires automatically (no manual fire key) |
| ESC | Pause |
| H (hold 3s) | Dock with mothership to save progress |
| K (hold 3s) | Surrender (give up current run) |
| B (hold 2.4s) | Homecoming -- FTL return to base for resupply and talent reconfiguration |
| L | Toggle HUD expanded/collapsed |

### Coding Standards

See `docs/REFACTORING_GUIDE.md` for full conventions and `docs/MAINTENANCE_GUIDE.md` for maintenance procedures. Key rules:

**Imports (priority order):**
1. Same package, same layer -> relative: `from .base import Entity`
2. Same package, different layer -> relative: `from ..config import settings`
3. Different package (including airwar subpackages) -> absolute: `from airwar.config import SCREEN_WIDTH`
4. Stdlib/third-party -> absolute: `import pygame`

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

### MotherShip Subsystem -- Interface-Driven Architecture

The mothership docking/save system uses an interface-driven design with 6 ABCs in `game/mother_ship/interfaces.py`:

| Interface | Role |
|-----------|------|
| `IInputDetector` | Docking input detection (hold-H) |
| `IMotherShipUI` | Mothership visual state display |
| `IEventBus` | Publish/subscribe for cross-system events |
| `IPersistenceManager` | Save/load game state (JSON) |
| `IMotherShipStateMachine` | Docking state machine (`IDLE -> PRESSING -> DOCKING -> DOCKED -> UNDOCKING -> COOLDOWN`) |
| `IGameScene` | Contract for `GameIntegrator` to access `GameScene` without layer violations (30+ methods: score, health, buffs, enemies, etc.) |

**Mothership visual:** Large capital-class vessel (cold-steel-blue, ~430px wingspan), swept-back wings, bridge tower with cyan glass canopy, underside docking bay with pulsing guide lights. Rendered via `draw_glow_circle` and multi-layer polygon hull.

**Docking flow:**
1. Hold H 3s -> `DOCKING` animation (90f ease-in-out-cubic) -- player smoothly pulled to docking bay, silent invincibility + controls locked. **Mothership provides cover fire during docking animation.**
2. `DOCKED` (20s) -- player rides inside mothership, mothership fires **explosive missiles** (250 damage, 80px AoE radius, 5 targets, ~3.3 shots/sec), full game loop continues (enemies spawn, boss timer advances)
3. Stay expired -> `UNDOCKING` two-phase: Phase 1 ejects player backward (30f), Phase 2 mothership accelerates upward off-screen (60+f)

**Mothership movement:** WASD/arrows, only during DOCKED state. No inertial friction -- direct response. Starts fixed at screen center.

**Invincibility:** Uses `silent_invincible` flag during docking to suppress the standard damage-blink visual effect. Player `controls_locked` prevents movement and auto-fire while docked.

**Save data fields:** Player position (x, y), score, kills, boss_kills, health, max_health, buff levels, difficulty, username, is_in_mothership flag. All buff effects are re-applied after load via `_reapply_buff_effects()`. Legacy saves without player position default to bottom-center screen.

**Ammo Magazine & Warning Banner:** `ui/ammo_magazine.py` renders 10-cell ammo indicator to the left of the mothership during docking, with a `WARNING_CELL_THRESHOLD = 3` constant controlling when bottom cells turn red. `ui/warning_banner.py` displays a slide-in "AMMO DEPLETED" alert panel (550ms enter -> 4s hold -> 450ms exit -> callback). `WarningBanner.activate()` returns `bool` -- `True` on success, `False` if already active. `GameIntegrator.get_status_data()` computes `ammo_count`, `ammo_max`, and `ammo_warning` fields.

**GameIntegrator public API:**
- `request_undock()` -- publish `UNDOCK_REQUESTED` to internal event bus (GameScene calls this instead of accessing private `_event_bus`)
- `MotherShipStateMachine.force_state(state)` -- force-set state for save/restore (bypasses transition validation)
- `InputDetector.reset_progress()` -- reset docking hold progress for save/restore

### Homecoming System -- Return to Base

**Location:** `game/homecoming/` (detector + sequence), `ui/homecoming_ui.py`, `ui/base_talent_console.py`.

Hold B for 2.4s to trigger an animated FTL return to the home base. Only available when: playing, not paused, not docked, not in reward selection, not in entrance animation, and no active homecoming sequence.

**Sequence phases** (`HomecomingSequence`):
1. `FTL_ESCAPE` (54f) — player accelerates upward with particle trail
2. `BLACKOUT` (34f) — screen fades to black
3. `STATION_REVEAL` (70f) — base station fades in
4. `APPROACH` (96f) — camera pans toward landing pad
5. `LANDING` (72f) — player descends to landing position
6. `HANDOFF` (64f) — transition to base interior
7. **Base console** — `BaseTalentConsole` renders talent loadout, resupply button, and departure controls

**Departure** (B key again or "Continue"):
1. `BASE_LAUNCH` (76f) — player catapulted from base
2. `RETURN_BLACKOUT` (34f) — screen fades
3. `ORBITAL_STRIKE` (86f) — clears all enemies on screen (strike triggers at 56% progress)
4. Player returns to battlefield at previous position

**During homecoming:** Gameplay is locked — pause, reward selection, and all game logic are blocked. Player is invincible. All enemy bullets and player bullets are cleared. Auto-save triggers on base entry.

**Base console actions:**
- **Resupply** — restore health and boost to full, save loadout
- **Talent route switching** — toggle between offense/support route options (see Talent/Loadout System)
- **Continue** — depart base and return to combat

`HomecomingDetector` mirrors the pattern of `InputDetector` (hold-H for mothership), using a 2.4s hold on B key.

### Health Indicator -- Discrete Battery

**Location:** `ui/discrete_battery.py`, integrated via `IntegratedHUD` in `rendering/integrated_hud.py`.

Segmented discrete health indicator replacing the old liquid-style health tank:
- **Vertical mode (collapsed panel):** ~36x?350px, 30 segments, bottom-aligned in panel
- **Horizontal mode (expanded panel):** 24px tall, 30 segments inside dark rounded bar, ~85% panel width
- **Color:** All active segments same color -- green (>50%), amber (25-50%), red (<25%)
- **Empty segments:** Dark gray `(12, 12, 14)`, thin border frame hints at total capacity
- **Pixel-precise fill:** remainder distribution ensures segments exactly fill the frame at 100% health

**Liquid Health Tank:** `ui/liquid_health_tank.py` -- glass-canister style alternative health display with spring-physics liquid animation and wave surface effects. Used alongside the discrete battery for visual variety. Key features: spring-driven level transitions (k=8.0, damping=3.5), color interpolation across 4 stops (green->amber->orange->red), bubble particle system, pre-rendered steel-housing and glass-frame caches. Caches are split into true-static (frame, steel_bg) and per-frame-rebuilt (liquid_surf).

### Boost System

**Location:** `entities/player.py` (state), `ui/boost_gauge.py` (UI), `config/settings.py` (BOOST_CONFIG).

Boost energy mechanic:
- **Activation:** Hold Shift key
- **Consumption:** 1 unit/frame while active (no movement required)
- **Speed multiplier:** 1.7x? base speed via `player.boost_speed_mult`
- **Recovery:** 1.5s delay after release -> 2s ramp from 15% to 100% rate
- **Capacity (per difficulty):** Easy=300, Medium=200, Hard=120
- **Recovery rate:** Easy=1.2, Medium=1.0, Hard=0.8 units/frame

**Boost Gauge UI:** 270 ? arc gauge (speedometer-style), 31 tick marks, pointer needle. Bottom-left position at `(108, screen_h - 98)`, radius 80px, panel 200x?180 (compact mini version). Military cockpit aesthetic: steel-blue arc, ACCENT_TEAL lit ticks, WARNING-red needle when active.

**Boost Recovery Buff:** `BoostRecoveryBuff` in `game/buffs/buffs.py` -- multiplies `player.boost_recovery_rate` by 1.5. Registered in `buff_registry.py`, reward pool entry in `reward_system.py`.

### Phase Dash

**Location:** `entities/player.py` (state machine), unlocked via "Phase Dash" talent buff.

Invincible dash triggered by pressing Shift (just-pressed, not hold):
- **Cost:** 25% of max boost energy (`PHASE_DASH_COST_RATIO = 0.25`)
- **Distance:** 250px in movement direction (minimum 120px), clamped to screen bounds
- **Phases:** windup (5f) → active (14f) → recovery (8f)
- **Cooldown:** 90 frames after activation
- **Visual:** Alpha pulse between 75–165 during dash, color-cycled sprite
- **Invincibility:** `is_phase_dash_invincible()` returns True during windup/active/recovery

When phase dash is active, normal boost consumption is blocked for that frame. Phase dash uses `boost_current` for fuel. If Phase Dash talent is not unlocked (`player.phase_dash_enabled = False`), pressing Shift falls through to normal boost behavior.

### Weapon Modes

**Location:** `entities/player.py`.

Two weapon modifiers that can be activated individually or combined:

- **Spread Shot** (`_has_spread`): Fires 3 bullets in a fan pattern (-10?, 0?, +10?). Bullet type becomes `'spread'` (or `'spread_laser'` if combined with laser).
- **Laser** (`_has_laser`): Upgrades bullet type to `'laser'` with higher damage (35 vs 10 base). When combined with spread, produces `'spread_laser'` bullets.

Weapon modes are set via `player.set_weapon_modifiers(spread, laser, explosive)` and exposed via `player.get_weapon_status()`. Both modes are granted through the reward system as talent buffs and are subject to route exclusivity in the talent loadout system.

### Talent / Loadout System

**Location:** `game/systems/talent_balance_manager.py`, `ui/base_talent_console.py`.

Two exclusive talent routes, each with two mutually-exclusive options:

| Route | Options | Effect |
|-------|---------|--------|
| **Offense** (`weapon route`) | Spread Shot vs Laser | Bullet pattern vs damage upgrade |
| **Support** (`mobility route`) | Phase Dash vs Mothership Recall | Invincible dash vs mothership cooldown -50% |

**Mechanics:**
- Player earns buff levels through the reward system (milestone pickups)
- `TalentBalanceManager` calculates effective levels: total earned points in a route are assigned entirely to the selected option; the unselected option gets level 0 ("locked")
- Route budget = sum of earned levels for both options in the route
- If budget is 0 (neither option ever picked), the route is locked
- Player switches selected option via the base talent console during homecoming
- Loadout is persisted in save data via `reward_system.talent_loadout`

**Mothership Recall** (`_apply_mothership_recall`): Sets `player.mothership_cooldown_mult = 0.5 ** level` — at level 1, cooldown is halved; at level 2, quartered.

### Aim Assist & Crosshair

**Location:** `entities/player.py` (aim logic), `ui/aim_crosshair.py` (visual).

Mouse-driven aiming with two-layer target selection:
1. **Auto-aim assist** — snaps aim toward the nearest enemy within range
2. **Mouse override** — large mouse movements (>threshold) switch to the enemy nearest to cursor direction, giving manual control feel
3. **Smoothing** — raw mouse input is delayed/smoothed to reduce jerkiness during assist transitions

**Aim crosshair** (`AimCrosshair`): Renders a modern crosshair at the mouse position with:
- Outer lines (14px) with center gap (8px), inner ring (radius 5px)
- Pulsing glow ring via `sin` oscillation
- Uses `ACCENT_BRIGHT` / `ACCENT_DIM` colors from design tokens

### Difficulty Strategies

**Location:** `game/systems/difficulty_strategies.py`.

Strategy pattern for difficulty scaling — each difficulty level is a concrete strategy class:

| Strategy | Growth Rate | Base Mult | Max Mult | Speed Bonus | Fire Rate Bonus |
|----------|------------|-----------|----------|-------------|-----------------|
| `EasyStrategy` | 0.5 | 0.8 | 3.0 | 0.1 | 0.15 |
| `MediumStrategy` | 1.0 | 1.0 | 5.0 | 0.2 | 0.25 |
| `HardStrategy` | 1.5 | 1.2 | 8.0 | 0.35 | 0.4 |

These strategies control how enemy stats scale over time: `growth_rate` determines how fast stats increase, `base_multiplier` sets the starting scaling factor, and `max_multiplier` caps it. `speed_bonus` and `fire_rate_bonus` control enemy movement speed and firing frequency scaling respectively.

### Performance Optimizations

**Surface/font caching:**
- `game_rendering_background.py`: StarLayer and DustLayer glow surfaces cached by `(radius, alpha)` key -- eliminates ~400 SRCALPHA allocations/frame
- `integrated_hud.py`: Font objects cached via `_get_font(size)`, arrow/hint text pre-rendered -- eliminates ~12 `font.Font()` calls/frame
- `_sprites_ships.py`: `_code_hash` uses `@functools.lru_cache` -- MD5 computed once per function, not per frame per entity

**Batch Rust acceleration:**
- `game_loop_manager.py`: `batch_update_movements` called once/frame for all 'active' state enemies, results distributed via `_batch_result` attribute -- replaces 5-8 individual FFI calls
- `collision_controller.py`: `batch_collide_bullets_vs_entities` replaces PersistentSpatialHash with single FFI call -- eliminates 40 per-frame hash updates + O(N ?) pair enumeration

**Hot path micro-optimizations:**
- `bullet.py`: Trail stores `(x,y,w,h)` tuples instead of `pygame.Rect`, deque iterated directly (no `list()` copy), `maxlen` handles eviction
- `bullet_manager.py`: `_cleanup_enemy_bullets` fast-paths with `any()` -- most frames skip list allocation
- `enemy.py`: Timer read/write uses pre-computed `_timer_attr` string with `setattr`, batch movement params pre-computed in `_init_movement`

**Surface caching (new):**
- `boost_gauge.py`: Arc track and dim ticks cached as pre-rendered `_arc_cache` layer -- eliminates ~60 `pygame.draw.line`/`pygame.draw.arc` calls per frame, recalculated only on resize
- `mother_ship.py`: Phantom preview surface (`_phantom_surf`) cached by screen size -- eliminates full-screen SRCALPHA allocation per frame during phantom rendering
- `game_rendering_background.py`: Gradient surface converted once with `.convert()` and cached globally -- avoids redundant surface conversion
- `_sprites_common.py`: `convert_alpha()` wrapped in try/except for pygame error resilience
- `ammo_magazine.py`: Frame background cached by `(fw, fh)` key -- eliminates per-frame rounded rect + rivet draws
- `warning_banner.py`: Banner background cached by `(screen_w,)` key -- eliminates per-frame hazard stripe + tech bracket poly draws
- `liquid_health_tank.py`: Steel housing and glass frame are truly static caches (never invalidated); liquid layer rebuilt per frame as a local Surface for correct clip-blit semantics

**Spawn tuning:**
- `ENEMIES_PER_FRAME = 2` (was 3) -- wave spawns spread across 6 frames
- Entry animation: `0.04`/frame (25 frames, was 50)
- Exit animation: `0.03`/frame (33 frames, was 67)
- Spawn data uses tuples not dicts

### Boss System

**Movement:** 4-phase lerp-based system in `Boss._select_next_target()`:
- PATROL: horizontal to opposite side with vertical drift
- SWEEP: diagonal to random zone
- HOVER: local  ?130px X,  ?80px Y repositioning
- CHASE: drift toward player area with random offset
- Lerp factor: `0.025 x? speed`, smooth exponential deceleration
- Y range: 50 to `screen_h // 2 + 60`

**Boss spawn:** `SpawnController.spawn_boss()` forces all active enemies into 'exiting' state before creating boss.

**Boss timer:** `_render_boss_timer()` in `hud_renderer.py` -- styled panel below health bar, 32px font, color transitions steel-blue->amber->red as time runs low, pulsing "ESCAPING!" warning when >70% elapsed.

**Boss enrage:** When boss HP drops below 30%, enters enrage state:
- Screen-distortion overlay (`_render_boss_enrage_overlay`) — horizontal scan-line bands with sine-wave displacement, intensity proportional to enrage progress
- Player controls locked during enrage activation (`_should_lock_player_for_boss_enrage`)
- Boss fires denser patterns with shorter intervals
- Visual intensity computed via `boss.enrage_visual_intensity()`

### Hit Response

**`_on_player_damaged()`** in `game_scene.py`:
1. Applies damage via `GameController.on_player_hit()`
2. **Clears all enemy bullets** via `BulletManager.clear_enemy_bullets()`
3. Invincibility activates (90 frames standard, or until death animation completes)

### Other Key Subsystems

| Subsystem | Location | Responsibility |
|-----------|----------|----------------|
| GameController | `game/managers/game_controller.py` | Game state, scoring, milestones, difficulty level |
| SpawnController | `game/managers/spawn_controller.py` | Enemy wave spawning |
| CollisionController | `game/managers/collision_controller.py` | Entity collision (can use Rust spatial hash) |
| BulletManager | `game/managers/bullet_manager.py` | Player/enemy bullet pools |
| BossManager | `game/managers/boss_manager.py` | Boss spawn and phase transitions |
| MilestoneManager | `game/managers/milestone_manager.py` | Score thresholds -> reward triggers |
| GiveUp | `game/give_up/` | Hold-K-3s surrender flow |
| UserDB | `utils/database.py` | User stats (high score, kills, games played) |

### Rendering Pipeline

Pure pygame rendering (no GPU/ModernGL). The rendering pipeline draws in order:
Parallax starfield background -> Entities -> Bullets -> HUD (DiscreteBattery / LiquidHealthTank) -> Buff stats -> Pause button -> **BoostGauge (bottom-left)** -> **AmmoMagazine + WarningBanner (mothership)** -> MotherShip -> **Boss enrage overlay** -> Explosions -> GiveUp UI -> **Homecoming progress** -> **Aim crosshair** -> **Homecoming sequence animation** -> **Base talent console** (if at base) -> **Reward Selector** -> **Notifications (topmost)**

The aim crosshair renders above most elements for visibility. Notifications are topmost so critical messages (boss escape, kill score) are never obscured.

### Enemy Movement

8 movement patterns in `entities/movement_strategies.py` and `airwar_core/src/movement.rs`:
- **Entry:** Ease-out quad deceleration into position
- **Active transition:** First 15 frames blend from static target to full pattern amplitude (ease-in quad)
- **Zigzag fix:** Y-axis oscillation uses `_lifetime` (non-resetting timer) instead of `zigzag_timer` to prevent 6-25px frame jumps
- Python `_smooth_noise` corrected to match Rust interpolation (`int_x + 1` ceiling, not `int_x + frac_x`)

### Window / Fullscreen

`window/window.py` -- `pygame.DOUBLEBUF` for both windowed and fullscreen modes. `SCALED` removed entirely (causes cropped viewport on pygame 2.6+ X11/Wayland backends). Uses `tick_busy_loop` for accurate frame timing. Fullscreen uses `pygame.FULLSCREEN` flag.

---

## CI (GitHub Actions)

**Workflow:** `.github/workflows/ci.yml` — triggers on `push` and `pull_request`, single job on `ubuntu-latest`.

**Steps (in order):** checkout → setup Python 3.12 (with pip cache) → setup Rust stable → cache Cargo → install `libsdl2-dev` + `shellcheck` → pip install `requirements-dev.txt` → `maturin build --release` + pip install wheel → `ruff check .` → `python -m compileall` → `shellcheck` build scripts → `pytest`

**CI config:** `timeout-minutes: 15`, `concurrency` with `cancel-in-progress: true`.

### CI Validation (run locally before pushing)

```bash
# Ruff lint (same as CI)
python3 -m ruff check .

# Bytecode compilation check (same as CI)
python3 -m compileall -q airwar main.py

# Build script syntax (same as CI)
bash -n build_linux.sh && bash -n build_macos.sh

# Run tests in CI-like headless mode
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m pytest
```

### CI-Specific Gotchas

- **`SDL_VIDEODRIVER` env var:** CI uses `SDL_VIDEODRIVER` (VIDEO + DRIVER, no underscore). This is the SDL2 standard name — if CI tests fail with "no video device", verify this var is set to `dummy`.
- **Rust extension is mandatory in CI:** Unlike local dev (which gracefully falls back to pure Python), CI builds and installs `airwar_core` wheel before running tests. If Rust build fails, CI fails.
- **`libsdl2-dev` required:** Pygame needs SDL2 system headers for the dummy video driver to work in headless CI.

---

## Language Preference

- **All responses in English** -- code comments, documentation, review reports, and all human-facing text output should use English to avoid character encoding issues (garbled text / luan ma) across different OS locales and terminal configurations.
