# Tutorial UI Redesign - Implementation Plan

**Date**: 2026-04-22
**Reference**: `docs/2026-04-22-tutorial-ui-redesign.md`

---

## Phase 1: Core Refactoring (P0)

### T1.1: Refactor `tutorial_scene.py`

**Tasks**:
1. Import `DesignTokens` and related utilities:
   ```python
   from airwar.config.design_tokens import get_design_tokens
   from airwar.ui.menu_background import MenuBackground
   from airwar.ui.particles import ParticleSystem
   ```

2. Replace color initialization with DesignTokens:
   ```python
   self._tokens = get_design_tokens()
   colors = self._tokens.colors
   self.colors = {
       'bg': colors.BACKGROUND_PRIMARY,
       'title': colors.TEXT_PRIMARY,
       'selected': colors.HUD_AMBER,
       # ...
   }
   ```

3. Remove standalone color definitions and particle systems

4. Adopt menu_scene.py patterns for initialization

**Acceptance Criteria**:
- [ ] DesignTokens properly initialized
- [ ] Colors match other scenes
- [ ] Background and particle systems use shared components

---

### T1.2: Refactor `renderer.py` - Panel Rendering

**Tasks**:
1. Replace `TUTORIAL_COLORS` with `DesignTokens` colors
2. Use `menu_scene.py` panel rendering pattern:
   - 4-layer glow effect
   - Unified border style
   - Same border radius

3. Remove independent background rendering (use MenuBackground)

**Acceptance Criteria**:
- [ ] Panel matches menu_scene.py exactly
- [ ] Glow effects consistent
- [ ] Border radius matches (15)

---

### T1.3: Refactor `renderer.py` - Option Boxes

**Tasks**:
1. Replace circular progress indicators with option list highlighting
2. Implement option box style from menu_scene.py:
   - Selected: glow effect + BUTTON_SELECTED_BG + HUD_AMBER border
   - Unselected: BUTTON_UNSELECTED_BG + TEXT_MUTED border

3. Add keyboard navigation highlighting (UP/DOWN selection)

**Acceptance Criteria**:
- [ ] Option boxes match menu_scene.py style
- [ ] Selection highlighting works
- [ ] Arrow indicators display correctly

---

### T1.4: Refactor `renderer.py` - Buttons

**Tasks**:
1. Update button style to match pause_scene.py:
   - Width: 180
   - Height: 50
   - Border radius: 10
   - Colors: HUD_AMBER palette

2. Add hover effects using DesignTokens

**Acceptance Criteria**:
- [ ] Buttons match pause_scene.py style
- [ ] Hover states work
- [ ] Colors consistent with design tokens

---

## Phase 2: Layout Adjustments (P1)

### T2.1: Update `panel.py` Layout Calculations

**Tasks**:
1. Update panel dimensions to match DesignTokens:
   - Width: 400 (from Spacing.PANEL_WIDTH)
   - Height: 460 (from Spacing.PANEL_HEIGHT)

2. Adjust content area calculations:
   - Title area height
   - Navigation area height
   - Option box dimensions

3. Remove hardcoded values, use Spacing system

**Acceptance Criteria**:
- [ ] Panel dimensions match other scenes
- [ ] Content areas properly calculated
- [ ] Responsive scaling works

---

### T2.2: Update `renderer.py` - Typography

**Tasks**:
1. Replace `TUTORIAL_FONTS` with DesignTokens:
   ```python
   Typography.TITLE_SIZE      # 100
   Typography.OPTION_SIZE      # 44
   Typography.BODY_SIZE        # 36
   Typography.CAPTION_SIZE     # 32
   Typography.SMALL_SIZE       # 24
   ```

2. Update all text rendering calls

**Acceptance Criteria**:
- [ ] Typography matches other scenes
- [ ] Text sizes consistent
- [ ] No hardcoded font sizes

---

### T2.3: Update `renderer.py` - Spacing

**Tasks**:
1. Replace hardcoded spacing with DesignTokens:
   ```python
   Spacing.SPACE_MD           # 12
   Spacing.SPACE_LG           # 16
   Spacing.SPACE_XL           # 20
   ```

2. Update all padding and margin calculations

**Acceptance Criteria**:
- [ ] Spacing consistent with other scenes
- [ ] No hardcoded spacing values

---

## Phase 3: Configuration Cleanup (P2)

### T3.1: Simplify `tutorial_config.py`

**Tasks**:
1. Remove redundant color definitions (now in DesignTokens)
2. Remove redundant font definitions (now in DesignTokens)
3. Keep only tutorial-specific configurations:
   - TUTORIAL_STEPS
   - StepType enum
   - Basic layout configs (if needed)

4. Update exports in `__init__.py`

**Acceptance Criteria**:
- [ ] No duplicate color definitions
- [ ] No duplicate font definitions
- [ ] Tutorial-specific configs preserved

---

### T3.2: Update imports across files

**Tasks**:
1. Update all imports in affected files
2. Remove old imports (TUTORIAL_COLORS, TUTORIAL_FONTS)
3. Add DesignTokens imports

**Acceptance Criteria**:
- [ ] All imports updated
- [ ] No circular dependencies
- [ ] Clean import structure

---

## Phase 4: Testing (P3)

### T4.1: Update unit tests

**Tasks**:
1. Update `test_tutorial_flow.py` if needed
2. Update `test_tutorial_navigator.py` if needed
3. Update `test_tutorial_renderer.py` if exists
4. Update `test_tutorial_panel.py` if needed

**Acceptance Criteria**:
- [ ] All tutorial tests pass
- [ ] Visual regression tests pass (if any)

---

### T4.2: Run full test suite

**Tasks**:
1. Run all tests
2. Verify no regressions
3. Check for any warnings

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] No new warnings
- [ ] Performance acceptable

---

## Phase 5: Documentation (P4)

### T5.1: Update README or docs

**Tasks**:
1. Update any relevant documentation
2. Document design token usage

**Acceptance Criteria**:
- [ ] Documentation updated
- [ ] Code comments added where needed

---

## Execution Order

```
Phase 1 (P0): Core Refactoring
├── T1.1: tutorial_scene.py
├── T1.2: renderer.py - Panel
├── T1.3: renderer.py - Options
└── T1.4: renderer.py - Buttons

Phase 2 (P1): Layout
├── T2.1: panel.py
├── T2.2: Typography
└── T2.3: Spacing

Phase 3 (P2): Cleanup
├── T3.1: tutorial_config.py
└── T3.2: Import updates

Phase 4 (P3): Testing
├── T4.1: Unit tests
└── T4.2: Full suite

Phase 5 (P4): Documentation
└── T5.1: Docs update
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Incremental changes, test after each phase |
| Visual inconsistencies | Compare with menu_scene.py after each change |
| Layout issues | Use ResponsiveHelper consistently |
| Test failures | Update tests before refactoring |

---

## Success Criteria

1. Tutorial scene visually matches menu/pause scenes
2. All DesignTokens properly integrated
3. No hardcoded color/font/spacing values
4. All tests pass
5. Clean code structure
