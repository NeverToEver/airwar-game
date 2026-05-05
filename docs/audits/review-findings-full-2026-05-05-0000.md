# Code Review: Full Codebase Audit (Consolidated)
Date: 2026-05-05
Reviewer: AI Agent (fresh context)
Merged sources:
- `review-findings-full-2026-05-05-0000.md` — initial full-codebase audit.
- `review-findings-full-joint-2026-05-05-1713.md` — joint follow-up audit and first maintenance pass, merged here to avoid audit document sprawl.

## Summary
- **Files reviewed:** ~97 Python source files + 7 Rust source files (~26,000 lines)
- **Test files:** 25 test files covering core, UI, entities, managers, systems
- **Issues tracked after consolidation:** 49 (1 critical, 26 major, 19 minor, 3 nit)
- **Open items after first maintenance pass:** 8 (3 major, 5 minor/documentation)
- **Remediation update:** Completed items are checked below. Partial items are annotated inline.
- **Verification after latest maintenance pass:** `.venv/bin/python -m ruff check .`, `.venv/bin/python -m compileall -q airwar main.py`, `.venv/bin/python -m pytest` (211 passed), `cargo test --manifest-path airwar_core/Cargo.toml` (27 passed), `git diff --check`.

## Critical Issues
No open critical issues remain.

- [x] **[DATA]** `game/scene_director.py` — “save and quit” followed by the exit confirmation default action “return to main menu” deleted the just-saved progress. **REMEDIATED:** `saved=True` now preserves the save when returning to the main menu; unsaved exits still clear old saves. Covered by `airwar/tests/test_scene_director.py::test_exit_confirm_return_to_menu_keeps_successful_save` and `airwar/tests/test_scene_director.py::test_exit_confirm_return_to_menu_clears_unsaved_exit`.

---

## Major Issues

### Cross-Layer Supplemental Findings

- [x] **[INT/LOGIC]** `game/managers/collision_controller.py` / `airwar_core/src/collision.rs` — Rust batch collision used `(center, max(width, height) / 2)` square approximation while Python used true rectangle `colliderect`, causing false positives for thin/wide hitboxes. **REMEDIATED:** batch collision now passes `(id, left, top, width, height)` and Rust uses true rectangular AABB. Covered by `airwar/tests/test_collision_controller.py::test_rust_collision_data_uses_rect_dimensions_not_square_radius` and Rust `test_batch_collision_uses_rect_bounds_not_square_radius`.
- [x] **[LOGIC]** `game/managers/collision_controller.py` — piercing bullets could damage the same enemy on every frame while overlapping the hitbox; `Bullet.has_hit_enemy()` / `add_hit_enemy()` existed but were unused. **REMEDIATED:** piercing hits are deduplicated in the shared collision application path for both Python and Rust batch results. Covered by `airwar/tests/test_collision_controller.py::test_piercing_bullet_does_not_damage_same_enemy_twice`.
- [x] **[UI/ERR]** `scenes/welcome_scene.py` — delete-account confirmation rendered `delete_confirm_yes/no` buttons but did not route those names in the button dispatch table; modal mouse clicks could also fall through to underlying controls. **REMEDIATED:** delete confirm buttons are routed and the delete modal now owns mouse clicks while open. Covered by `airwar/tests/test_welcome_login_layout.py::test_delete_confirm_buttons_delete_or_cancel_user`.
- [ ] **[SEC/CFG]** `utils/database.py`, `game/mother_ship/persistence_manager.py`, `utils/generated_asset_cache.py`, `build_linux.sh`, `build_macos.sh` — runtime user data, saves, and generated asset caches default to `airwar/data`, while build scripts package `airwar/data` wholesale. This can ship local `users.json`, save files, and generated caches in PyInstaller artifacts. Move runtime data to an OS user-data directory and package only static assets.
- [ ] **[INT/ARCH]** `game/mother_ship/event_bus.py`, `input_detector.py`, `game_integrator.py`, `scenes/game_scene.py` — mothership events include `EVENT_SAVE_GAME_REQUEST` with a subscriber but no publisher, and `EVENT_DOCKING_COMPLETE` with a publisher but no subscriber. The dormant save handler pauses the scene; if wired later, `GameScene.update()` would stop updating the integrator while paused. Clarify the docking/save contract and delete or document dead events.
- [ ] **[ARCH]** `scenes/game_scene.py` — still acts as a 1500+ line cross-system coordinator for rendering, HUD, collision, mothership, homecoming, pause, rewards, save/restore, and overlays. Continue extracting small flow coordinators around save flow, mothership scene adaptation, and overlay orchestration.

