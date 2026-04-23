# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Air War (飞机大战)** is a 2D space shooter game built with Python + Pygame. Players control a spaceship, fight enemies, collect buffs, and dock with a mothership to save progress.

### Tech Stack

- Python 3.x + Pygame + Pillow
- Architecture: Scene Pattern, Manager Pattern, Observer Pattern

---

## Commands

### Installation

```bash
pip install -r requirements.txt
```

### Running the Game

```bash
python main.py
```

### Testing

```bash
# Run all tests
cd airwar && python -m pytest

# Run only smoke tests (core functionality)
cd airwar && python -m pytest -m smoke

# Exclude slow tests
cd airwar && python -m pytest -m "not slow"

# Run a specific test file
cd airwar && python -m pytest tests/test_game_scene_pause_button.py

# Run a specific test with verbose output
cd airwar && python -m pytest tests/test_entities.py::TestPlayer -v
```

---

## Game Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Move spaceship |
| Space | Fire weapon |
| ESC | Pause game |
| H (hold) | Dock with mothership to save |
| K (hold 3 seconds) | Surrender |

---

## Architecture

### Scene Pattern

The game uses a **Scene-based architecture** with `SceneManager` and `SceneDirector`.

#### Scene Flow

```
LoginScene -> MenuScene -> GameScene
                           |
                           +-> PauseScene (ESC)
                           |
                           +-> DeathScene (game over)
                           |      |
                           |      +-> MenuScene (restart)
                           |
                           +-> ExitConfirmScene (quit from pause)
                           |
                           +-> TutorialScene (from menu)

SceneDirector orchestrates this flow, handling transitions and state preservation.
```

#### Available Scenes

| Name | File | Description |
|------|------|-------------|
| `login` | `login_scene.py` | User authentication |
| `menu` | `menu_scene.py` | Main menu (new game, continue, settings, tutorial, quit) |
| `game` | `game_scene.py` | Main gameplay (coordinates all subsystems) |
| `pause` | `pause_scene.py` | Pause overlay (resume, save, quit) |
| `death` | `death_scene.py` | Game over screen |
| `exit_confirm` | `exit_confirm_scene.py` | Exit confirmation dialog |
| `tutorial` | `tutorial_scene.py` | Interactive tutorial |

#### Scene Base Class

All scenes implement the `Scene` abstract base class:

```python
enter(**kwargs)      # Called when scene becomes active (kwargs for state transfer)
exit()               # Called when leaving a scene
handle_events(event) # Process pygame events
update(*args)        # Update game state
render(surface)      # Draw to screen
```

#### SceneManager

Manages scene registration and switching. Also supports state preservation:

```python
save_scene_state(name, state)  # Save state before switching
get_scene_state(name)           # Retrieve saved state
```

---

### Core Classes

| Class | Location | Responsibility |
|-------|----------|-----------------|
| `Game` | `game/game.py` | Entry point: creates window, SceneManager, SceneDirector, registers scenes |
| `SceneDirector` | `game/scene_director.py` | Orchestrates login -> menu -> game flow, manages game sessions |
| `GameScene` | `scenes/game_scene.py` | Main gameplay: coordinates subsystems, handles game loop |
| `GameController` | `game/managers/game_controller.py` | Game state, scoring, milestones, difficulty |
| `Player` | `entities/player.py` | Player ship with health, movement, shooting |
| `Enemy` | `entities/enemy.py` | Enemy ships with 6 movement patterns |
| `Boss` | `entities/enemy.py` | Boss with phase-based attacks |

---

### Game State Machine

Within `GameScene`, the `GameController` manages gameplay state:

```
PLAYING -> DYING -> GAME_OVER
   ^         |
   |_________| (on player death animation)
```

#### GameState Fields

```python
score: int              # Current score
score_multiplier: int   # Difficulty-based multiplier (easy=1, medium=2, hard=3)
paused: bool           # Pause flag
player_invincible: bool # Invincibility after taking damage
ripple_effects: list   # Visual effects queue
notification: str      # In-game notification text
entrance_animation: bool # Opening animation flag
gameplay_state: GameplayState  # PLAYING | DYING | GAME_OVER
```

---

### Key Subsystems

#### Managers (`game/managers/`)

| Manager | Purpose |
|---------|---------|
| `GameController` | Game state, scoring, milestones |
| `SpawnController` | Enemy wave spawning logic |
| `CollisionController` | Entity collision detection |
| `BulletManager` | Player/enemy bullet pools |
| `BossManager` | Boss spawning and phase transitions |
| `MilestoneManager` | Progress milestones, reward triggers |
| `InputCoordinator` | Keyboard/mouse coordination |
| `UIManager` | UI element management |
| `GameLoopManager` | Frame timing and delta time |

