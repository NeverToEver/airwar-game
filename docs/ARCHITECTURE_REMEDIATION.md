# Architecture Remediation Plan

## Objective

Remove the achievement feature, establish one authoritative save path and
time source, and begin separating gameplay session state from `GameScene`.
The playable flow remains Welcome -> Game -> Pause/Death/Menu -> Exit.

## Scope And Invariants

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

## Work Items

- [completed] Document the implementation plan and acceptance criteria.
- [completed] Remove the achievement subsystem and its runtime wiring.
- [completed] Create and inject one game-save service for all save triggers.
- [completed] Add a frame-time context and migrate active gameplay timing.
- [completed] Introduce `GameSession` as the first composition boundary.
- [completed] Run lint, compilation, and focused lifecycle checks.

## Acceptance Criteria

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

## Implementation Notes

- `GameSaveService` is the only gameplay-level constructor of
  `PersistenceManager`. It is created by `SceneStatePersistence` and injected
  into the game scene for auto-save and base-loadout saves.
- `FrameClock` samples the window clock once per rendered frame and emits
  60 Hz simulation steps. Overlay scenes do not advance that clock, so paused
  gameplay timers cannot jump when the overlay closes.
- `GameSession` owns the collaborators created for one run. `GameScene`
  installs temporary compatibility attributes from that session while its
  downstream consumers are migrated incrementally.