### Architecture & Layer Violations

- [x] **[LAY]** `ui/base_talent_console.py:8` — UI directly imports `TalentBalanceManager` from game systems. UI should receive talent data as parameters, not import game system classes. **HIGH**
- [x] **[LAY]** `ui/homecoming_ui.py:7` — UI imports `HomecomingPhase`, `HomecomingSequence` from game layer.
- [x] **[LAY]** `ui/particles.py:6` — UI imports `GAME_CONSTANTS` from game engine.
- [x] **[LAY]** `ui/buff_stats_panel.py:68` — Hidden local import of `create_buff` from game buff system inside method body.
- [x] **[LAY]** `entities/enemy.py:3,8,12` — Entity imports font rendering, design tokens, and sprite drawing. Entities should be pure domain objects. **REMEDIATED:** entity drawing moved to `game/rendering/entity_renderer.py`; entity classes no longer import UI/font/sprite drawing modules.
- [x] **[LAY]** `entities/bullet.py:12` — Entity imports sprite drawing functions. **REMEDIATED:** bullet drawing/trail rendering moved to `game/rendering/entity_renderer.py`.
- [x] **[LAY]** `entities/enemy.py:815` — Local import of sprite drawing inside `render()` method.

### Observability

- [x] **[OBS]** `scenes/welcome_scene.py:292,319,327,358,379` — Five `except DatabaseError:` handlers set user-facing error messages but perform **no logging**. Disk-full or JSON-corruption failures are invisible to post-mortem debugging.

### Error Handling

- [x] **[ERR]** `game/mother_ship/event_bus.py:63` — All exceptions caught from all subscribers with no handler-removal mechanism. A permanently broken subscriber will fail silently on every event.
- [x] **[ERR]** `game/managers/game_loop_manager.py:238` — `except (ValueError, TypeError): continue` silently skips enemies during batch movement data building with no logging.

### Code Duplication

- [x] **[DUP]** `ui/chamfered_panel.py` / `ui/effects.py` — Chamfered panel rendering logic duplicated across two modules (~167 lines total). One should delegate to the other.
- [x] **[DUP]** `ui/scene_rendering_utils.py:draw_option_box` / `ui/effects.py:render_option_box` — Option box rendering duplicated with different parameter styles (~133 lines total).
- [x] **[DUP]** `game/scene_director.py:104-148` — Pause result dispatch logic duplicated verbatim across keyboard and mouse paths.

### Performance

- [x] **[PERF]** `game/managers/collision_controller.py:348-373` — `_handle_explosive_damage` loops over every active enemy per explosion, no spatial filtering. O(enemies × explosions) per frame.
- [x] **[PERF]** `game/managers/collision_controller.py:375-396` — Boss collision check iterates all player bullets every frame without spatial optimization.
- [x] **[PERF]** `game/managers/bullet_manager.py:207-215` — Laser trail uses `list.pop(0)` (O(n)). Should use `collections.deque` with `maxlen`.

### Pattern & Complexity

