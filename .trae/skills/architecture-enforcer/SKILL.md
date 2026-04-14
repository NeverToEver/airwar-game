---
name: "architecture-enforcer"
description: "Enforces software architecture & engineering standards (SRP, low-coupling, interface-oriented, decoupling). Invoke before any code generation, refactoring, or design task."
---

# Architecture & Engineering Standards Enforcer

This skill enforces strict software architecture and engineering standards across all code generation, refactoring, design, and documentation tasks. It MUST be applied automatically before any code-related work.

## Mandatory Pre-Work Checklist

Before writing ANY code, you MUST:

1. **Architecture Design First**: Describe module division and responsibility boundaries
2. **Smell Detection**: Identify scattered logic, duplicated code, mixed responsibilities
3. **Refactor Proposal**: Suggest refactoring with runnable code if issues found
4. **Documentation**: Generate module design docs, interface specs, and maintenance guides
5. **Problem-First**: If given messy code, point out problems BEFORE refactoring

## I. Core Design Principles (ALWAYS Enforced)

### 1. Single Responsibility Principle (SRP)
- One class/function does ONE thing with a clear, describable responsibility
- If you cannot describe a class's responsibility in one sentence, it does too much
- A function that exceeds one screen height MUST be split

### 2. High Cohesion, Low Coupling
- Related logic MUST be concentrated; unrelated logic MUST be isolated
- Modules communicate ONLY through interfaces, never through shared mutable state
- No module should need to know the internal details of another module

### 3. Interface-Oriented Design
- External dependencies MUST depend on abstractions, not concrete implementations
- All public APIs MUST be defined through class interfaces or protocol classes
- Facilitate replacement and extension without modifying existing code

### 4. Maintainability First
- Clear code structure, consistent naming conventions, moderate comments
- Code should be easy to iterate on without breaking existing functionality

### 5. Extensibility First
- Reserve extension points; avoid hardcoding, magic numbers, deep nesting
- Use configuration files or constants for all tunable values
- Design with the Open/Closed Principle in mind

### 6. Avoid Shotgun Surgery
- Same-category functionality MUST be centralized
- Logic MUST NOT be scattered across multiple files
- A single requirement change should only require modifying ONE module

## II. Project Structure Standards

### Rules
1. **Organize by function/module**, NOT by code length
2. **Entry files** only handle startup and dispatch — NO business logic
3. **Core modules** MUST be independent packages/files: window, renderer, input, game logic, resource management
4. **Configuration** MUST be centrally managed, never scattered

### Expected Module Layout (Game Project)
```
project/
├── main.py                  # Entry point: startup & dispatch only
├── config/                  # Centralized configuration
│   ├── settings.py          # Game settings & constants
│   └── keys.py              # Key bindings
├── core/                    # Core engine modules
│   ├── window.py            # Window management
│   ├── renderer.py          # Rendering abstraction
│   ├── input_handler.py     # Input event processing
│   └── game_loop.py         # Main loop controller
├── entities/                # Game entities
│   ├── base_entity.py       # Abstract base entity
│   ├── player.py            # Player entity
│   └── enemy.py             # Enemy entity
├── systems/                 # Game systems (logic)
│   ├── collision.py         # Collision detection
│   ├── movement.py          # Movement system
│   └── spawning.py          # Entity spawning
├── ui/                      # UI layer
│   ├── hud.py               # Heads-up display
│   └── menu.py              # Menu screens
├── resources/               # Resource management
│   ├── asset_loader.py      # Asset loading abstraction
│   └── sound_manager.py     # Sound management
└── utils/                   # Shared utilities
    └── helpers.py           # Common helper functions
```

## III. Code Style Standards (Mandatory)

### Naming
- Variables: `snake_case`, descriptive names, NO single-letter variables (except loop counters `i`, `j`)
- Functions: `snake_case`, name should describe the action (`calculate_damage`, NOT `calc`)
- Classes: `PascalCase`, name should describe the concept (`PlayerShip`, NOT `PS`)
- Constants: `UPPER_SNAKE_CASE` (`MAX_HEALTH`, NOT `max_hp`)
- Private members: prefix with `_` (`_internal_state`)

