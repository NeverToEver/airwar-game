#!/bin/bash
# =============================================================================
# Air War - Linux Build Script
# =============================================================================
# Usage: bash build_linux.sh
# Output: dist/AirWar (standalone executable, ~40MB)
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
PYTHON_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "ERROR: Python >= 3.11 is required. Found $PYTHON_VERSION at $PYTHON_BIN."
    exit 1
fi
echo "Python: $PYTHON_VERSION"

# 1. Create isolated build environment
echo "[1/4] Preparing build environment..."
"$PYTHON_BIN" -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# 2. Build and install Rust extension into the build environment
echo "[2/4] Building Rust extension..."
if command -v cargo >/dev/null 2>&1; then
    if python -m maturin develop --release --manifest-path airwar_core/Cargo.toml; then
        echo "   Rust extension installed in .venv-build."
    else
        echo "   WARNING: Rust extension build failed."
        echo "   Game will fall back to pure Python (slower but functional)."
    fi
else
    echo "   WARNING: cargo not found."
    echo "   Game will fall back to pure Python (slower but functional)."
fi

# 3. Validate imports
echo "[3/4] Validating Python environment..."
python -c "import pygame, PIL, PyInstaller; from airwar.core_bindings import RUST_AVAILABLE; print('Rust acceleration:', RUST_AVAILABLE)"

# 4. Build standalone executable
echo "[4/4] Building standalone executable..."
rm -rf build dist
PYINSTALLER_ARGS=(
    --name="AirWar" \
    --hidden-import=pygame \
    --hidden-import=PIL \
    --hidden-import=PIL.Image \
    --noconsole \
    --onefile
)
if python -c "from airwar.core_bindings import RUST_AVAILABLE; raise SystemExit(0 if RUST_AVAILABLE else 1)"; then
    PYINSTALLER_ARGS+=(--collect-all airwar_core)
fi
python -m PyInstaller "${PYINSTALLER_ARGS[@]}" main.py

echo ""
echo "=== Build complete ==="
echo "Executable: dist/AirWar"
ls -lh dist/AirWar
