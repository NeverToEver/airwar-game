# AirWar Code Quality Audit Report

**Date:** 2026-04-26
**Updated:** 2026-04-26 — 4 unresolved items tracked in REMEDIATION_PLAN.md
**Scope:** `/home/ubt/airwar/airwar/` (all Python source files, excluding tests)
**Method:** Automated scan with manual review across 4 dimensions: magic numbers, long functions/nesting/god classes, naming/imports, and design/duplication issues.

## Fix Status

| Priority | Issues Fixed | Status |
|----------|-------------|--------|
| **P0** | `MilitaryUI.SCANLINE_*` missing attributes added | ✅ Fixed |
| **P1** | Collision damage hardcoded → `GAME_CONSTANTS` | ✅ Fixed |
| **P1** | 8 dead-code functions removed | ✅ Fixed |
| **P1** | FPS tick rate hardcoded → `FPS` constant | ✅ Fixed |
| **P1** | Entrance animation duration hardcoded → `GAME_CONSTANTS` | ✅ Fixed |
| **P2** | Scene UI triplication extracted to `ui/scene_rendering_utils.py` | ✅ Fixed |
| **P2** | 23 local imports moved to module level | ✅ Fixed |
| **P2** | 6 unused imports removed (plus 1 confirmed false positive) | ✅ Fixed |
| **P3** | Buff boilerplate compressed via class attributes | ✅ Fixed |
| **P3** | `print()` → `logging.error()` in event_bus.py | ✅ Fixed |
| **P4** | Duplicated boolean expression extracted in login_scene.py | ✅ Fixed |
| **P3** | `utils/sprites.py` god module | ✅ Fixed — split into `_sprites_common.py`, `_sprites_ships.py`, `_sprites_bullets.py` |
| **P3** | HUD renderer 12-parameter threading | ❌ Unresolved |
| **P4** | Scattered magic numbers in UI positioning/sizing | ❌ Unresolved |
| **P4** | Unexplained movement parameters in `enemy.py` | ❌ Unresolved |
| **P4** | Wildcard import in `config/__init__.py` | ❌ Unresolved |
| **P2** | `pygame.SCALED` flag missing → HW-accelerated display | ✅ Fixed |
| **P2** | SRCALPHA surface caching in `EffectsRenderer.render_chamfered_rect` | ✅ Fixed |
| **P2** | SRCALPHA surface caching in `draw_chamfered_panel` | ✅ Fixed |
| **P2** | SRCALPHA reuse in `Player._render_hitbox_indicator` | ✅ Fixed |
| **P2** | SRCALPHA caching in `SegmentedProgressBar` segments/glow/pulse | ✅ Fixed |

---

## Table of Contents

