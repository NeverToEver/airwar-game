#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo
echo "  =============================="
echo "    AirWar - Uninstaller"
echo "  =============================="
echo
echo "  This will remove: .venv, airwar_core/target, __pycache__, pip package"
echo "  Source code, saves, and config will NOT be affected."
echo
read -rp "  Proceed? [y/N] " answer
if [[ ! "$answer" =~ ^[Yy] ]]; then
    echo "  Cancelled."
    exit 0
fi

echo
echo "  [..] Removing virtual environment..."
rm -rf .venv && echo "  [OK] .venv"

echo "  [..] Removing Rust build cache..."
rm -rf airwar_core/target && echo "  [OK] target/"

echo "  [..] Removing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo "  [OK] __pycache__"

echo "  [..] Uninstalling airwar_core..."
pip uninstall -y airwar_core 2>/dev/null || true
echo "  [OK] Package"

echo
echo "  Done. Run ./run.sh to play again."
