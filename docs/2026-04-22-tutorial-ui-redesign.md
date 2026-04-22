# Tutorial UI Redesign Specification

**Date**: 2026-04-22
**Status**: Approved
**Author**: Claude Code
**Related Issues**: UI inconsistency with other scenes, layout problems (text crowding, overlapping buttons)

---

## 1. Problem Statement

The tutorial scene has significant visual and functional inconsistencies compared to other scenes in the application:

### 1.1 Visual Inconsistency
- **Color System**: Tutorial uses independent blue-toned color scheme (`TUTORIAL_COLORS`), while other scenes use orange-toned scheme from `DesignTokens.Colors`
- **Typography**: Tutorial defines independent font sizes, while other scenes use `DesignTokens.Typography`
- **Spacing**: Tutorial uses hardcoded spacing values instead of `DesignTokens.Spacing`

### 1.2 Layout Problems
- **Panel Size**: Tutorial panel (700x600) is much larger than other panels (400x460), causing:
  - Text crowding
  - Poor spacing
  - Content overlap
- **Component Style**: Tutorial uses different button and progress indicator styles

### 1.3 Component Differences
- Tutorial: Independent circular progress indicators, simple rectangular buttons
- Others: Glowing option boxes with unified border and shadow effects

---

## 2. Design Decisions

### 2.1 Visual Style: Full Consistency
**Decision**: Tutorial scene will use `DesignTokens` completely for all visual elements.

**Rationale**:
- Maximizes UI consistency across all scenes
- Leverages existing, well-tested design system
- Easier to maintain and extend

### 2.2 Layout Structure: Panel + List
**Decision**: Use centered panel with vertical option list (matching menu_scene.py pattern).

**Layout Structure**:
```
┌─────────────────────────────────────┐
│          AIR WAR                    │
│        Tutorial Title               │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │
│  │ > Key   - Description       │    │
│  │   Key   - Description        │    │
│  │   Key   - Description        │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│     [前一步]        [下一步]         │
├─────────────────────────────────────┤
│   Note: 辅助说明文字                │
│   Warning: 警告信息                │
└─────────────────────────────────────┘
```

### 2.3 Progress Indicator: Option List Highlighting
**Decision**: Remove independent progress indicators, use option highlighting instead.

**Rationale**:
- Matches menu_scene.py pattern
- Cleaner visual design
- Natural progress indication through content navigation

### 2.4 Keyboard Navigation: Preserved
**Decision**: Keep UP/DOWN navigation for content item selection.

**Rationale**:
- Improves interactivity
- Accessible keyboard-only navigation
- Consistent with existing tutorial behavior

---

## 3. Design Tokens Integration

### 3.1 Colors
Use `DesignTokens.Colors` directly:

```python
# Background
Colors.BACKGROUND_PRIMARY      # (5, 5, 8)
Colors.BACKGROUND_SECONDARY   # (12, 10, 8)

# Primary Palette
Colors.HUD_AMBER              # (255, 180, 50)
Colors.HUD_AMBER_BRIGHT       # (255, 200, 80)
Colors.HUD_ORANGE             # (255, 140, 0)

# Text
Colors.TEXT_PRIMARY           # (255, 220, 180)
Colors.TEXT_SECONDARY         # (220, 180, 150)
Colors.TEXT_MUTED             # (150, 120, 100)
Colors.TEXT_HINT              # (120, 100, 80)

# UI Elements
Colors.PANEL_BORDER           # (150, 110, 80)
Colors.BUTTON_SELECTED_BG     # (50, 35, 25)
Colors.BUTTON_UNSELECTED_BG   # (30, 20, 15)

# Effects
Colors.PARTICLE_PRIMARY       # (255, 150, 50)
Colors.PARTICLE_ALT           # (255, 100, 80)
```

### 3.2 Typography
Use `DesignTokens.Typography`:

```python
Typography.TITLE_SIZE         # 100 - Tutorial title
Typography.HEADING_SIZE       # 72 - Section headings
Typography.OPTION_SIZE        # 44 - Content items
Typography.BODY_SIZE          # 36 - Descriptions
Typography.CAPTION_SIZE       # 32 - Hint text
Typography.SMALL_SIZE         # 24 - Auxiliary text
```

