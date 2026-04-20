# Responsive Layout Optimization Design

## 1. Overview

Optimize all menu scenes to support responsive layout scaling from 800x600 to fullscreen, solving crowding and text truncation issues.

## 2. Problem Statement

Current menu scenes have fixed pixel values for spacing, fonts, and panel sizes. This causes:
- Crowding in smaller windows (800x600)
- Excessive spacing in larger windows
- Text truncation when elements don't fit

## 3. User Requirements

- **Scope**: Optimize all 5 menu scenes (MenuScene, PauseScene, ExitConfirmScene, DeathScene, LoginScene)
- **Approach**: Responsive layout (ratio-based scaling)
- **Window Support**: 800x600 to fullscreen
- **Optimization Target**: All elements (titles, options, hints, panel margins)
- **Style**: Allow scene-specific differences

## 4. Architecture

### 4.1 Core Tool: ResponsiveHelper

Create `airwar/utils/responsive.py` with static methods:

```python
class ResponsiveHelper:
    BASE_WIDTH = 1280
    BASE_HEIGHT = 720
    MIN_SCALE = 0.625  # 800/1280 - minimum scale protection
    MAX_SCALE = 1.5    # maximum scale protection

    @staticmethod
    def get_scale_factor(width: int, height: int) -> float:
        scale = width / ResponsiveHelper.BASE_WIDTH
        return max(MIN_SCALE, min(scale, MAX_SCALE))

    @staticmethod
    def scale(spacing: int, scale: float) -> int:
        return int(spacing * scale)

    @staticmethod
    def font_size(base_size: int, scale: float) -> int:
        return int(base_size * scale)
```

### 4.2 Design Rationale

- **Base Window**: 1280x720 (primary design target)
- **Scale Calculation**: Based on window width for horizontal alignment consistency
- **Min Scale**: 0.625 (800/1280) prevents elements from becoming too small
- **Max Scale**: 1.5 caps scaling to prevent elements from becoming too large in fullscreen

## 5. Scene-Specific Adjustments

| Scene | Current Issue | Adjustment |
|-------|---------------|------------|
| MenuScene | Panel fixed 400px, crowded in small windows | Panel width = min(400, 400×scale) |
| PauseScene | Option spacing fixed 70px, 3 hint lines dense | Option spacing = 70×scale, hint font fixed at 26 |
| ExitConfirmScene | "GAME SAVED" fixed 50px from options | Save indicator spacing = 50×scale |
| DeathScene | Score area insufficient spacing from options | Score-to-option spacing + 20×scale |
| LoginScene | Panel fixed 460×500px | Panel = (460×scale, 500×scale) |

## 6. Responsive Tables

### 6.1 Font Size Reference

| Base Size | 800x600 (0.625) | 1280x720 (1.0) | 1920x1080 (1.5) |
|-----------|-----------------|----------------|-----------------|
| 100 | 63 | 100 | 100 (capped) |
| 80 | 50 | 80 | 100 (capped) |
| 48 | 30 | 48 | 72 |
| 44 | 28 | 44 | 66 |
| 42 | 26 | 42 | 63 |
| 28 | 18 | 28 | 42 |
| 26 | 16 | 26 | 39 |
| 24 | 15 | 24 | 36 |
| 22 | 14 | 22 | 33 |

### 6.2 Spacing Reference

| Base Spacing | 800x600 (0.625) | 1280x720 (1.0) | 1920x1080 (1.5) |
|--------------|-----------------|----------------|-----------------|
| 70px | 44px | 70px | 105px |
| 65px | 41px | 65px | 98px |
| 60px | 38px | 60px | 90px |
| 55px | 34px | 55px | 83px |
| 50px | 31px | 50px | 75px |
| 30px | 19px | 30px | 45px |

## 7. Implementation Checklist

- [ ] Create `airwar/utils/responsive.py`
- [ ] Update MenuScene with responsive scaling
- [ ] Update PauseScene with responsive scaling
- [ ] Update ExitConfirmScene with responsive scaling
- [ ] Update DeathScene with responsive scaling
- [ ] Update LoginScene with responsive scaling
- [ ] Update scene tests if needed
- [ ] Manual verification at 800x600, 1280x720, fullscreen

## 8. Files to Modify

- `airwar/utils/responsive.py` (new)
- `airwar/scenes/menu_scene.py`
- `airwar/scenes/pause_scene.py`
- `airwar/scenes/exit_confirm_scene.py`
- `airwar/scenes/death_scene.py`
- `airwar/scenes/login_scene.py`

## 9. Constraints

- Must maintain existing visual style and effects
- Must not break existing functionality
- Window resize must be handled smoothly
- All tests must pass after changes
