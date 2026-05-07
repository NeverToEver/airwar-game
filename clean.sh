#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run)
            DRY_RUN=1
            ;;
        --help|-h)
            echo "Usage: ./clean.sh [--dry-run]"
            echo
            echo "Removes build artifacts and disposable caches, but keeps source code,"
            echo "virtual environments, saves, account data, and config."
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            echo "Usage: ./clean.sh [--dry-run]" >&2
            exit 2
            ;;
    esac
done

remove_path() {
    local path="$1"
    if [ ! -e "$path" ]; then
        return
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "would remove $path"
    else
        rm -rf "$path"
        echo "removed $path"
    fi
}

remove_pycache() {
    if [ "$DRY_RUN" -eq 1 ]; then
        find . -type d -name __pycache__ -print
    else
        find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
        echo "removed __pycache__ directories"
    fi
}

remove_path "build"
remove_path "dist"
remove_path "target"
remove_path "airwar_core/target"
remove_path "AirWar.spec"
remove_path "airwar.spec"
remove_path ".pytest_cache"
remove_path ".ruff_cache"
remove_path ".coverage"
remove_path "coverage.xml"
remove_path "htmlcov"
remove_path "airwar/data/generated_assets"
generated_asset_cache="$(python3 - <<'PY' 2>/dev/null || true
from airwar.utils.platform_paths import generated_asset_cache_dir
print(generated_asset_cache_dir())
PY
)"
if [[ "$generated_asset_cache" == *"/airwar/generated_assets" || "$generated_asset_cache" == *"/airwar/Cache/generated_assets" ]]; then
    remove_path "$generated_asset_cache"
fi
remove_pycache
