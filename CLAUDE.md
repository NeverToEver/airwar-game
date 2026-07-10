# Air War Development Guide

Air War is in active initialization. Preserve a stable playable loop while
individual systems are still being formed.

## Runtime Path

Welcome -> tutorial/settings or game -> pause/death/menu -> exit.

Combat, persistence, mothership flow, localization, and the optional
leaderboard are part of the current application. Do not replace these systems
with broad rewrites while their gameplay behavior is still being developed.

## Working Rules

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

The current development status is maintained in `docs/DEVELOPMENT.md`.
