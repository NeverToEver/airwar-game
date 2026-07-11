# Contributing to Air War

Thank you for your interest in improving Air War! This is a hobby project, but contributions of all kinds — bug reports, documentation, code, or feedback — are welcome.

## Reporting Issues

- Use [GitHub Issues](../../issues).
- Include your OS, Python version, and how you launched the game.
- Attach the log file at `~/.cache/airwar/airwar.log` when relevant.

## Development Setup

```bash
git clone git@github.com:NeverToEver/airwar-game.git
cd airwar-game
pip install -r requirements-dev.txt

# Optional: build the Rust extension
cd airwar_core && maturin develop --release && cd ..
```

## Before Submitting a PR

1. Run the test suite:

   ```bash
   python3 -m pytest tests/
   ```

2. Run the linter:

   ```bash
   python3 -m ruff check .
   ```

3. Run the bytecode check:

   ```bash
   python3 -m compileall -q airwar main.py
   ```

4. If you changed gameplay logic, please also run the game manually and verify the affected flow.

## Code Style

- Target Python 3.12.
- Line width: 120.
- Keep changes minimal and focused.
- Match the existing code style around your change.
- Add type annotations for new code when practical.

## Screenshots in README

If you update UI or scenes, you can regenerate the README screenshots:

```bash
SDL_VIDEODRIVER=dummy python3 scripts/capture_screenshots.py
```

## Code of Conduct

Please read and follow our [Code of Conduct](./CODE_OF_CONDUCT.md).
