#!/bin/bash
# =============================================================================
# Air War - Linux Build (slim wrapper around AirWar.spec)
# =============================================================================
# Usage: bash build_linux.sh
# Output: dist/AirWar/AirWar (standalone executable, ~40MB)
# Env:    AIRWAR_KEEP_BUILD_VENV=1 to preserve .venv-build after the run
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Air War Linux Build ==="
KEEP_BUILD_VENV="${AIRWAR_KEEP_BUILD_VENV:-0}"

cleanup_build_venv() {
    if [ "$KEEP_BUILD_VENV" != "1" ]; then
        rm -rf .venv-build
    fi
}
trap cleanup_build_venv EXIT

PYTHON_BIN="${PYTHON:-python3}"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "ERROR: Python >= 3.11 is required. Found at $PYTHON_BIN."
    "$PYTHON_BIN" --version
    exit 1
fi
echo "Python: $("$PYTHON_BIN" --version)"

# 1. Isolated build venv with PyInstaller + maturin + project deps
"$PYTHON_BIN" -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# 2. Optional Rust extension (game falls back to pure Python if unavailable)
if command -v cargo >/dev/null 2>&1; then
    python -m maturin develop --release --manifest-path airwar_core/Cargo.toml \
        || echo "WARNING: Rust build failed; using pure-Python fallback."
else
    echo "WARNING: cargo not found; using pure-Python fallback."
fi

# 3. Build standalone executable from AirWar.spec
rm -rf build dist
python -m PyInstaller AirWar.spec

echo ""
echo "=== Build complete ==="
echo "Executable: dist/AirWar/AirWar"
ls -lh dist/AirWar/AirWar
