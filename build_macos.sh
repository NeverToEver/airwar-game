#!/bin/bash
# =============================================================================
# Air War - macOS Build (slim wrapper around AirWar.spec)
# =============================================================================
# Usage: bash build_macos.sh
# Prerequisites: Xcode Command Line Tools, Rust (rustup), Python 3.11+
# Output: dist/AirWar/AirWar (standalone macOS executable)
# Optional env:
#   AIRWAR_KEEP_BUILD_VENV=1       preserve .venv-build after the run
#   AIRWAR_OSX_BUNDLE_ID=...       bundle identifier (default: com.airwar.game)
#   AIRWAR_CODESIGN_IDENTITY=...   run codesign --force --deep --sign=<id>
#   AIRWAR_NOTARIZE=1              submit for notarization (xcrun altool)
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Air War macOS Build ==="
KEEP_BUILD_VENV="${AIRWAR_KEEP_BUILD_VENV:-0}"
export AIRWAR_OSX_BUNDLE_ID="${AIRWAR_OSX_BUNDLE_ID:-com.airwar.game}"

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
    mkdir -p airwar_core/airwar_core
    cat > airwar_core/airwar_core/__init__.py <<'PY'
"""Editable-install bridge for the PyO3 airwar_core extension."""

from .airwar_core import *  # noqa: F403
PY
    python -m maturin develop --release --manifest-path airwar_core/Cargo.toml \
        || echo "WARNING: Rust build failed; using pure-Python fallback."
else
    echo "WARNING: cargo not found; using pure-Python fallback."
fi

# 3. Build standalone app bundle from AirWar.spec
rm -rf build dist
python -m PyInstaller AirWar.spec

# 4. Optional code signing (mitigates Gatekeeper warnings)
APP_BIN="dist/AirWar/AirWar"
if [ -n "${AIRWAR_CODESIGN_IDENTITY:-}" ]; then
    echo "Codesigning with identity: $AIRWAR_CODESIGN_IDENTITY"
    codesign --force --deep --sign "$AIRWAR_CODESIGN_IDENTITY" "$APP_BIN"
    if [ "${AIRWAR_NOTARIZE:-0}" = "1" ]; then
        echo "Submitting for notarization..."
        xcrun altool --notarize-app \
            --primary-bundle-id "$AIRWAR_OSX_BUNDLE_ID" \
            --file "$APP_BIN" --output-format xml
    fi
else
    echo "Skipping codesign (set AIRWAR_CODESIGN_IDENTITY to enable)."
fi

echo ""
echo "=== Build complete ==="
echo "App: $APP_BIN"
ls -lh "$APP_BIN"
echo ""
echo "To create a DMG (optional):"
echo "  mkdir -p dmg-root && cp $APP_BIN dmg-root/"
echo "  hdiutil create -volname AirWar -srcfolder dmg-root -ov AirWar.dmg"