### 3.3 Spacing
Use `DesignTokens.Spacing`:

```python
Spacing.SPACE_MD              # 12
Spacing.SPACE_LG              # 16
Spacing.SPACE_XL              # 20
Spacing.SPACE_2XL             # 24
Spacing.SPACE_3XL             # 32

Spacing.BORDER_RADIUS_MD      # 8
Spacing.BORDER_RADIUS_LG      # 12
```

### 3.4 Components
Use `DesignTokens.UIComponents`:

```python
UIComponents.BUTTON_WIDTH     # 280
UIComponents.BUTTON_HEIGHT    # 60
UIComponents.TITLE_Y          # 100
UIComponents.HINT_Y_OFFSET    # 70
```

### 3.5 Animation
Use `DesignTokens.Animation`:

```python
Animation.GLOW_SPEED          # 0.08
Animation.GLOW_RADIUS_DEFAULT # 4
Animation.GLOW_RADIUS_TITLE   # 6
Animation.GLOW_RADIUS_BUTTON  # 5
Animation.HOVER_SCALE_FACTOR  # 0.18
Animation.BLINK_INTERVAL      # 25
```

---

## 4. Component Specifications

### 4.1 Panel Layout

| Property | Value | Source |
|----------|-------|--------|
| Width | 400 | `Spacing.PANEL_WIDTH` |
| Height | 460 | `Spacing.PANEL_HEIGHT` |
| Border Radius | 15 | `Spacing.BORDER_RADIUS_XL` |
| Glow Effect | 4 layers, 4px each | `menu_scene.py` pattern |
| Border | 2px, `PANEL_BORDER` | `Colors.PANEL_BORDER` |

### 4.2 Option Box Style

**Selected State**:
```python
background: BUTTON_SELECTED_BG (50, 35, 25)
border: 2px solid HUD_AMBER
glow: 4 layers, expand 3px each
text: HUD_AMBER
arrow: ">"
```

**Unselected State**:
```python
background: BUTTON_UNSELECTED_BG (30, 20, 15)
border: 1px solid TEXT_MUTED
text: TEXT_MUTED
arrow: " "
```

**Dimensions**:
```python
height: 70 (from Spacing.OPTION_HEIGHT)
gap: 12 (from Spacing.OPTION_GAP)
width: 360 (within 400 panel with padding)
```

### 4.3 Button Style

Match `pause_scene.py` button style:

```python
width: 180 (ButtonConfig.WIDTH)
height: 50 (ButtonConfig.HEIGHT)
border_radius: 10
colors: Using HUD_AMBER palette
```

**Hover State**:
```python
background: Colors.HUD_AMBER with 50% opacity
border: Colors.HUD_AMBER_BRIGHT
```

### 4.4 Text Rendering

**Title (Tutorial Step Title)**:
```python
font: TITLE_SIZE (100)
color: TEXT_PRIMARY
glow: HUD_AMBER_BRIGHT, 6 layers
position: center-x, panel_y + 60
```

**Content Item Key**:
```python
font: OPTION_SIZE (44)
color: HUD_AMBER (selected) / TEXT_MUTED (unselected)
position: left-aligned with 20px padding
```

**Content Item Description**:
```python
font: BODY_SIZE (36)
color: TEXT_SECONDARY
position: right-aligned with 20px padding
```

**Hint Text**:
```python
font: SMALL_SIZE (24)
color: TEXT_HINT
blink: every 25 frames
```

### 4.5 Background Effects

**Particle System**:
```python
count: 45 (from UIComponents.PARTICLE_COUNT)
color: PARTICLE_PRIMARY or PARTICLE_ALT
direction: -1 (floating upward)
```

**Glow Text Effect** (from `menu_scene.py`):
```python
for i in range(glow_radius, 0, -1):
    alpha = int(120 / i)
    # Draw text offset by i pixels
```

---

## 5. Interaction Design

### 5.1 Keyboard Navigation

