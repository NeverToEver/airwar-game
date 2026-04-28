#!/bin/bash
# =============================================================================
# Air War - macOS Build Script
# =============================================================================
# Usage: bash build_macos.sh
# Prerequisites: Xcode Command Line Tools, Rust (rustup), Python 3.12+
# Output: dist/AirWar (standalone macOS executable)
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Air War macOS Build ==="

# 1. Build Rust extension for macOS
echo "[1/4] Building Rust extension (macOS target)..."
cd airwar_core
cargo build --release
cd ..

# 2. Install Rust extension
echo "[2/4] Installing Rust extension..."
RUST_DYLIB="airwar_core/target/release/libairwar_core.dylib"
if [ -f "$RUST_DYLIB" ]; then
    SITE_PACKAGES=$(python3 -c "import site; print(site.getusersitepackages())")
    mkdir -p "$SITE_PACKAGES/airwar_core"
    cp "$RUST_DYLIB" "$SITE_PACKAGES/airwar_core/airwar_core.cpython-312-darwin.so"
    echo "   Rust extension installed."
else
    echo "   WARNING: Rust .dylib not found at $RUST_DYLIB"
    echo "   Game will fall back to pure Python."
fi

# 3. Install PyInstaller
echo "[3/4] Checking PyInstaller..."
python3 -c "import PyInstaller" 2>/dev/null || pip3 install pyinstaller --break-system-packages

# 4. Build standalone app bundle
echo "[4/4] Building macOS app bundle..."
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
    --osx-bundle-identifier=com.airwar.game \
    main.py

echo ""
echo "=== Build complete ==="
echo "App: dist/AirWar"
ls -lh dist/AirWar
echo ""
echo "To create a DMG (optional):"
echo "  hdiutil create -volname AirWar -srcfolder dist/AirWar.app -ov AirWar.dmg"
