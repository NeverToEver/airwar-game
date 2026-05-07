#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo
echo "  =============================="
echo "    AirWar - Local Uninstaller"
echo "  =============================="
echo
echo "  This will remove local environments, build artifacts, and disposable caches:"
echo "    .venv, .venv-build, build/, dist/, target/, airwar_core/target/"
echo "    AirWar.spec, airwar.spec, __pycache__, .pytest_cache, .ruff_cache"
echo "    airwar/data/generated_assets/"
echo "    platform generated-asset cache"
echo
echo "  Source code, saves, account data, and config will NOT be affected."
echo
read -rp "  Proceed? [y/N] " answer
if [[ ! "$answer" =~ ^[Yy] ]]; then
    echo "  Cancelled."
    exit 0
fi

remove_path() {
    local path="$1"
    if [ -e "$path" ]; then
        rm -rf "$path"
        echo "  [OK] $path"
    else
        echo "  [--] $path"
    fi
}

echo
if [ -x .venv/bin/python ]; then
    echo "  [..] Uninstalling airwar_core from .venv..."
    .venv/bin/python -m pip uninstall -y airwar_core >/dev/null 2>&1 || true
    echo "  [OK] airwar_core package"
fi

echo "  [..] Removing local environments..."
remove_path ".venv"
remove_path ".venv-build"

echo "  [..] Removing build artifacts..."
remove_path "build"
remove_path "dist"
remove_path "target"
remove_path "airwar_core/target"
remove_path "AirWar.spec"
remove_path "airwar.spec"

echo "  [..] Removing caches..."
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
echo "  [OK] __pycache__"
remove_path ".pytest_cache"
remove_path ".ruff_cache"
remove_path "airwar/data/generated_assets"
generated_asset_cache="$(python3 - <<'PY' 2>/dev/null || true
from airwar.utils.platform_paths import generated_asset_cache_dir
print(generated_asset_cache_dir())
PY
)"
if [[ "$generated_asset_cache" == *"/airwar/generated_assets" || "$generated_asset_cache" == *"/airwar/Cache/generated_assets" ]]; then
    remove_path "$generated_asset_cache"
fi

echo
echo "  Done. Run ./run.sh to play again."
