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

# 1. Create isolated build environment
echo "[1/4] Preparing build environment..."
python3 -m venv .venv-build
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
    --add-data="airwar/data:airwar/data" \
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