### Function Length
- One function MUST NOT exceed one screen height (~40 lines)
- If longer, extract helper functions with clear names

### Nesting
- Maximum 3 levels of indentation
- Use early returns, guard clauses, and extracted methods to reduce nesting

### Duplication
- Duplicated code (3+ occurrences) MUST be extracted into a utility function or base class
- Shared behavior belongs in a base class; variant behavior uses strategy/template method patterns

### Global State
- Minimize global variables
- State MUST be centrally managed (e.g., in a game state manager class)
- NO direct manipulation of global mutable state across modules

## IV. Decoupling Requirements (Strict for Game/Window Projects)

### Mandatory Separation
1. **Window/Renderer/Event** MUST be encapsulated as independent modules
2. **External code MUST NEVER directly operate** underlying libraries (e.g., pygame window, surface)
3. **All underlying operations** MUST be exposed through class interfaces
4. **Game logic, UI, input, rendering** MUST be mutually isolated
5. **Any modification** should affect only ONE module, never trigger cascading changes

### Decoupling Pattern
```python
# WRONG: Direct pygame usage in game logic
class Player:
    def move(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.x -= 5

# CORRECT: Input abstraction + interface
class InputHandler:
    def get_direction(self) -> tuple[int, int]:
        raise NotImplementedError

class PygameInputHandler(InputHandler):
    def get_direction(self) -> tuple[int, int]:
        keys = pygame.key.get_pressed()
        direction_x = -1 if keys[pygame.K_LEFT] else (1 if keys[pygame.K_RIGHT] else 0)
        direction_y = -1 if keys[pygame.K_UP] else (1 if keys[pygame.K_DOWN] else 0)
        return (direction_x, direction_y)

class Player:
    def __init__(self, input_handler: InputHandler):
        self._input_handler = input_handler

    def move(self):
        direction = self._input_handler.get_direction()
        self.x += direction[0] * self.speed
        self.y += direction[1] * self.speed
```

## V. Output Format Requirements

For EVERY code task, the output MUST follow this structure:

### Step 1: Design Overview
- Module division and responsibility boundaries
- Data flow and dependency diagram (text-based)
- Key interfaces and their contracts

### Step 2: Complete Runnable Code
- Full implementation following all standards above
- No placeholders, no TODOs, no stubs
- Code must be directly executable

### Step 3: Documentation (Auto-Generated)
- **Module Design Document**: Purpose, responsibilities, dependencies for each module
- **Interface Specification**: Public APIs, parameters, return values, side effects
- **Maintenance Guide**: How to extend, common modification points, testing approach

## VI. Code Review Checklist (Auto-Apply)

Before finalizing ANY code, verify:

- [ ] Each class has a single, clear responsibility
- [ ] No module directly accesses another module's internals
- [ ] All public APIs are through interfaces/abstract classes
- [ ] No magic numbers — all constants are named
- [ ] No function exceeds ~40 lines
- [ ] No more than 3 levels of nesting
- [ ] No duplicated code blocks
- [ ] No global mutable state accessed across modules
- [ ] Underlying library calls are wrapped in abstraction layers
- [ ] Game logic is independent of rendering/input/UI
- [ ] Configuration is centralized
- [ ] Entry file contains no business logic

## VII. Anti-Patterns (Immediately Flag & Refactor)

| Anti-Pattern | Description | Refactoring |
|---|---|---|
| God Class | One class does everything | Split by responsibility |
| Magic Number | Unnamed constants | Extract to named constants |
| Hardcoded Dependency | Direct `import` of concrete class | Use interface/abstraction |
| Scattered Logic | Same feature logic in multiple files | Centralize in one module |
| Deep Nesting | 4+ levels of if/while | Guard clauses, early returns |
| Long Function | Function > 40 lines | Extract helper functions |
| Global State | Mutable globals across modules | Centralized state manager |
| Leaky Abstraction | Underlying library details exposed | Wrap in interface |
| Copy-Paste Code | Duplicated blocks | Extract utility/base class |
| Mixed Concerns | Logic + UI + I/O in one function | Separate by concern |
