# Air War Agent Guide

This document consolidates the information coding agents need when working on Air
War.

---

## Development Guide

Air War is in active initialization. Preserve a stable playable loop while
individual systems are still being formed.

### Runtime Path

Welcome -> tutorial/settings or game -> pause/death/menu -> exit.

Combat, persistence, mothership flow, localization, and the optional
leaderboard are part of the current application. Do not replace these systems
with broad rewrites while their gameplay behavior is still being developed.

### Working Rules

- Keep changes local and directly useful to the current runtime.
- Prefer existing Pygame and project helpers over new abstraction layers.
- Keep Rust acceleration optional; Python fallback behavior must remain usable.
- Run the game manually after gameplay, scene, input, rendering, persistence,
  or UI changes.
- Before handoff, run:

```bash
python3 -m pytest tests/
python3 -m ruff check .
python3 -m compileall -q airwar main.py tests
```

The current development status is maintained in the "Development Status"
section below.

---

## Development Status

Air War is in an initialization-stage development cycle. The project is being
shaped around a stable playable loop, not release certification or renderer
migration.

### Current Scope

The maintained runtime path is:

1. Start the application.
2. Choose a player and difficulty from the welcome scene.
3. Optionally enter the tutorial or settings.
4. Run the game scene, including combat, pause, death, save/restore, and
   mothership flow.
5. Return to the welcome scene or exit cleanly.

The leaderboard remains an optional player-facing feature. Rust bindings remain
an optional acceleration layer with their existing Python fallback.

### Development Rules

- Make small changes that preserve the playable loop above.
- Prefer direct Pygame/Python code over new layers, adapters, or generic
  frameworks unless an existing runtime consumer requires them.
- Keep new behavior local to its owning scene, entity, or game system.
- Use a manual game run after changes that affect input, scene transitions,
  combat, rendering, save data, or UI layout.
- Run `python3 -m pytest tests/`, `python3 -m ruff check .`, and
  `python3 -m compileall -q airwar main.py tests` before handing off a change.

Avoid broad refactors whose benefit cannot be observed in the current playable
loop. Update this document only when the active development scope changes.

---

## Architecture Remediation Plan

### Objective

Remove the achievement feature, establish one authoritative save path and
time source, and begin separating gameplay session state from `GameScene`.
The playable flow remains Welcome -> Game -> Pause/Death/Menu -> Exit.

### Scope And Invariants

1. Remove achievement registry code, event subscriptions, game-over
   evaluation, and achievement-specific UI/runtime dependencies. Leaderboard
   and player statistics remain independent features.
2. Every save operation (manual, quit, auto-save, and base-loadout save) must
   use the same injected persistence service and therefore the same save
   directory and username policy.
3. Each frame obtains elapsed time exactly once from the window clock. Runtime
   gameplay systems receive that value through a shared frame context. Timers
   migrated in this change must no longer depend on rendered frame count.
4. `GameScene` remains the compatibility facade for now. A `GameSession`
   composition object owns the initialized gameplay collaborators so new code
   does not add more scene-level state fields.

### Work Items

- [completed] Document the implementation plan and acceptance criteria.
- [completed] Remove the achievement subsystem and its runtime wiring.
- [completed] Create and inject one game-save service for all save triggers.
- [completed] Add a frame-time context and migrate active gameplay timing.
- [completed] Introduce `GameSession` as the first composition boundary.
- [completed] Run lint, compilation, and focused lifecycle checks.

### Acceptance Criteria

- No runtime import or reference to the achievement registry or achievement
  notification remains.
- Save triggers call one service instance configured by `SceneDirector`; no
  gameplay code constructs `PersistenceManager` directly.
- A frame's `dt` is read once, clamped, and supplied to gameplay updates.
  Autosave, mothership firing, and hold detectors use elapsed seconds.
- `GameSceneFactory` returns a typed session object rather than mutating a
  scene as its primary construction contract.
- `python3 -m ruff check .` and
  `python3 -m compileall -q airwar main.py` pass.

### Implementation Notes

- `GameSaveService` is the only gameplay-level constructor of
  `PersistenceManager`. It is created by `SceneStatePersistence` and injected
  into the game scene for auto-save and base-loadout saves.
- `FrameClock` samples the window clock once per rendered frame and emits
  60 Hz simulation steps. Overlay scenes do not advance that clock, so paused
  gameplay timers cannot jump when the overlay closes.
- `GameSession` owns the collaborators created for one run. `GameScene`
  installs temporary compatibility attributes from that session while its
  downstream consumers are migrated incrementally.

---

## SOLID Frame Clock Refactor

### Defect

`FrameClock.advance()` rounds `wall_dt / fixed_dt` independently for every
rendered frame. Fractional time is discarded. At a steady 50 FPS, each 20 ms
frame produces one 16.67 ms simulation step, so the game advances only 1.67
seconds during two seconds of real gameplay.

### Design

`FrameContext` remains an immutable transport object. A new
`SimulationStepScheduler` protocol owns the policy that turns sampled wall
time into fixed simulation steps. `FixedStepAccumulator` is the production
implementation: it clamps oversized wall deltas, retains fractional remainder,
and advances simulation time only by emitted fixed steps.

`FrameClock` becomes a small coordinator over that abstraction. This gives it
one responsibility and makes alternative policies (for replay or deterministic
tests) injectable without changing scene orchestration.

### Acceptance Criteria

- Repeated 20 ms samples emit 120 fixed steps over roughly two seconds.
- Fractional time remains in the accumulator rather than being rounded away.
- `simulate=False` emits no steps and leaves both elapsed simulation time and
  the remainder unchanged.
- The scene switcher depends only on `FrameClock`'s public API.
- Lint, compilation, targeted cadence checks, and headless application
  lifecycle checks pass.

### Work Items

- [completed] Document defect, design, and acceptance criteria.
- [completed] Implement the scheduling abstraction and accumulator.
- [completed] Wire the existing frame clock to the abstraction.
- [completed] Verify cadence and runtime lifecycle.
