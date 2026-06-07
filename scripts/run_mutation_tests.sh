#!/usr/bin/env bash
# =============================================================================
# Air War - Mutation Test Runner
# =============================================================================
# Runs mutmut 2.x against the airwar package using the project's pytest suite.
# Configuration is read from [tool.mutmut] in pyproject.toml.
#
# Usage:
#   ./scripts/run_mutation_tests.sh
#
# Prerequisites:
#   pip install -r requirements-dev.txt   # installs mutmut>=2.0
#   cd airwar_core && maturin develop --release   # optional, enables Rust accel
#
# Notes:
#   - mutmut 2.x dropped the legacy --max-children flag. Parallelism is now
#     controlled via the runner string in pyproject.toml using pytest-xdist
#     (e.g. add `-n 4` to the runner). This script simply invokes `mutmut run`
#     and inherits the configured runner.
#   - First run is slow (creates .mutmut-cache/). Subsequent runs are incremental.
#   - To inspect results: `python -m mutmut results` and `python -m mutmut show <id>`.
# =============================================================================

set -euo pipefail

# Always run from the project root so pyproject.toml is found.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

# Surface missing dependency clearly instead of a cryptic stack trace.
if ! python -c "import mutmut" >/dev/null 2>&1; then
    echo "Error: mutmut is not installed. Run: pip install -r requirements-dev.txt" >&2
    exit 1
fi

# Targeted mutation count knob (still supported in 2.x via positional arg).
# Pass an integer to mutate just one mutant, or omit for the full suite.
MUTANT_ARG="${1:-}"

echo "Running mutmut 2.x against airwar/ using the configured runner..."
if [[ -n "${MUTANT_ARG}" ]]; then
    exec python -m mutmut run "${MUTANT_ARG}"
else
    exec python -m mutmut run
fi