- [x] **[PAT]** `scenes/welcome_scene.py:220` — 14-branch if/elif chain for button click handling. Should use a dispatch dict.
- [x] **[PAT]** `entities/enemy.py:392` — 9-branch if/elif chain for movement type initialization. Factory pattern or config dict would be cleaner.
- [x] **[PAT]** `entities/enemy.py:160` — `Enemy.update()` is 123 lines handling entrance, active, exit states, Rust/Python dispatch, and firing. Split into 3-4 methods.
- [x] **[PAT]** `game/managers/collision_controller.py:249` — `check_player_bullets_vs_enemies()` is 83 lines with two separate code paths (Rust batch / Python fallback) in one function.

---

## Minor Issues

### Supplemental Maintenance / Process Findings

- [ ] **[TEST/CFG]** `.github/workflows/ci.yml` — CI builds and installs the Rust extension but does not run `cargo test --manifest-path airwar_core/Cargo.toml`. Add a dedicated Rust unit-test step so Rust-only regressions fail before Python integration.
- [ ] **[SUPPLY/CFG]** `requirements.txt`, `requirements-dev.txt`, `airwar_core/Cargo.toml`, `.gitignore` — dependency ranges plus ignored `Cargo.lock` make release builds less reproducible. Add an application build lock/constraints strategy and commit or explicitly validate the Rust lockfile policy.
- [ ] **[ERR/UX]** `scenes/game_scene.py:_try_auto_save` — autosave ignores the `PersistenceManager.save_game(...)` return value, so failures are log-only and invisible to the player. Surface a non-blocking notification or save-status indicator.
- [ ] **[TEST]** Cross-layer flow tests remain thin around save/exit lifecycle, modal mouse routing, Rust/Python collision parity, piercing hit dedupe, and build-artifact data exclusion. The first four now have regression tests; build artifact data exclusion and broader flow coverage remain open.

### Error Handling

- [x] `utils/database.py:54` — `except OSError: pass` silently swallows temp-file cleanup failures. Should at least log.
- [x] `game/systems/reward_system.py:314,364,407` — Three `except ValueError:` catch blocks silently continue with no logging.
- [x] `game/scene_director.py:356-358` — `_save_game_on_quit` ignores the return value of `_perform_save`. User may think progress was saved when it wasn't.

### Rust Extension

- [x] `airwar_core/src/particles.rs:95` — `.unwrap()` on `SystemTime::now().duration_since(UNIX_EPOCH)`. Use `.expect()` with a message.
- [x] `airwar_core/src/collision.rs:110-138` — `unsafe` SSE2 SIMD collision detection. Correctly scoped but should carry a SAFETY comment.

### Import Style

- [x] Multiple `__init__.py` files (`game/managers/__init__.py`, `game/__init__.py`, `config/__init__.py`) use absolute imports for same-package modules where relative imports are specified by coding standards.
- [x] 11 instances of local imports in method bodies (`import random`, `import math`, `from ... import`). These create per-call import overhead. Move to top-level. **REMEDIATED/REVIEWED:** non-lazy production local imports were moved; remaining local imports are lazy compatibility/config or `TYPE_CHECKING` imports.
- [x] 6 files use relative `..` imports for cross-package access where absolute `from airwar.` is required by coding standards. **REMEDIATED/REVIEWED:** touched cross-package imports now use `airwar.` absolute imports; same-package `airwar.game` internal imports were left in local style.

### Magic Numbers

- [x] `entities/enemy.py` — Hover timer scale `0.08` appears 5 times (lines 234, 241, 260, 373, 827). Should be a named constant.
- [x] `entities/enemy.py:462-472` — Movement parameters (`0.05`, `2.0`, `0.03`, etc.) hardcoded in ternary expression.
- [x] `ui/effects.py` — Glow layer counts (`3`, `4`), corner radius (`12`), alpha divisors (`50`, `60`) hardcoded throughout.

### Documentation

- [ ] 574 public classes/methods across all packages are missing docstrings. Most affected: `game/mother_ship/` (87), `entities/` (81), `game/systems/` (67). **DEFERRED:** left as documentation debt; broad mechanical docstring generation would add low-value noise and should be handled with targeted API documentation work.

### Other

