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

# 1. Build Rust extension
echo "[1/4] Building Rust extension..."
cd airwar_core
cargo build --release
cd ..

# 2. Copy Rust .so to match PyO3 module name
echo "[2/4] Installing Rust extension..."
RUST_SO="airwar_core/target/release/libairwar_core.so"
if [ -f "$RUST_SO" ]; then
    # Install to user site-packages so PyInstaller can find it
    SITE_PACKAGES=$(python3 -c "import site; print(site.getusersitepackages())")
    mkdir -p "$SITE_PACKAGES/airwar_core"
    cp "$RUST_SO" "$SITE_PACKAGES/airwar_core/airwar_core.cpython-312-x86_64-linux-gnu.so"
    echo "   Rust extension installed to $SITE_PACKAGES/airwar_core/"
else
    echo "   WARNING: Rust .so not found at $RUST_SO"
    echo "   Game will fall back to pure Python (slower but functional)."
fi

# 3. Install PyInstaller if needed
echo "[3/4] Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null || pip install pyinstaller --break-system-packages

# 4. Build standalone executable
echo "[4/4] Building standalone executable..."
rm -rf build dist
pyinstaller \
    --name="AirWar" \
    --add-data="airwar/data:airwar/data" \
    --collect-all airwar_core \
    --hidden-import=pygame \
    --hidden-import=PIL \
    --hidden-import=PIL.Image \
    --noconsole \
    --onefile \
    main.py

echo ""
echo "=== Build complete ==="
echo "Executable: dist/AirWar"
ls -lh dist/AirWar
