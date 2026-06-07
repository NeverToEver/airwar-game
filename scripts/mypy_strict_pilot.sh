#!/usr/bin/env bash
# mypy --strict pilot runner.
#
# Runs mypy --strict against a curated list of modules that pass cleanly
# under --strict (or that we are actively trying to bring into compliance).
# This is intentionally separate from the project-wide mypy invocation:
#
#   * The project-wide config keeps `disallow_untyped_defs = false` because
#     only ~10% of the 193 source files have full annotations. Enabling
#     --strict globally would produce 2k+ warnings, which is exactly the
#     problem the project CLAUDE.md warns about.
#   * The [[tool.mypy.overrides]] block in pyproject.toml applies strict
#     to `airwar.game.achievements`, but mypy propagates the override
#     settings through transitive imports — checking one strict module
#     pulls in the whole dependency graph. This script bypasses that by
#     passing file paths explicitly.
#
# See docs/mypy_status.md for the rollout analysis and recommended path.
#
# Usage:
#   ./scripts/mypy_strict_pilot.sh          # check the curated list
#   ./scripts/mypy_strict_pilot.sh path/to/module.py  # check one file
#
# Exit code is non-zero if mypy reports any error.

set -euo pipefail

cd "$(dirname "$0")/.."

# Modules that are already strict-clean. The audio module has no airwar
# imports, the config/settings module only depends on the stdlib + pygame,
# and the achievements module was authored with type annotations in mind
# (and was the pilot for the [[tool.mypy.overrides]] approach).
DEFAULT_TARGETS=(
  "airwar/audio/sound_manager.py"
  "airwar/config/settings.py"
  "airwar/game/achievements.py"
)

if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=("${DEFAULT_TARGETS[@]}")
fi

echo "mypy --strict pilot: ${TARGETS[*]}"
echo "---"
# --follow-imports=silent keeps the strict check scoped to the named
# files. Without it, mypy follows imports from each target and applies
# the same strict settings to the entire dependency graph — defeating
# the purpose of a curated pilot.
exec python3 -m mypy --strict --follow-imports=silent "${TARGETS[@]}"