1. [Magic Numbers](#1-magic-numbers)
2. [Long Functions & Deep Nesting](#2-long-functions--deep-nesting)
3. [God Classes & God Modules](#3-god-classes--god-modules)
4. [Import & Naming Issues](#4-import--naming-issues)
5. [Code Duplication](#5-code-duplication)
6. [Dead Code](#6-dead-code)
7. [Other Issues](#7-other-issues)
8. [Priority Recommendations](#8-priority-recommendations)

---

## 1. Magic Numbers

### 1.1 Constants That Exist but Aren't Used (Hardcoded Instead)

| File | Line(s) | Hardcoded Value | Existing Constant |
|------|---------|-----------------|-------------------|
| `game/managers/collision_controller.py` | 377 | `20` (enemy collision damage) | `GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE` |
| `game/managers/collision_controller.py` | 409 | `30` (boss collision damage) | `GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE` |
| `game/managers/game_controller.py` | 29 | `60` (entrance animation frames) | `GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION` |
| `game/scene_director.py` | 57,80,118,191,262,298 | `60` (FPS tick rate, repeated 6×) | `GameConfig.fps` |
| `game/rendering/game_renderer.py` | 40,45 | `(10,10,30)` (fallback bg color) | `Colors` class in design_tokens.py |

### 1.2 Duplicated Configuration Dicts

| Data | Location 1 | Location 2 |
|------|-----------|-----------|
| `{'easy':1, 'medium':2, 'hard':3}` | `game/managers/game_controller.py:46` | `scenes/game_scene.py:602` |

### 1.3 Unexplained Movement Parameters (enemy.py)

The `Enemy` class has six movement patterns with raw numeric literals at lines 277-314 that have no named constants or comments:

| Pattern | Line | Magic Numbers |
|---------|------|---------------|
| Hover | 298 | `0.08` (timer increment) |
| Hover | 300 | `0.7`, `0.5` (frequency, amplitude) |
| Spiral | 305-306 | `0.5`, `2`, `0.3` (radius, freq, amp) |
| Straight | 314 | `0.05`, `0.3` (oscillation freq/amp) |
| Sine | 277 | `0.5` (vertical sine divisor) |
| Zigzag | 287 | `0.1`, `0.5` (sine freq, amp factor) |
| Dive | 292 | `0.05`, `0.3` (sine freq, amp factor) |
| Dive | 294 | `0.03`, `0.3` (secondary sine factors) |

Additionally, V-formation spawn logic (lines 500-530) hardcodes `140`, `50`, `40`, `80`, `0.40`, `0.70` — raw positioning numbers with no named constants, making formation layout tuning difficult.

### 1.4 Scattered UI Dimensions

Hundreds of hardcoded positioning/sizing values across scene files and UI components. Many correspond to values defined in `design_tokens.py` (`Spacing`, `Typography`, `MilitaryUI`) but aren't referenced. Examples:

- Font sizes hardcoded as `Font(None, 36)`, `Font(None, 28)`, etc. instead of `Typography` constants
- Panel/button dimensions in `death_scene.py`, `pause_scene.py`, `exit_confirm_scene.py` — all hardcoded
- UI margins, offsets, and padding values used once and never named

---

## 2. Long Functions & Deep Nesting

### 2.1 Top 10 Longest Functions (>70 logic lines)

| Lines | File | Function | Issue |
|-------|------|----------|-------|
| 134 | `entities/enemy.py:155` | `Enemy.update` | Handles entry/exit animation, 6 movement patterns, firing, bounds — violates SRP |
| 133 | `utils/sprites.py:707` | `_draw_boss_ship` | Monolithic ship rendering |
| 128 | `utils/sprites.py:160` | `_draw_player_ship` | Monolithic ship rendering |
| 112 | `utils/sprites.py:333` | `_draw_enemy_ship` | Monolithic ship rendering |
| 92 | `ui/chamfered_panel.py:52` | `draw_chamfered_panel` | Panel drawing with too many options |
| 91 | `ui/hex_icon.py:135` | `_draw_icon_shape` | 7-branch elif chain for icon shapes |
| 83 | `ui/effects.py:84` | `render_chamfered_rect` | Overloaded renderer |
| 79 | `collision_controller.py:200` | `check_player_bullets_vs_enemies` | Complex collision logic |
| 74 | `scenes/game_scene.py:79` | `GameScene.enter` | Massive initialization |
| 71 | `collision_controller.py:118` | `check_all_collisions` | 13-parameter coordinator |

### 2.2 Deep Nesting (6+ levels)

| Depth | File:Line | Context |
|-------|-----------|---------|
| **10** | `ui/hex_icon.py:235` | `_draw_icon_shape` — 7 elif branches + for + if |
| **10** | `ui/game_over_screen.py:67` | `show` — while/for/if/elif chain |
| **9** | `game/scene_director.py:238` | Nested pause action handling |
| **8** | `scenes/login_scene.py:189` | Keyboard event dispatch |
| **7** | `entities/enemy.py:303` | Movement pattern branching inside update |
| **6** | `collision_controller.py:249` | Spatial hash collision inner loop |
| **6** | Several scene files | Event loop pattern: `while/for/if/elif/elif/elif/elif` |

**Common pattern**: Scene event dispatch uses `while` → `for` → `if/elif/elif/...` chains that create deep nesting. A dispatch table or strategy pattern could eliminate most of this.

### 2.3 Functions with Excessive Parameters (>10)

| Params | File:Line | Function |
|--------|-----------|----------|
| **13** | `collision_controller.py:118` | `check_all_collisions(player, enemies, boss, enemy_bullets, reward_system, player_invincible, score_multiplier, on_enemy_killed, on_boss_killed, on_boss_hit, on_player_hit, on_lifesteal, on_clear_bullets)` |
| **12** | `game/rendering/integrated_hud.py:58` | `IntegratedHud.render(surface, score, difficulty, player_health, player_max_health, kills, next_progress, boss_kills, unlocked_buffs, get_buff_color, current_coefficient, initial_coefficient)` |
| **12** | `game/rendering/hybrid_renderer.py:32` | `HybridRenderer.render_hud` (same set) |
| **12** | `game/rendering/game_renderer.py:114` | `GameRenderer.render_hud` (same set) |
| **11** | `ui/military_hud.py:439` | `render_complete_hud` |
| **10** | `game/managers/ui_manager.py:7` | `render_hud` |

**Root cause**: The same 12-parameter set is threaded through 4 renderer layers (`GameRenderer` → `HybridRenderer` → `IntegratedHud` → `MilitaryHUD`). A `HudState` dataclass would eliminate this.

---

## 3. God Classes & God Modules

| Lines | File | Contents |
|-------|------|----------|
| **868** | `utils/sprites.py` | God module — 15+ standalone drawing functions, 4 of which are >100 lines each |
| **860** | `entities/enemy.py` | `Enemy`, `EnemySpawner`, `BossData`, `Boss` — spawning, movement, rendering all mixed |
| **634** | `scenes/game_scene.py` | `GameScene` — init, update, render, pause layout, save/restore, events |
| **615** | `scenes/login_scene.py` | `LoginScene` — input/button rendering (normal + military), login/register logic, theming |
| **549** | `ui/buff_stats_panel.py` | `BuffStatsPanel` + `AttackModePanel` + `BuffStatsAggregator` |
| **522** | `ui/reward_selector.py` | `RewardSelector` — rendering, options, particles |
| **487** | `ui/military_hud.py` | `MilitaryHUD` — 6 separate rendering concerns in one class |
| **397** | `game/scene_director.py` | `SceneDirector` — main loop, pause, tutorial, game flow, exit confirm, save/load, resize |

---

## 4. Import & Naming Issues

### 4.1 Local Imports in Method Bodies — ✅ Fixed (2026-04-26)

Project rules prohibit `from airwar.*` imports inside methods (except for optional deps or circular imports with comments). All 23 violations were fixed by moving imports to module level (no circular dependencies found). The self-import in `game/constants.py` docstring was also removed.

### 4.2 Unused Imports — ✅ Fixed (2026-04-26)

| File | Unused Items | Status |
|------|-------------|--------|
| `config/design_tokens.py` | `Dict`, `Any` | Removed |
| `game/explosion_animation/explosion_manager.py` | `List`, `Optional`, `Callable` | Removed |
| `game/mother_ship/progress_bar_ui.py` | `Optional`, `Literal` | Removed |
| `scenes/game_scene.py` | `Tuple` | Removed |
| `game/managers/boss_manager.py` | `Optional`, `Callable` | Removed |
| `game/managers/milestone_manager.py` | `Optional`, `Callable` | **False positive** — both used at lines 60-61, 135 |
| `game/mother_ship/interfaces.py` | `Dict` | Removed |

### 4.3 Wildcard Import

- `config/__init__.py:1` — `from .settings import *` (mitigated by `__all__`, but still a wildcard)

### 4.4 Vague Variable Names

- `data` used as parameter/local var in `entities/bullet.py:37` (BulletData), `utils/database.py:23` (user dict), `utils/sprites.py` (raw pixel bytes)
- Single-letter variables (`p`, `r`, `b`, `e`) used across entire method bodies, not just comprehensions, in `reward_selector.py`, `menu_background.py`, `particles.py`

### 4.5 Built-in Name Shadowing

**No violations found.**

---

## 5. Code Duplication

### 5.1 Scene UI Triplication — ✅ Fixed (2026-04-26)

Three scene files had near-identical implementations extracted to shared utility:

- Created `ui/scene_rendering_utils.py` with `SceneRenderingUtils` class
- `_draw_glow_text`, `_draw_option_box`, `_draw_decorative_lines` unified with parameterized variations
- Removed ~26 lines of duplication from each of `death_scene.py`, `pause_scene.py`, `exit_confirm_scene.py`
- `menu_scene.py` also updated to use shared `draw_glow_text`
- Minor cosmetic differences handled via parameters (glow radius, alpha divisor, layer count)

### 5.2 Duplicated Guard Logic

`_can_use_give_up` is defined in two places:
- `scenes/game_scene.py:287-292`
- `game/managers/input_coordinator.py:74-79`

Both check `controller.is_playing()` AND `not controller.state.paused` AND `not reward_selector.visible`.

### 5.3 Buff Boilerplate — ✅ Fixed (2026-04-26)

All 17 buff classes now use class-level attributes:
- `NAME` and `COLOR` added to `Buff` base class with default implementations
- `get_name()` and `get_color()` removed from all subclasses
- `get_notification()` now has base default returning `f'REWARD: {self.NAME}'`
- Only 9 subclasses with custom notification logic keep `get_notification()` overrides
- Total reduction: ~200 lines of boilerplate

---

## 6. Dead Code — ✅ Fixed (2026-04-26)

All 8 unused functions were removed:
- `clear_sprite_caches()` — removed from `utils/sprites.py`
- `clear_particle_glow_cache()` — removed from `explosion_effect.py`
- `get_typography()`, `get_spacing()`, `get_animation()` — removed from `config/design_tokens.py` + `__all__` updated
- `clear_chamfered_cache()` — removed from `ui/chamfered_panel.py`
- `GameRenderingBackground.clear_all_caches()` — removed from `game_rendering_background.py`
- `get_adaptive_screen_size()` — removed from `config/settings.py`

---

## 7. Other Issues

### 7.1 Bug: Nonexistent Design Token References — ✅ Fixed (2026-04-26)

Added `SCANLINE_ALPHA = 25` and `SCANLINE_SPACING = 4` to `MilitaryUI` class in `config/design_tokens.py`.

### 7.2 Print Statement in Production Code — ✅ Fixed (2026-04-26)

`game/mother_ship/event_bus.py:27`:
```python
# Before:
print(f"Event callback error [{event}]: {e}")
# After:
logging.error(f"Event callback error [{event}]: {e}")
```

### 7.3 Complex Boolean Expressions

- `scenes/login_scene.py:598,600`: ✅ Fixed — extracted to `_is_error_message()` helper method
- `scenes/game_scene.py:585`: ❌ Unresolved
- `game/scene_director.py:344,375`: ❌ Unresolved
- `game/mother_ship/game_integrator.py`: ❌ Unresolved

### 7.4 Mutable Default Arguments

**No violations found.**

### 7.5 Per-Frame SRCALPHA Surface Allocations — ✅ Fixed (2026-04-26)

Performance profiling identified ~50 SRCALPHA surface creations per frame as the primary bottleneck (each `pygame.Surface((w, h), pygame.SRCALPHA)` + `.fill()` allocates and clears GPU memory).

**Fixes applied:**

| File | Before | After | Improvement |
|------|--------|-------|-------------|
| `ui/effects.py:render_chamfered_rect` | 6 SRCALPHA surfaces per call (glow ×4, bg, border) | Fully cached by (width, height, color) keys | ~5 fewer allocs/call |
| `ui/chamfered_panel.py:draw_chamfered_panel` | 4 SRCALPHA surfaces + 3 `_create_chamfered_surface` calls | Replaced with `_get_chamfered_surface` (cached) + `.copy()`; dead `glow_result` removed | ~6 fewer allocs/call |
| `entities/player.py:_render_hitbox_indicator` | 1 SRCALPHA per frame (every frame when invincible) | Surface reused via instance attr, only `fill()` per frame | 0 allocs after first |
| `ui/segmented_bar.py:_draw_chamfered_segment` | 1 SRCALPHA per segment per frame | Cached by (width, height, fill_color, border_color) | ~N fewer allocs/frame |
| `ui/segmented_bar.py:render_with_glow` | 1 SRCALPHA per call | Cached by (width, height, glow_color) | ~1 fewer alloc/call |
| `ui/segmented_bar.py:render_danger_pulse` | 1 SRCALPHA per call | Surface reused via instance attr | 0 allocs after first |

**Additional performance fix:**
- `window/window.py`: All 4 `pygame.display.set_mode()` calls now include `pygame.SCALED` flag for SDL2 hardware-accelerated display scaling.

---

## 8. Priority Recommendations

| Pri | Issue | Impact | Suggested Fix | Status |
|-----|-------|--------|---------------|--------|
| **P0** | `MilitaryUI.SCANLINE_*` missing in `design_tokens.py` | Runtime `AttributeError` | Add the missing attributes or fix the references | ✅ Fixed |
| **P1** | Collision damage hardcoded despite existing constants | Inconsistency, tuning confusion | Replace with `GAME_CONSTANTS.DAMAGE.*` | ✅ Fixed |
| **P1** | 8 dead-code functions | Maintenance burden | Remove unreferenced functions | ✅ Fixed |
| **P1** | FPS tick rate hardcoded in scene_director.py (7×) | Inconsistency | Replace with `FPS` constant | ✅ Fixed |
| **P1** | Entrance animation duration hardcoded | Redundant literal | Use `GAME_CONSTANTS.ANIMATION.ENTRANCE_DURATION` | ✅ Fixed |
| **P2** | Scene UI triplication (3 scene files) | ~78 lines of copy-paste per file | Extract shared utility | ✅ Fixed |
| **P2** | `Enemy.update` — 134 lines, 6 movement types | Hard to debug, test, or extend | Extract `MovementStrategy` hierarchy | ❌ Unresolved |
| **P2** | 23 local imports in method bodies | Import convention violation | Move to module level | ✅ Fixed |
| **P2** | 6 unused imports | Dead code | Remove from import lines | ✅ Fixed |
| **P3** | Buff boilerplate (17 classes × 3 methods) | ~200 lines of repetition | Use class attributes on base class | ✅ Fixed |
| **P3** | `utils/sprites.py` 868-line god module | Poor discoverability | Split into entity-specific sprite modules | ❌ Unresolved |
| **P3** | HUD renderer 12-parameter threading | Fragile, hard to refactor | Introduce `HudState` dataclass | ❌ Unresolved |
| **P3** | `print()` in event_bus.py | Not suitable for production | Replace with `logging.error()` | ✅ Fixed |
| **P3** | Wildcard import in `config/__init__.py` | Namespace pollution risk | Use explicit imports | ❌ Unresolved |
| **P4** | Scattered magic numbers in positioning/sizing | Hard to tune UI consistently | Migrate to `design_tokens.py` constants | ❌ Unresolved |
| **P4** | Unexplained movement parameters in `enemy.py` | Opaque tuning | Name constants with descriptive identifiers | ❌ Unresolved |
| **P4** | Complex boolean: duplicated error check in login_scene.py | Readability | Extract to `_is_error_message()` | ✅ Fixed |

---

*Generated by automated code quality audit. Each finding should be verified manually before acting on it.*