| Key | Action |
|-----|--------|
| `↑` / `W` | Select previous content item |
| `↓` / `S` | Select next content item |
| `←` | Go to previous tutorial step |
| `→` | Go to next tutorial step |
| `ESC` | Return to menu |
| `ENTER` / `SPACE` | Confirm / Next step |

### 5.2 Mouse Interaction

| Element | Action |
|---------|--------|
| Button area | Click to navigate steps |
| Option box | Click to select item (optional) |
| Outside panel | No action |

### 5.3 State Management

**Step Navigation**:
- Track current step index (0 to n-1)
- Track selected content item index
- Handle step transitions with state reset

**Selection State**:
- Default selection: first item
- Wrap around at boundaries
- Clear selection on step change

---

## 6. Layout Calculations

### 6.1 Panel Positioning

```python
center_x = screen_width // 2
center_y = screen_height // 2
panel_x = center_x - PANEL_WIDTH // 2
panel_y = center_y - PANEL_HEIGHT // 2 + 30  # Slight offset for title
```

### 6.2 Title Section

```python
title_y = panel_y + 60
# Or use UIComponents.TITLE_Y for consistency
```

### 6.3 Content Area

```python
content_start_y = panel_y + TITLE_HEIGHT + PADDING
content_height = panel_height - TITLE_HEIGHT - NAV_HEIGHT - PADDING * 2
```

### 6.4 Navigation Buttons

```python
button_y = panel_y + panel_height - BUTTON_HEIGHT - 30
# Buttons centered within panel
```

---

## 7. File Structure Changes

### 7.1 Files to Modify

| File | Changes |
|------|---------|
| `scenes/tutorial_scene.py` | Adopt DesignTokens, simplify render calls |
| `components/tutorial/renderer.py` | Complete rewrite of rendering logic |
| `components/tutorial/panel.py` | Adjust layout calculations |
| `config/tutorial/tutorial_config.py` | Simplify/remove redundant configs |
| `config/tutorial/__init__.py` | Update exports |

### 7.2 Files to Remove

| File | Reason |
|------|--------|
| `config/tutorial/tutorial_colors.py` | Replaced by DesignTokens |
| `config/tutorial/tutorial_fonts.py` | Replaced by DesignTokens |

### 7.3 New Components to Reuse

```python
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.effects import EffectsRenderer
from airwar.utils.responsive import ResponsiveHelper
```

---

## 8. Testing Requirements

### 8.1 Visual Regression Tests
- Compare tutorial scene screenshots with menu/pause scenes
- Verify color consistency
- Check spacing and layout ratios

### 8.2 Functional Tests
- Keyboard navigation works correctly
- Mouse click detection on buttons
- Step transitions maintain state
- Selection wrapping behavior

### 8.3 Responsive Tests
- Test on different screen resolutions
- Verify scaling behavior
- Check panel positioning

---

## 9. Migration Checklist

- [ ] Update `tutorial_scene.py` to use DesignTokens
- [ ] Rewrite `renderer.py` with unified component styles
- [ ] Adjust `panel.py` layout calculations
- [ ] Simplify `tutorial_config.py`
- [ ] Remove redundant color/font configs
- [ ] Reuse `MenuBackground`, `ParticleSystem`
- [ ] Update all tests
- [ ] Verify visual consistency with menu/pause scenes
- [ ] Test keyboard and mouse interactions
- [ ] Run full test suite

---

## 10. Success Criteria

1. **Visual Consistency**: Tutorial scene matches menu/pause scenes in color, typography, and spacing
2. **Layout Correctness**: No text crowding or component overlap
3. **Functional Completeness**: All navigation features work as specified
4. **Performance**: No regression in frame rate or responsiveness
5. **Maintainability**: Single source of truth for design tokens

---

## 11. References

- `scenes/menu_scene.py` - Reference implementation for panel and option styles
- `scenes/pause_scene.py` - Reference for button and glow effects
- `ui/buff_stats_panel.py` - Example of DesignTokens integration
- `config/design_tokens.py` - Design token definitions
- `components/tutorial/renderer.py` - Current tutorial renderer (to be rewritten)

---

**Approval Status**: Approved by user on 2026-04-22
**Implementation Priority**: High
**Estimated Effort**: Medium
