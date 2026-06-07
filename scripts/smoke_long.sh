#!/usr/bin/env bash
# 60-second real-machine smoke test for airwar-game.
#
# Wraps scripts/smoke_real.sh with a default 60s duration (production target)
# instead of the 3s CI-friendly default. Auto-detects SDL_VIDEODRIVER based on
# platform, captures pytest output, and prints a clear pass/fail summary.
#
# Usage:
#   ./scripts/smoke_long.sh                          # 60s run, auto driver
#   SDL_VIDEODRIVER=wayland ./scripts/smoke_long.sh  # force a driver
#   AIRWAR_SMOKE_DURATION=30 ./scripts/smoke_long.sh # override duration
#
# Exits 0 on pass, 1 on failure (with tail of pytest output for debugging).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Default to 60s (production target) when not provided. Allow override via
# env var so callers can shorten it for quick local checks.
export AIRWAR_SMOKE_DURATION="${AIRWAR_SMOKE_DURATION:-60}"

# Auto-detect a real SDL display driver when the caller hasn't picked one
# (or has explicitly cleared it back to "dummy"). Skip detection when the
# user forces something other than "dummy".
if [[ -z "${SDL_VIDEODRIVER:-}" || "${SDL_VIDEODRIVER}" == "dummy" ]]; then
    case "$(uname -s)" in
        Darwin)
            export SDL_VIDEODRIVER="cocoa"
            ;;
        Linux)
            export SDL_VIDEODRIVER="x11"
            ;;
        *)
            echo "[smoke_long] WARNING: unknown platform $(uname -s); leaving SDL_VIDEODRIVER unset" >&2
            ;;
    esac
fi

# Quiet audio backend unless caller already set one.
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"

LOG_FILE="$(mktemp -t smoke_long.XXXXXX.log)"
trap 'rm -f "$LOG_FILE"' EXIT

echo "[smoke_long] SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-<unset>}"
echo "[smoke_long] AIRWAR_SMOKE_DURATION=${AIRWAR_SMOKE_DURATION}s"
echo "[smoke_long] Project root: ${PROJECT_ROOT}"
echo "[smoke_long] Log file: ${LOG_FILE}"

# Delegate to smoke_real.sh so the actual pytest invocation (and its CLI
# flags) stay in one place. Append its full output to the log for diagnosis.
set +e
bash "${SCRIPT_DIR}/smoke_real.sh" "$@" 2>&1 | tee "${LOG_FILE}"
status=${PIPESTATUS[0]}
set -e

if [[ "${status}" -eq 0 ]]; then
    echo "=== 60s SMOKE: pass ==="
    exit 0
fi

echo "=== 60s SMOKE: FAIL ==="
echo "[smoke_long] pytest exited with status ${status}"
echo "[smoke_long] Last 60 lines of output:"
tail -n 60 "${LOG_FILE}" || true
exit 1
