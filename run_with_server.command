#!/usr/bin/env bash
# macOS double-click launcher for AirWar + leaderboard server.
# Opens in Terminal.app and runs the combined server+game launcher.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec bash run_with_server.sh "$@"