- [x] `utils/sprites.py` — Private symbols (`_bytes_to_surface`, `_glow_circle_cache`, etc.) exported in `__all__`, contradicting underscore convention.
- [x] `game/managers/boss_manager.py` — `TYPE_CHECKING` imports use absolute paths for same-package modules.
- [x] `ui/buff_stats_panel.py:169-170` — Duplicate log line (same message logged twice in same except block).
- [x] `airwar_core/src/particles.rs:95` — `fast_rand()` uses `SystemTime` for seeding (RNG antipattern). Prefer a proper PRNG or at minimum seed from a cryptographic source once at module init.

---

## Nit

- [x] `airwar/core_bindings.py:1,5,44` — Chinese comments/docstrings. Coding standards specify English.
- [x] `game/controllers/__init__.py` — Deprecated compat shim with Chinese-language deprecation notice. Should be removed.
- [x] `airwar_core/src/particles.rs:92-96` — `use std::time::SystemTime` inside function body (Rust style: prefer top-of-module imports).

---

## Positive Findings (Strengths)

- **Security:** No hardcoded secrets, no eval/exec/subprocess, no pickle, PBKDF2 password hashing with random salt, constant-time comparison, atomic file writes throughout.
- **Error handling:** No bare `except:` clauses, no truly empty except blocks, all file I/O uses context managers, pygame always shuts down in `finally`.
- **Code quality:** No mutable default arguments, no dead code after return/raise, centralized `GameConstants` + `DesignTokens` system, extensive type annotations, clean Rust/Python fallback integration.
- **Performance:** Well-designed surface/font caching, Rust batch acceleration, spatial hash collision detection, pre-rendered caches for static UI elements.
- **Testing:** 25 test files covering core gameplay, entities, UI, managers, persistence, and Rust bindings. CI pipeline with lint, compile check, and test steps.

---

## Rules Applied

- Security review (OWASP Top 10 adapted for local game)
- Error handling principles (empty catch, swallowed errors, resource management)
- Architectural pattern conformance (layer boundaries, import conventions)
- Code organization (method ordering, local imports, docstrings)
- Performance anti-patterns (hot-path allocations, algorithmic complexity)
- Language-specific: Python (mutable defaults, magic numbers, closures), Rust (unsafe, unwrap, import style)

## Dimensions Covered (Zero-Findings Guard Attestation)

- **Authentication:** Password hashing with PBKDF2-SHA256 + random salt + constant-time comparison — verified in `utils/database.py:57-98`.
- **Input validation:** Keyboard input length-limited (16 chars), control characters filtered — verified in `scenes/welcome_scene.py:192-210`. Save data validated with type/range checks — verified in `persistence_manager.py:90-144`.
- **Data integrity:** Atomic writes (write-to-tmp-then-os.replace) — verified in `database.py:43-55` and `persistence_manager.py:63-88`.
- **Serialization:** JSON only, no pickle/marshal — verified via full-codebase grep.
- **Network:** No network code, no sockets, no HTTP — verified via full-codebase grep.
- **Dependency injection:** Constructor-based injection in managers (BossManager, GameController, etc.) — verified in `game/managers/`.
- **Resource cleanup:** All file handles use `with` context managers; pygame shutdown in `finally` block — verified in `game/game.py:45-51`.
- **Configuration:** Centralized constants in `GameConstants` dataclass and `DesignTokens` singleton — verified in `game/constants.py:297` and `config/design_tokens.py:449-455`.
- **Rust FFI safety:** All `#[pyfunction]` exports verified safe; `unsafe` block (SSE2 SIMD) is scoped and correct — verified in `airwar_core/src/collision.rs:110-138`.
- **Test coverage:** 25 test files present with CI enforcement — verified via test file listing and `.github/workflows/ci.yml`.

## Consolidation Notes

- `review-findings-full-joint-2026-05-05-1713.md` has been merged into this file and should not remain as a separate audit artifact.
- This file is now the canonical 2026-05-05 full-codebase audit. Continue checking items off here as maintenance proceeds.
