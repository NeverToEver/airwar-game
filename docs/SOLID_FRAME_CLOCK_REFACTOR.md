# SOLID Frame Clock Refactor

## Defect

`FrameClock.advance()` rounds `wall_dt / fixed_dt` independently for every
rendered frame. Fractional time is discarded. At a steady 50 FPS, each 20 ms
frame produces one 16.67 ms simulation step, so the game advances only 1.67
seconds during two seconds of real gameplay.

## Design

`FrameContext` remains an immutable transport object. A new
`SimulationStepScheduler` protocol owns the policy that turns sampled wall
time into fixed simulation steps. `FixedStepAccumulator` is the production
implementation: it clamps oversized wall deltas, retains fractional remainder,
and advances simulation time only by emitted fixed steps.

`FrameClock` becomes a small coordinator over that abstraction. This gives it
one responsibility and makes alternative policies (for replay or deterministic
tests) injectable without changing scene orchestration.

## Acceptance Criteria

- Repeated 20 ms samples emit 120 fixed steps over roughly two seconds.
- Fractional time remains in the accumulator rather than being rounded away.
- `simulate=False` emits no steps and leaves both elapsed simulation time and
  the remainder unchanged.
- The scene switcher depends only on `FrameClock`'s public API.
- Lint, compilation, targeted cadence checks, and headless application
  lifecycle checks pass.

## Work Items

- [completed] Document defect, design, and acceptance criteria.
- [completed] Implement the scheduling abstraction and accumulator.
- [completed] Wire the existing frame clock to the abstraction.
- [completed] Verify cadence and runtime lifecycle.
