#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[airwar]${NC} $*"; }
ok()   { echo -e "${GREEN}[  ok  ]${NC} $*"; }
err()  { echo -e "${RED}[FAILED]${NC} $*"; }

# ── Python ──────────────────────────────────────────────
PYTHON=""
for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python >= 3.11 not found. Install it first:"
    echo "  sudo apt install python3.12 python3.12-venv"
    exit 1
fi
ok "Python: $($PYTHON --version)"

# ── Rust / Cargo ────────────────────────────────────────
NEED_RUST=false
if ! command -v cargo &>/dev/null; then
    NEED_RUST=true
fi

if $NEED_RUST; then
    log "Installing Rust toolchain..."
    if [ -f "$HOME/.cargo/env" ]; then
        . "$HOME/.cargo/env"
    fi
    if ! command -v cargo &>/dev/null; then
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        . "$HOME/.cargo/env"
    fi
fi
ok "Cargo: $(cargo --version 2>&1 | head -1)"

# ── System deps (SDL2) ──────────────────────────────────
if ! python3 -c "import ctypes.util; print(ctypes.util.find_library('SDL2') or '')" 2>/dev/null | grep -q sdl; then
    if command -v apt-get &>/dev/null; then
        log "Installing SDL2 system library..."
        sudo apt-get update -qq && sudo apt-get install -y -qq libsdl2-dev
    elif command -v brew &>/dev/null; then
        log "Installing SDL2 via brew..."
        brew install sdl2
    fi
fi
ok "SDL2: available"

# ── Virtual environment ─────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV_DIR/bin/python" ]; then
    log "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi
. "$VENV_DIR/bin/activate"
ok "venv: $VENV_DIR"

# ── Python dependencies ─────────────────────────────────
if ! python -c "import pygame" 2>/dev/null; then
    log "Installing Python dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
fi
ok "Python dependencies: satisfied"

# ── Rust extension ──────────────────────────────────────
RUST_DIR="$SCRIPT_DIR/airwar_core"
RUST_MARKER="$VENV_DIR/.rust_built"
NEED_BUILD=false

if [ ! -f "$RUST_MARKER" ]; then
    NEED_BUILD=true
elif [ "$RUST_DIR/Cargo.toml" -nt "$RUST_MARKER" ] 2>/dev/null; then
    NEED_BUILD=true
elif [ -n "$(find "$RUST_DIR/src" -name '*.rs' -newer "$RUST_MARKER" 2>/dev/null || true)" ]; then
    NEED_BUILD=true
fi

if $NEED_BUILD; then
    log "Building Rust extension (airwar_core)..."
    pip install --quiet maturin
    (cd "$RUST_DIR" && maturin develop --release)
    touch "$RUST_MARKER"
fi
ok "Rust extension: built"

# ── Launch ──────────────────────────────────────────────
log "Launching AirWar..."
exec python main.py
