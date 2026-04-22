# Technical Design: Difficulty Coefficient Display

## Overview

| Field | Value |
|-------|-------|
| **Feature Name** | Difficulty Coefficient Display |
| **Type** | UI Component |
| **Status** | Draft |
| **Date** | 2026-04-22 |

---

## 1. Concept & Vision

A vertical sidebar on the left side of the screen displaying the player's difficulty coefficient evolution in real-time. Styled with a sci-fi/cyberpunk aesthetic featuring neon borders and glow effects, it serves as a constant reminder of how the game has become more challenging compared to the initial difficulty selection.

**Display Format:** `current → initial` (e.g., `4.5 → 1.0`)

---

## 2. Design Specifications

### 2.1 Visual Style: Sci-fi/Cyberpunk

| Element | Specification |
|---------|---------------|
| **Primary Color** | `#00ffff` (Cyan neon) |
| **Secondary Color** | `#ff00ff` (Magenta accent) |
| **Background** | `rgba(10, 10, 30, 0.85)` (Dark translucent) |
| **Border** | 2px solid with glow effect |
| **Font** | Pygame default monospace-style |
| **Font Size** | 24px for values, 16px for label |

### 2.2 Layout

```
┌──────────────┐
│   COEFF      │  ← Label (16px, dim cyan)
│              │
│  4.5 → 1.0   │  ← Main display (24px, bright cyan)
│              │
│  ▓▓▓▓▓░░░░░  │  ← Progress bar to max
│              │
│  [+3.5]      │  ← Delta indicator (optional, green if positive)
└──────────────┘
```

- **Position:** Left center, vertically centered on screen
- **Dimensions:** 120px width, auto height (~140px)
- **Margin from edge:** 15px

### 2.3 Dynamic Elements

| Element | Behavior |
|---------|----------|
| **Glow pulse** | Subtle pulse animation when coefficient increases |
| **Color shift** | Bar color transitions based on danger level (same as DifficultyIndicator) |
| **Delta badge** | Shows increase from initial, green glow if significant |

---

## 3. Data Flow

```
DifficultyManager
       │
       ├── get_current_multiplier() ──► Current value
       │
       ├── _strategy.base_multiplier ──► Initial value (stored at init)
       │
       └── get_current_params() ──────► Max multiplier for progress bar
```

### 3.1 Required Data from DifficultyManager

| Method | Usage |
|--------|-------|
| `get_current_multiplier()` | Current difficulty multiplier |
| `_strategy.base_multiplier` | Initial multiplier (read-only at init) |
| `MAX_MULTIPLIER_GLOBAL` | For progress bar calculation |

---

## 4. Component Design

### 4.1 Class: `DifficultyCoefficientPanel`

**Location:** `airwar/game/systems/difficulty_coefficient_panel.py` (new file)

```python
class DifficultyCoefficientPanel:
    def __init__(self, difficulty_manager: DifficultyManager):

    def update(self) -> None:
        """Called each frame to check for value changes"""

    def render(self, surface: pygame.Surface) -> None:
        """Render the sidebar panel"""
```

### 4.2 States

| State | Visual Effect |
|-------|---------------|
| **Stable** | Standard cyan glow |
| **Increasing** | Pulse animation, brighter glow |
| **High danger (≥6.0)** | Red tint, warning pulse |

---

## 5. Integration Points

### 5.1 HUD Renderer Integration

**File:** `airwar/game/systems/hud_renderer.py`

Add new method:
```python
def render_difficulty_coefficient_panel(self, surface, difficulty_manager) -> None:
```

### 5.2 UIManager Integration

**File:** `airwar/game/managers/ui_manager.py`

Add render call in `render_game()` or create dedicated `render_difficulty_panel()` method.

### 5.3 Game Loop Integration

**File:** `airwar/game/managers/game_loop_manager.py`

- Call `panel.update()` in game loop
- Access `difficulty_manager` via `_game_controller.difficulty_manager`

---

## 6. File Changes Summary

| Action | File | Description |
|--------|------|-------------|
| **CREATE** | `airwar/game/systems/difficulty_coefficient_panel.py` | New panel component |
| **MODIFY** | `airwar/game/systems/hud_renderer.py` | Add render method |
| **MODIFY** | `airwar/game/managers/ui_manager.py` | Integrate panel rendering |
| **MODIFY** | `airwar/game/managers/game_loop_manager.py` | Update loop calls |

---

## 7. Acceptance Criteria

- [ ] Panel displays on left center of screen
- [ ] Shows format: `4.5 → 1.0`
- [ ] Cyan neon glow effect applied
- [ ] Progress bar shows relative to max multiplier
- [ ] Updates in real-time as difficulty increases
- [ ] Follows existing code patterns and conventions
- [ ] No breaking changes to existing UI elements

---

## 8. Implementation Order

1. Create `DifficultyCoefficientPanel` class with basic rendering
2. Add sci-fi glow effects (pygame drawing with transparency)
3. Integrate into `HUDRenderer`
4. Wire up in `UIManager`
5. Add update calls in game loop
6. Test and polish visual effects
