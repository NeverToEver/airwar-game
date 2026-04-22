# Plan: Difficulty Coefficient Display

> Source: [difficulty-coefficient-display-design.md](../docs/designs/difficulty-coefficient-display-design.md)

## Status: ✅ COMPLETED

## Architectural Decisions

- **Display format**: `current → initial` (e.g., `4.5 → 1.0`)
- **Position**: Left center, vertically centered, 15px margin from edge
- **Style**: Sci-fi/Cyberpunk (cyan neon glow)
- **Data source**: DifficultyManager (existing system)

---

## Phase 1: Core Panel Component ✅

**User stories**:
- As a player, I want to see the current difficulty coefficient
- As a player, I want to see the initial difficulty coefficient
- As a player, I want to see the relationship between current and initial

### What to build

Create the `DifficultyCoefficientPanel` class that:
- Displays `current → initial` format
- Shows a label "COEFF"
- Shows a progress bar relative to max multiplier
- Positions on left center of screen

### Acceptance Criteria

- [x] `DifficultyCoefficientPanel` class created in `airwar/game/systems/`
- [x] Renders at left center position (x=15, vertically centered)
- [x] Displays format: `{current} → {initial}`
- [x] Progress bar shows current/max ratio
- [x] Label "COEFF" displayed above values
- [x] Basic cyan color scheme applied

---

## Phase 2: Sci-fi Glow Effects ✅

**User stories**:
- As a player, I want visually appealing UI that matches the game theme
- As a player, I want visual feedback when difficulty increases

### What to build

Enhance the panel with:
- Neon border glow effect (cyan with transparency)
- Dark translucent background
- Pulse animation when coefficient increases
- Color shift based on danger level (green → yellow → red)

### Acceptance Criteria

- [x] Neon border with glow effect rendered
- [x] Dark translucent background `rgba(10, 10, 30, 220)`
- [x] Pulse animation triggers on value increase
- [x] Color transitions match DifficultyIndicator thresholds

---

## Phase 3: Integration ✅

**User stories**:
- As a player, I want to see the panel during gameplay
- As a player, I want the panel to update in real-time

### What to build

Integrate panel into existing rendering pipeline:
- Panel initialization in GameScene.enter()
- Update call in GameScene.update()
- Render call in GameScene.render()

### Acceptance Criteria

- [x] Panel renders during normal gameplay
- [x] Panel updates in real-time as boss kills increase
- [x] No conflicts with existing UI elements (HUD, BuffStatsPanel, DifficultyIndicator)
- [x] No breaking changes to existing functionality

---

## Phase 4: Testing ✅

**User stories**:
- As a developer, I want automated tests for the new component

### What to build

Add unit tests for the panel component.

### Acceptance Criteria

- [x] Test renders without exceptions
- [x] Test displays correct format
- [x] Test progress bar calculation
- [x] Test glow effect rendering
- [x] Test color thresholds

---

## File Changes Summary

| Phase | Action | File |
|-------|--------|------|
| 1 | CREATE | `airwar/game/systems/difficulty_coefficient_panel.py` |
| 1-2 | MODIFY | `airwar/game/systems/hud_renderer.py` (not modified) |
| 3 | MODIFY | `airwar/scenes/game_scene.py` |
| 4 | CREATE | `airwar/tests/test_difficulty_coefficient_panel.py` |
