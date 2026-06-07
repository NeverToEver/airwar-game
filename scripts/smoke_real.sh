#!/usr/bin/env bash
# Real-machine smoke test for airwar-game.
#
# Runs the smoke test in airwar/tests/smoke_real_machine.py on a REAL SDL
# display (NOT the dummy driver). Use this on a developer machine to verify
# the game boots, runs, and shuts down cleanly without a graphical session
# attached.
#
# Usage:
#   ./scripts/smoke_real.sh                  # default 3-second run
#   AIRWAR_SMOKE_DURATION=60 ./scripts/smoke_real.sh   # full 60s target
#   SDL_VIDEODRIVER=cocoa ./scripts/smoke_real.sh      # macOS explicit
#   SDL_VIDEODRIVER=x11   ./scripts/smoke_real.sh      # Linux X11 explicit
#   SDL_VIDEODRIVER=wayland ./scripts/smoke_real.sh    # Linux Wayland explicit
#
# Exits 0 on pass, non-zero on test failure or if no display is available.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Force a real SDL display driver. The project conftest.py defaults to
# "dummy" for headless CI; we override that here. The smoke test itself
# contains a skipif guard that re-asserts this contract.
if [[ -z "${SDL_VIDEODRIVER:-}" || "${SDL_VIDEODRIVER}" == "dummy" ]]; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
        export SDL_VIDEODRIVER="cocoa"
    else
        export SDL_VIDEODRIVER="x11"
    fi
fi

# Skip the dummy audio backend if no audio device is present.
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"

# Show the chosen driver for log clarity.
echo "[smoke_real] SDL_VIDEODRIVER=${SDL_VIDEODRIVER}"
echo "[smoke_real] AIRWAR_SMOKE_DURATION=${AIRWAR_SMOKE_DURATION:-3.0}s"
echo "[smoke_real] Project root: ${PROJECT_ROOT}"

# Run only the smoke test file. -s prints all output (the test uses
# pygame.display, so any SDL error messages are useful diagnostics).
exec python3 -m pytest \
    airwar/tests/smoke_real_machine.py \
    -v \
    -s \
    --no-header \
    --color=yes \
    "$@"
