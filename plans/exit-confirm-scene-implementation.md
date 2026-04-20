# Plan: ExitConfirmScene Implementation

> Source PRD: `docs/superpowers/specs/2026-04-25-exit-confirm-scene-design.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Scene name**: `exit_confirm`
- **Enum location**: `airwar/scenes/scene.py` alongside existing `PauseAction`
- **Class name**: `ExitConfirmScene`
- **Action enum**: `ExitConfirmAction` with values `RETURN_TO_MENU`, `START_NEW_GAME`, `QUIT_GAME`
- **Visual style**: Mirror `PauseScene` exactly (gradient background, stars, particles, glow effects)
- **Integration point**: `SceneDirector._show_pause_menu()` → `_show_exit_confirm()`

---

## Phase 1: Core Infrastructure

**User stories**: 
- 新增 ExitConfirmAction 枚举
- 创建 ExitConfirmScene 类骨架
- 注册场景到 SceneManager

### What to build

Create the minimal working infrastructure for `ExitConfirmScene`:
1. Add `ExitConfirmAction` enum to `scene.py`
2. Create `ExitConfirmScene` class with basic enter/exit/update/render methods
3. Export new class in `scenes/__init__.py`
4. Register scene in `game.py`
5. Basic keyboard navigation (W/S for selection, Enter for confirmation)

### Acceptance criteria

- [ ] `ExitConfirmAction` enum exists with three values
- [ ] `ExitConfirmScene` can be instantiated
- [ ] Scene renders a simple UI with three options
- [ ] W/S keys navigate between options
- [ ] Enter key selects current option and sets result

---

## Phase 2: Visual Consistency

**User stories**:
- 实现与 PauseScene 一致的视觉效果

### What to build

Implement full visual design matching `PauseScene`:
1. Gradient background rendering
2. Animated star field
3. Rising particle effects
4. Glowing title text
5. Styled option boxes with selection highlighting
6. Keyboard hint text at bottom

### Acceptance criteria

- [ ] Background matches PauseScene gradient
- [ ] Stars animate with twinkle effect
- [ ] Particles rise from bottom
- [ ] Title has glow effect
- [ ] Selected option has green highlight
- [ ] Unselected options are grayed out

---

## Phase 3: Scene Director Integration

**User stories**:
- 实现 SceneDirector 中的退出确认流程
- 连接暂停菜单到退出确认场景

### What to build

Integrate `ExitConfirmScene` into the game flow:
1. Add `_show_exit_confirm()` method to `SceneDirector`
2. Modify `_handle_pause_toggle()` to route to exit confirm
3. Handle `saved=True` and `saved=False` states
4. Implement result handling for all three actions
5. ESC key returns to menu (equivalent to RETURN_TO_MENU)

### Acceptance criteria

- [ ] Selecting SAVE_AND_QUIT shows exit confirm with "GAME SAVED ✓"
- [ ] Selecting QUIT_WITHOUT_SAVING shows exit confirm with "EXIT GAME"
- [ ] RETURN_TO_MENU clears save and returns to menu
- [ ] START_NEW_GAME clears save and restarts with same difficulty
- [ ] QUIT_GAME exits the application

---

## Phase 4: Testing

**User stories**:
- 单元测试覆盖
- 集成测试覆盖

### What to build

Comprehensive test coverage:
1. Unit tests for `ExitConfirmScene` class
2. Unit tests for `ExitConfirmAction` enum
3. Integration tests for game flow
4. Test for keyboard navigation
5. Test for result handling

### Acceptance criteria

- [ ] Unit tests pass for ExitConfirmScene
- [ ] Integration tests pass for full exit flow
- [ ] All existing tests still pass

---

## Phase 5: Polish

**User stories**:
- 优化用户体验

### What to build

Final polish and edge cases:
1. Smooth transition animations (fade in/out)
2. Sound effects (if applicable)
3. Edge case: window close during exit confirm
4. Documentation

### Acceptance criteria

- [ ] Scene has smooth enter/exit animation
- [ ] Closing window during exit confirm is handled gracefully
- [ ] Code is documented
