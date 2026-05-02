# Code Audit Report

**Date:** 2026-05-03  
**Scope:** `airwar/airwar/` (all `.py` files, excluding tests, `__pycache__`, `.venv`)  
**Methods:** Static analysis via grep + manual context review; 11 bug patterns across 2 scanning passes

---

## Summary

| Severity | Count | Description |
|----------|-------|-------------|
| High (crash) | 1 | `random.randint()` with float args — already fixed in this session |
| Medium (silent wrong behavior) | 1 | Boss wobble animation dead code due to premature `int()` truncation |
| Low (unused imports) | 15 | Dead imports across 15 files |
| Cosmetic | 2 | Style issues with no runtime impact |
| Clean | 8 patterns | No issues found in the other patterns scanned |

**Overall:** The codebase is in good shape. Only 2 real bugs found, both already fixed in this session. The 15 unused imports are the largest remaining clean-up target.

---

## 1. High Severity — Crashes

### 1.1 `random.randint()` float argument → `TypeError` crash

- **File:** `airwar/entities/enemy.py:830-837`
- **Status:** Fixed (this session, before audit)

Boss HOVER phase called `random.randint()` with `self.rect.x`/`self.rect.y` as range bounds. Pygame rects can hold float coordinates, and `randint` requires integers. Wrapped all 4 arguments with `int()`.

---

## 2. Medium Severity — Silent Wrong Behavior

### 2.1 Boss survival wobble animation has zero visual effect

- **File:** `airwar/entities/enemy.py:785`
- **Status:** Fixed (this session)

```python
# Before (broken):
self.rect.y += int(math.sin(self.survival_timer * 0.025) * 0.4)

# After (fixed):
self.rect.y += math.sin(self.survival_timer * 0.025) * 0.4
```

**Root cause:** `math.sin()` returns [-1.0, 1.0]. Multiplied by 0.4 gives [-0.4, 0.4]. `int()` truncates toward zero, so every value becomes `0`. The wobble was dead code — it compiled and ran but never moved the boss vertically.

`self.rect.y` is `float` (custom `Rect` dataclass), so the float result is safe without `int()`.

---

## 3. Low Severity — Unused Imports

These do not affect runtime behavior but add noise for maintainers and slightly slow module loading. All are safe to remove.

| # | File | Unused Import |
|---|------|---------------|
| 1 | `entities/bullet.py:9` | `Optional` from `typing` |
| 2 | `entities/bullet.py:12` | `SCREEN_HEIGHT` from `..config` |
| 3 | `game/rendering/integrated_hud.py:4` | `Dict`, `Any` from `typing` |
| 4 | `ui/buff_stats_panel.py:2` | `Any` from `typing` |
| 5 | `scenes/game_scene.py:4` | `Tuple` from `typing` |
| 6 | `game/mother_ship/mother_ship_state.py:3` | `Optional` from `typing` |
| 7 | `game/mother_ship/event_bus.py:3` | `Any` from `typing` |
| 8 | `game/mother_ship/game_integrator.py:2` | `Any` from `typing` |
| 9 | `game/buffs/base_buff.py:4` | `Optional` from `typing` |
| 10 | `game/rendering/hud_renderer.py:2` | `Optional` from `typing` |
| 11 | `ui/chamfered_panel.py:3` | `Optional` from `typing` |
| 12 | `ui/hex_icon.py:4` | `Optional` from `typing` |
| 13 | `ui/segmented_bar.py:3` | `Optional` from `typing` |
| 14 | `game/systems/reward_system.py:4` | `BUFF_REGISTRY` from `..buffs.buff_registry` |
| 15 | `ui/game_over_screen.py:3` | `Tuple` from `typing` |

All `__init__.py` re-export files were verified — their "unused" imports are intentional for the public API surface and are NOT listed above.

---

## 4. Cosmetic

### 4.1 `is True` instead of `== True`

- **File:** `game/scene_director.py:119`
- **Code:** `escape_handled = result is True`

`True` is a singleton in CPython so this works correctly, but PEP 8 recommends `==` for boolean value comparison. `is` should be reserved for `is None` / `is not None` singleton checks.

### 4.2 `pygame.Rect` construction with float args

4 locations pass float `self.rect.x`/`self.rect.y` into `pygame.Rect()` constructors (which silently truncate to int). Visual offset is ≤1 pixel — not noticeable during gameplay.

| File | Line | Context |
|------|------|---------|
| `entities/base.py` | 127 | `get_rect()` for rendering |
| `entities/player.py` | 200-203 | `get_hitbox()` for collision |
| `entities/enemy.py` | 431-433 | `_sync_rects()` collision rect drift |
| `game/managers/bullet_manager.py` | 199-200 | Laser trail positions |

---

## 5. Patterns Verified Clean

These 8 patterns were scanned across the entire codebase and found **zero issues**:

| Pattern | Result |
|---------|--------|
| `range()` with float arguments | 0 instances — all args are ints |
| Bare `except:` clauses | 0 instances — all exceptions specify a type |
| Mutable default arguments (`def f(x=[])`) | 0 instances |
| `is` with non-singleton values (`is 0`, `is ""`) | 0 instances |
| Float division where `//` intended | 0 instances — all `/` uses are in float-safe contexts |
| Dangerous `dict.get()` defaults | 0 instances — all safe |
| List/dict indexing with floats | 0 instances |
| `except Exception:` (overly broad) | 1 instance (`event_bus.py:33`), justified for event dispatch safety |

---

## 6. Already Fixed in Prior Commit (e4d526f)

The following issues noted in the prior commit's audit were verified as resolved:

- Input validation on login (username length, guest name sanitization)
- File I/O error handling in `PersistenceManager` and `UserDB`
- Dead code removal in `scene.py` (state persistence API) and `game_scene.py` (duplicate pause API)

---

## 7. Recommendation

**Do now:** Nothing critical remains. The two real bugs found in this audit (Boss `randint` float crash, Boss wobble dead code) are already fixed in this session.

**Nice to have:** Clean up the 15 unused imports. They're low-risk and can be done in a single pass — each change is just deleting a name from an import line.
