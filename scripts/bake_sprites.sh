#!/usr/bin/env bash
# Air War - Aseprite bake script (P2-8).
#
# Converts airwar/assets/sprites/source/**/*.ase to PNGs that the
# generated-asset cache (airwar/utils/generated_asset_cache.py) will
# load on the next game launch. Idempotent: skips files whose cached
# PNG is newer than the .ase source.
#
# Requires the `aseprite` CLI on PATH. Get it from:
#   https://www.aseprite.org
#
# Usage:
#   ./scripts/bake_sprites.sh                 # bake everything stale
#   ./scripts/bake_sprites.sh --force         # re-bake every source
#   ./scripts/bake_sprites.sh --release       # also print cache dir for archiving
#   ./scripts/bake_sprites.sh --check         # exit 0 iff everything is fresh
#
# Exit codes:
#   0  success (all sources up-to-date, or baked successfully)
#   1  aseprite CLI missing
#   2  --check found stale sources
#   3  aseprite returned non-zero on at least one file
#
# This script does NOT install aseprite; the system it runs on must
# already have the binary. It is intentionally a no-op without the
# CLI so CI runners and developer machines that lack it stay green.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="$PROJECT_ROOT/airwar/assets/sprites/source"
CACHE_DIR_ENV="${AIRWAR_GENERATED_ASSET_DIR:-}"

FORCE=0
RELEASE=0
CHECK_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --force)   FORCE=1 ;;
        --release) RELEASE=1 ;;
        --check)   CHECK_ONLY=1 ;;
        -h|--help)
            sed -n '2,25p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 64
            ;;
    esac
done

# ----------------------------------------------------------------------
# Resolve the platform-specific cache directory.
# Mirrors airwar/utils/platform_paths.py:generated_asset_cache_dir().
# We shell out to Python instead of re-implementing the rules so the
# two stay in sync.
# ----------------------------------------------------------------------
resolve_cache_dir() {
    if [[ -n "$CACHE_DIR_ENV" ]]; then
        printf '%s\n' "$CACHE_DIR_ENV"
        return
    fi
    (
        cd "$PROJECT_ROOT"
        SDL_VIDEODRIVER=dummy python3 -c "
from airwar.utils.platform_paths import generated_asset_cache_dir
print(generated_asset_cache_dir())
"
    )
}

CACHE_DIR="$(resolve_cache_dir)"

# ----------------------------------------------------------------------
# Find aseprite. Bail out cleanly if it is missing.
# ----------------------------------------------------------------------
if ! command -v aseprite >/dev/null 2>&1; then
    cat >&2 <<EOF
[bake_sprites] aseprite CLI not found on PATH.

This is expected on most machines — the game falls back to the
procedural builder in airwar/utils/sprites.py when no baked PNG is
present. Install aseprite from https://www.aseprite.org and re-run
this script if you want to ship pre-baked PNGs.

Source dir:  $SOURCE_DIR
Cache dir:   $CACHE_DIR
EOF
    exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "[bake_sprites] source directory does not exist: $SOURCE_DIR" >&2
    exit 1
fi

# Aseprite export naming. We use a flat namespace per category so the
# generated PNGs land in cache with predictable names. The names
# intentionally do NOT need to match generated_asset_cache.py's hash
# scheme — the cache re-hashes on load and will pick up whatever
# PNG is on disk, regenerating the procedural version only if the
# PNG is missing or corrupt.
mapfile -t SOURCES < <(find "$SOURCE_DIR" -type f -name '*.ase' | sort)

if [[ ${#SOURCES[@]} -eq 0 ]]; then
    echo "[bake_sprites] no .ase files under $SOURCE_DIR (nothing to bake)"
    exit 0
fi

mkdir -p "$CACHE_DIR"

bake_one() {
    local src="$1"
    local rel="${src#$SOURCE_DIR/}"
    local category="${rel%%/*}"           # ships / bullets / fx
    local stem="${src##*/}"               # player.ase
    stem="${stem%.ase}"                   # player
    local out="$CACHE_DIR/${category}_${stem}.png"

    if [[ $FORCE -eq 0 && -f "$out" && "$out" -nt "$src" ]]; then
        echo "[bake_sprites] fresh   $rel"
        return 0
    fi

    if [[ $CHECK_ONLY -eq 1 ]]; then
        echo "[bake_sprites] STALE   $rel"
        return 1
    fi

    echo "[bake_sprites] baking  $rel -> ${out#$PROJECT_ROOT/}"
    # --batch: run without UI
    # --save-as <path>: export to this path
    # --format png: explicit (Aseprite infers from .png extension too)
    if ! aseprite --batch "$src" \
            --save-as "$out" \
            --format png \
            --trim-sprite >/dev/null
    then
        echo "[bake_sprites] FAILED  $rel" >&2
        return 1
    fi
}

stale_count=0
fail_count=0
for src in "${SOURCES[@]}"; do
    if ! bake_one "$src"; then
        if [[ $CHECK_ONLY -eq 1 ]]; then
            stale_count=$((stale_count + 1))
        else
            fail_count=$((fail_count + 1))
        fi
    fi
done

if [[ $CHECK_ONLY -eq 1 ]]; then
    if [[ $stale_count -gt 0 ]]; then
        echo "[bake_sprites] $stale_count stale source(s) need baking"
        exit 2
    fi
    echo "[bake_sprites] all sources fresh"
    exit 0
fi

if [[ $fail_count -gt 0 ]]; then
    echo "[bake_sprites] $fail_count file(s) failed to bake" >&2
    exit 3
fi

if [[ $RELEASE -eq 1 ]]; then
    echo "[bake_sprites] release-ready cache directory: $CACHE_DIR"
    echo "[bake_sprites] tar with: tar -C \"$CACHE_DIR\" -czf airwar-sprites.tar.gz ."
fi

echo "[bake_sprites] done. cache=$CACHE_DIR"