#### Systems (`game/systems/`)

| System | Purpose |
|--------|---------|
| `HealthSystem` | Player health, damage, regeneration |
| `RewardSystem` | Score calculation, multiplier |
| `NotificationManager` | In-game message display |
| `DifficultyManager` | Dynamic difficulty adjustment |

#### Rendering (`game/rendering/`)

- `GameRenderer` - Backgrounds, entities, explosions, ripples, MotherShip
- `HUDRenderer` - Score, health bar, milestone progress bar

---

### Entity System

#### Entity Base Class (`entities/base.py`)

```python
class Entity:
    rect            # Visual bounding box (pygame.Rect)
    collision_rect  # Smaller hitbox for collision detection
    active: bool    # Whether entity is alive
```

#### Class Hierarchy

```
Entity (base.py)
  +-- Player (player.py)
  +-- Enemy (enemy.py)
        +-- Boss (enemy.py)
```

#### Enemy Movement Types

| Type | Description |
|------|-------------|
| `straight` | Constant downward velocity |
| `sine` | Oscillating horizontal movement while descending |
| `zigzag` | Alternates horizontal direction at intervals |
| `dive` | Rapid acceleration toward player Y position |
| `hover` | Floats in fixed Y range |
| `spiral` | Combines rotation with descent |

---

### Input Handling

#### Architecture

```
PygameInputHandler (raw pygame events)
        |
        v
InputCoordinator (coordinates keyboard + mouse)
        |
        v
GameScene.handle_events()
```

#### Mouse Interaction Mixins (`utils/mouse_interaction.py`)

| Mixin | Use Case | Key Methods |
|-------|----------|-------------|
| `MouseSelectableMixin` | Menu option lists | `handle_mouse_motion()`, `handle_mouse_click()`, `append_option_rect()` |
| `MouseInteractiveMixin` | Button-based UI | `register_button()`, `is_button_hovered()`, `get_hovered_button()` |

#### Interaction Priority

1. Mouse hover overrides keyboard selection
2. Mouse click confirms hovered option
3. ESC maintains original behavior (back/cancel)

---

### MotherShip System (`game/mother_ship/`)

Dock with the mothership to save game progress.

#### Components

| Component | Purpose |
|-----------|---------|
| `MotherShip` | Visual representation, docking zone detection |
| `MotherShipStateMachine` | Docking progress states (searching, approaching, docking, saving) |
| `PersistenceManager` | Save/load game state to JSON |
| `EventBus` | Pub/sub for docking events |
| `ProgressBarUI` | Docking progress visualization |
| `InputDetector` | Detects H key hold for docking trigger |
| `GameIntegrator` | Connects MotherShip system to game state |

#### Docking Flow

1. Player holds H key
2. InputDetector triggers docking mode
3. MotherShip appears on screen
4. Player flies to docking zone
5. State machine progresses: searching -> approaching -> docking -> saving
6. ProgressBarUI shows save progress
7. Game state serialized to JSON via PersistenceManager

---

### Milestone System

Score thresholds trigger milestones that spawn rewards:

```python
BASE_THRESHOLDS = (1000, 2500, 5000, 10000, 20000)
CYCLE_MULTIPLIER = 1.5  # Multiplied per cycle
DIFFICULTY_MULTIPLIERS = (1.0, 1.5, 2.0)  # easy, medium, hard
```

Milestones cycle through thresholds with increasing multipliers. At each milestone, player chooses from 3 random buffs.

---

### Config System

| File | Purpose |
|------|---------|
| `config/settings.py` | Screen size, colors, speeds, difficulty presets |
| `config/design_tokens.py` | Visual tokens (colors, fonts, spacing) |
| `config/difficulty_config.py` | Difficulty-specific parameters |

Dynamic screen resize supported via `set_screen_size()`, `get_screen_width()`, `get_screen_height()`.

---

### Buff System (`game/buffs/`)

18 buff types affect gameplay. Buffs are awarded at milestones and can stack. Categories include:

- Damage buffs (increase bullet damage)
- Speed buffs (increase movement/fire rate)
- Defense buffs (health regen, shields)
- Special buffs (spread shot, missiles, etc.)

---

### Data Persistence

| Component | File | Purpose |
|-----------|------|---------|
| `PersistenceManager` | `game/mother_ship/` | Save/load game to JSON |
| `UserDB` | `utils/database.py` | User statistics (high score, kills, games played) |

