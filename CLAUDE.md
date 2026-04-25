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
# As ubt user (recommended - uses locally installed packages)
cd /home/ubt/airwar && sudo -u ubt python3 main.py

# With explicit PYTHONPATH (if running as root)
cd /home/ubt/airwar && PYTHONPATH=/home/ubt/.local/lib/python3.12/site-packages python3 main.py
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

**Scene flow:** `LoginScene -> MenuScene -> GameScene`, which can branch to `PauseScene`, `DeathScene`, `ExitConfirmScene`, or `TutorialScene`. `SceneDirector` orchestrates transitions and state preservation.

**Scene base class** (`scenes/scene.py`):
```python
enter(**kwargs)      # Called when scene becomes active
exit()               # Called when leaving a scene
handle_events(event) # Process pygame events
update(*args)        # Update game state
render(surface)      # Draw to screen
```

**SceneManager** supports state preservation via `save_scene_state(name, state)` / `get_scene_state(name)`.

---

### Core Classes

**Game** (`game/game.py`) - Entry point: creates window, SceneManager, SceneDirector, registers scenes  
**SceneDirector** (`game/scene_director.py`) - Orchestrates login -> menu -> game flow, manages game sessions  
**GameScene** (`scenes/game_scene.py`) - Main gameplay: coordinates subsystems, handles game loop  
**GameController** (`game/managers/game_controller.py`) - Game state, scoring, milestones, difficulty  
**Player** (`entities/player.py`) - Player ship with health, movement, shooting  
**Enemy** (`entities/enemy.py`) - Enemy ships with 6 movement patterns; **Boss** subclass with phase-based attacks

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

**GameController** - Game state, scoring, milestones  
**SpawnController** - Enemy wave spawning logic  
**CollisionController** - Entity collision detection  
**BulletManager** - Player/enemy bullet pools  
**BossManager** - Boss spawning and phase transitions  
**MilestoneManager** - Progress milestones, reward triggers  
**InputCoordinator** - Keyboard/mouse coordination  
**UIManager** - UI element management  
**GameLoopManager** - Frame timing and delta time

#### Systems (`game/systems/`)

**HealthSystem** - Player health, damage, regeneration  
**RewardSystem** - Score calculation, multiplier  
**NotificationManager** - In-game message display  
**DifficultyManager** - Dynamic difficulty adjustment  
**DifficultyStrategies** - Difficulty growth rate strategies  
**MovementPatternGenerator** - Enemy movement pattern generation

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

**straight** - Constant downward velocity | **sine** - Oscillating horizontal while descending | **zigzag** - Alternates horizontal direction at intervals | **dive** - Rapid acceleration toward player Y | **hover** - Floats in fixed Y range | **spiral** - Rotation + descent

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

**MouseSelectableMixin** - Menu option lists (`handle_mouse_motion()`, `handle_mouse_click()`, `append_option_rect()`)  
**MouseInteractiveMixin** - Button-based UI (`register_button()`, `is_button_hovered()`, `get_hovered_button()`)

**Interaction priority:** Mouse hover overrides keyboard; mouse click confirms hovered option; ESC maintains original behavior (back/cancel)

---

### MotherShip System (`game/mother_ship/`)

Dock with the mothership to save game progress. **Docking flow:** hold H → MotherShip appears → fly to docking zone → state machine progresses (searching → approaching → docking → saving) → progress bar shows save progress → JSON serialization via PersistenceManager.

**Components:** MotherShip (visual, docking zone), MotherShipStateMachine (state progression), PersistenceManager (JSON save/load), EventBus (pub/sub), ProgressBarUI, InputDetector (H-key hold), GameIntegrator (connects to game)

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

**settings.py** - Screen size, colors, speeds, difficulty presets  
**game_config.py** - `GameConfig` singleton, adaptive screen sizing  
**design_tokens.py** - Design system (`Colors`, `MilitaryColors`, `ForestColors` themes), typography, spacing  
**difficulty_config.py** - Difficulty-specific parameters, movement pattern unlocks  
**tutorial/** - Tutorial step configuration

---

### Buff System (`game/buffs/`)

18 buff types awarded at milestones (can stack): damage, speed, defense (health regen, shields), and special (spread shot, missiles, etc.)

---

### Data Persistence

**PersistenceManager** (`game/mother_ship/persistence_manager.py`) - Save/load game state to JSON (player state, enemies, bullets, score, difficulty, milestone progress)  
**UserDB** (`utils/database.py`) - User statistics (high score, kills, games played)

---

### Rendering Pipeline

Background layers (parallax starfield) → Entities (player, enemies, bullets) → Effects (explosions, ripples) → MotherShip (when docking) → HUD (score, health, milestones) → UI overlays (pause, reward selector, notifications)

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
├── config/           Settings, game config, design tokens, difficulty, tutorial steps
├── entities/         Player, Enemy, Boss, Bullet (base class in base.py)
├── game/
│   ├── game.py       Entry point
│   ├── scene_director.py  Flow orchestration
│   ├── constants.py  All game constants (GAME_CONSTANTS dataclass)
│   ├── managers/     GameController, SpawnController, CollisionController, BulletManager,
│   │                 BossManager, MilestoneManager, InputCoordinator, UIManager, GameLoopManager
│   ├── rendering/    GameRenderer, HUDRenderer
│   ├── systems/      HealthSystem, RewardSystem, NotificationManager, DifficultyManager,
│   │                 MovementPatternGenerator
│   ├── buffs/        18 buff types (damage, speed, defense, special)
│   ├── mother_ship/  Dock/save mechanism (state machine, persistence, event bus)
│   ├── explosion_animation/  Explosion effects
│   └── death_animation/     Player death animation
├── scenes/           Scene base class, 7 scenes (login, menu, game, pause, death, exit_confirm, tutorial)
├── ui/               Reward selector, buff stats, chamfered panels, particles, military HUD
├── input/            PygameInputHandler
├── utils/            UserDB, mouse interaction mixins
├── window/           Resizable window management
└── tests/            pytest suite (smoke/slow markers)
```

---

## Testing

Test config is in `tests/pytest.ini` (default options: `-v --tb=short -ra`).  
**Markers:** `smoke` (core functionality), `slow` (integration tests)  
**Fixtures:** `temp_db` (temporary database), `clean_imports` (clean import state between tests)  
**Note:** Some tests require `pygame.init()` before running
