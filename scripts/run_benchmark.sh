#!/usr/bin/env bash
# Run the full benchmark suite locally (mirrors CI's slow tests).
#
# Usage:
#   ./scripts/run_benchmark.sh            # full suite
#   ./scripts/run_benchmark.sh --scenarios # scenarios only
#   ./scripts/run_benchmark.sh --visual   # visual regression only
#
# Output: pytest's standard pass/fail report.  Exit code 0 on success.

set -euo pipefail
cd "$(dirname "$0")/.."

# Headless mode: dummy SDL driver + no audio.  Matches conftest.py.
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-dummy}"

LAYER_FILTER="${1:-}"

if [[ "$LAYER_FILTER" == "--scenarios" ]]; then
    exec python3 -m pytest airwar/tests/benchmark/test_scenarios.py -m slow -v
elif [[ "$LAYER_FILTER" == "--visual" ]]; then
    exec python3 -m pytest airwar/tests/benchmark/test_visual.py -m slow -v
elif [[ "$LAYER_FILTER" == "--fuzz" ]]; then
    exec python3 -m pytest airwar/tests/benchmark/test_fuzz.py -m slow -v
else
    exec python3 -m pytest airwar/tests/benchmark/ -m slow -v
fi