Save data includes: player state, enemies, bullets, score, difficulty, milestone progress.

---

### Rendering Pipeline

Order (back to front):

1. Background layers (parallax starfield, 3 layers for depth)
2. Entities (player, enemies, bullets)
3. Effects (explosions, ripples)
4. MotherShip (when docking)
5. HUD (score, health bar, milestone progress)
6. UI overlays (pause button, reward selector, notifications)

---

### Constants (`game/constants.py`)

All game constants centralized in `GameConstants` dataclass:

```python
GAME_CONSTANTS.PLAYER       # Initial position, invincibility duration
GAME_CONSTANTS.DAMAGE       # Boss collision (30), enemy collision (20), explosive (30)
GAME_CONSTANTS.TIMING       # Fixed delta (1/60 sec), notification duration (90 frames)
GAME_CONSTANTS.ANIMATION    # Entrance duration, ripple effects
GAME_CONSTANTS.BALANCE      # Milestone thresholds, difficulty multipliers
```

---

## File Organization

```
airwar/
|-- config/
|   |-- settings.py              Screen size, colors, speeds, difficulty presets
|   |-- design_tokens.py         Visual design tokens
|   +-- difficulty_config.py     Difficulty-specific parameters
|-- components/                   Reusable components (health bar, timer)
|-- entities/
|   |-- base.py                Entity base class (rect, collision_rect, active)
|   |-- player.py              Player ship
|   |-- enemy.py               Enemy ships and Boss
|   +-- bullet.py              Bullet entities
|-- game/
|   |-- game.py                Entry point (creates window, registers scenes)
|   |-- scene_director.py      Flow orchestration (login->menu->game)
|   |-- constants.py           All game constants (dataclass-based)
|   |-- managers/
|   |   |-- game_controller.py  Game state, scoring, milestones
|   |   |-- spawn_controller.py  Enemy spawning
|   |   |-- collision_controller.py  Collision detection
|   |   |-- bullet_manager.py   Bullet pools
|   |   |-- boss_manager.py     Boss spawning/phases
|   |   |-- milestone_manager.py  Milestone tracking
|   |   |-- input_coordinator.py  Keyboard/mouse coordination
|   |   |-- ui_manager.py      UI elements
|   |   +-- game_loop_manager.py  Frame timing
|   |-- rendering/
|   |   |-- game_renderer.py   Entity drawing
|   |   +-- hud_renderer.py   Score, health, milestones
|   |-- systems/
|   |   |-- health_system.py   Damage/health logic
|   |   |-- reward_system.py   Score calculation
|   |   |-- notification_manager.py  In-game messages
|   |   +-- difficulty_manager.py  Dynamic difficulty
|   |-- spawners/               Enemy/bullet spawn patterns
|   |-- buffs/                  18 buff types
|   |-- mother_ship/            Dock/save mechanism
|   |   |-- mother_ship.py      Visual and docking logic
|   |   |-- state_machine.py   Docking state progression
|   |   |-- persistence_manager.py  JSON save/load
|   |   |-- event_bus.py       Pub/sub for events
|   |   |-- input_detector.py  H-key hold detection
|   |   +-- progress_bar_ui.py  Save progress display
|   |-- explosion_animation/    Explosion effect system
|   +-- death_animation/        Player death animation
|-- input/                     PygameInputHandler
|-- scenes/
|   |-- scene.py               Scene and SceneManager base classes
|   |-- login_scene.py         User login
|   |-- menu_scene.py          Main menu
|   |-- game_scene.py          Gameplay (coordinates all subsystems)
|   |-- pause_scene.py         Pause overlay
|   |-- death_scene.py         Game over
|   |-- exit_confirm_scene.py  Exit dialog
|   +-- tutorial_scene.py      Tutorial
|-- ui/
|   |-- reward_selector.py      Milestone buff selection
|   |-- give_up_ui.py          Surrender UI
|   +-- panels/, buttons/, effects/  UI components
|-- utils/
|   |-- database.py            UserDB (high scores, stats)
|   +-- mouse_interaction.py   MouseSelectableMixin, MouseInteractiveMixin
|-- window/                     Window management (resizable)
+-- tests/                      Test suite (pytest with smoke/slow markers)
```

---

## Testing

### Test Markers

| Marker | Purpose |
|--------|---------|
| `smoke` | Core functionality tests |
| `slow` | Integration tests |

### Fixtures (`tests/conftest.py`)

- `temp_db` - Temporary database for tests
- `clean_imports` - Clean import state between tests

### Notes

- Some tests require `pygame.init()` before running
- Run tests from project root: `cd airwar && python -m pytest`
