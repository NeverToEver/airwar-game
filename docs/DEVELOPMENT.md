# Development Status

Air War is in an initialization-stage development cycle. The project is being
shaped around a stable playable loop, not release certification or renderer
migration.

## Current Scope

The maintained runtime path is:

1. Start the application.
2. Choose a player and difficulty from the welcome scene.
3. Optionally enter the tutorial or settings.
4. Run the game scene, including combat, pause, death, save/restore, and
   mothership flow.
5. Return to the welcome scene or exit cleanly.

The leaderboard remains an optional player-facing feature. Rust bindings remain
an optional acceleration layer with their existing Python fallback.

## Development Rules

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
