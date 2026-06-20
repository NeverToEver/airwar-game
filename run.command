#!/usr/bin/env bash
# macOS double-click launcher for AirWar.
# Opens in Terminal.app and runs the game via run.sh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec bash run.sh "$@"
