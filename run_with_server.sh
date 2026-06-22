#!/usr/bin/env bash
# Launch AirWar together with the local leaderboard server.
# The server runs in the background and is terminated when the game exits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Re-use the same Python resolution as run.sh, falling back to venv.
PYTHON=""
for candidate in .venv/bin/python python3.13 python3.12 python3.11 python3; do
    if [ -x "$candidate" ]; then
        ver=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[airwar-server] ERROR: Python >= 3.11 not found." >&2
    exit 1
fi

exec "$PYTHON" run_with_server.py "$@"
