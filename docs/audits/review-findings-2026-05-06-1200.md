# Code Review: AirWar — Logic, Design, and Architecture

**Date:** 2026-05-06  
**Reviewers:** Claude Code (DeepSeek v4-pro) + Codex CLI (GPT-5.4-mini)  
**Branch:** master @ 3818214  
**Tests:** All passing (100%)

---

## Summary

- **Files reviewed:** 10+ core files
- **Issues found:** 9 (0 critical, 2 medium, 7 low)

---

## Logic Issues

### 1. [MEDIUM] Difficulty mismatch in restore_from_save
- **File:** `airwar/scenes/game_scene.py:1300`
- `restore_from_save()` overwrites `state.difficulty` but GameController, RewardSystem, and SpawnController were already constructed from the menu difficulty in `enter()`. Loaded saves can run with mixed balance rules — the difficulty-dependent systems (spawn rates, damage scaling) do not reflect the saved difficulty.

### 2. [MEDIUM] Shielded hits trigger ripple and invincibility
- **File:** `airwar/game/managers/game_controller.py:162`
- `on_player_hit()` does not check `is_shielded` before generating ripple effects and granting invincibility frames. Blocked hits produce visual and state feedback as if real damage occurred.

### 3. [LOW] activate_shield does not clamp duration
- **File:** `airwar/entities/player.py:264`
- `activate_shield(duration)` accepts zero or negative `duration`, which never ticks down, leaving the shield permanently on.

### 4. [LOW] activate_laser ignores duration parameter
- **File:** `airwar/entities/player.py:210`
- `activate_laser(duration)` receives a `duration` parameter but never stores or uses it. The laser buff is effectively permanent; the parameter is misleading.

---

## Game Design Issues

### 5. [MEDIUM] Bullet clear on hit removes all follow-up pressure
- **File:** `airwar/scenes/game_scene.py:482`
- Every player hit clears ALL enemy bullets. This makes the difficulty curve inconsistent — getting hit creates a "safe zone" and removes tension, particularly undermining Hard mode.

### 6. [LOW] Loading screen never renders
- **File:** `airwar/scenes/game_scene.py:163`
- `_is_loading` is set to `False` inside `enter()` before the first `render()` call. The loading screen code path in `render()` is dead code.

---

## Architecture Issues

### 7. [LOW] Duplicate HealthSystem with no clear owner
- **File:** `airwar/scenes/game_scene.py:177`
- GameScene creates its own `HealthSystem(difficulty)`, but GameController already owns the authoritative one inside `health_system`. Two instances coexist with no clear ownership.

### 8. [LOW] Access to private field breaks encapsulation
- **File:** `airwar/scenes/game_scene.py:1369`
- `_restore_to_mothership_state()` accesses `GameIntegrator._mother_ship` (private field), tightly coupling the scene to GameIntegrator internals.

### 9. [LOW] Bare except swallows errors silently
- **File:** `airwar/game/mother_ship/event_bus.py:67`
- `except Exception` catches all exceptions when invoking event callbacks, silently swallowing errors that could mask real bugs in event handlers.

---

## Rules Applied

- Architectural Pattern: Layer boundaries, encapsulation
- Error Handling Principles: Never swallow exceptions silently
- Game Design Principles: Consistent difficulty curve, meaningful player feedback
