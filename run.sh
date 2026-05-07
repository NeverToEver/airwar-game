#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[airwar]${NC} $*"; }
ok()   { echo -e "${GREEN}[  ok  ]${NC} $*"; }
warn() { echo -e "${YELLOW}[ warn ]${NC} $*"; }
err()  { echo -e "${RED}[FAILED]${NC} $*"; }

INSTALL_DEPS="${AIRWAR_INSTALL_DEPS:-0}"
for arg in "$@"; do
    case "$arg" in
        --install-deps)
            INSTALL_DEPS=1
            ;;
        --help|-h)
            echo "Usage: ./run.sh [--install-deps]"
            echo
            echo "By default this script only creates the project virtualenv and installs"
            echo "Python packages into it. System packages and Rust are only installed when"
            echo "--install-deps is passed or AIRWAR_INSTALL_DEPS=1 is set."
            exit 0
            ;;
        *)
            err "Unknown option: $arg"
            echo "Usage: ./run.sh [--install-deps]"
            exit 2
            ;;
    esac
done

can_install_deps() {
    case "$INSTALL_DEPS" in
        1|true|TRUE|yes|YES|y|Y)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

print_install_hint() {
    local tool="$1"
    local apt_pkg="$2"
    local brew_pkg="$3"

    warn "$tool is not available."
    if command -v apt-get >/dev/null 2>&1; then
        echo "  Install it with: sudo apt-get install $apt_pkg"
    elif command -v brew >/dev/null 2>&1; then
        echo "  Install it with: brew install $brew_pkg"
    else
        echo "  Install $tool with your platform package manager."
    fi
}

# Python
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        ver=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python >= 3.11 not found."
    if command -v apt-get >/dev/null 2>&1; then
        echo "  Install it with: sudo apt-get install python3 python3-venv"
    elif command -v brew >/dev/null 2>&1; then
        echo "  Install it with: brew install python"
    else
        echo "  Install Python from https://www.python.org/downloads/"
    fi
    exit 1
fi
ok "Python: $($PYTHON --version)"

# Optional Rust/Cargo acceleration
if [ -f "$HOME/.cargo/env" ]; then
    . "$HOME/.cargo/env"
fi

if ! command -v cargo >/dev/null 2>&1; then
    if can_install_deps; then
        log "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        . "$HOME/.cargo/env"
    else
        warn "Cargo not found. AirWar will use the pure-Python fallback."
        echo "  For Rust acceleration, install Rust from https://rustup.rs/"
        echo "  To let this script install it, rerun: ./run.sh --install-deps"
    fi
fi

if command -v cargo >/dev/null 2>&1; then
    ok "Cargo: $(cargo --version 2>&1 | head -1)"
fi

# SDL2 system library
SDL2_AVAILABLE=false
if "$PYTHON" -c "import ctypes.util; raise SystemExit(0 if ctypes.util.find_library('SDL2') else 1)" 2>/dev/null; then
    SDL2_AVAILABLE=true
fi

if ! $SDL2_AVAILABLE; then
    if can_install_deps; then
        if command -v apt-get >/dev/null 2>&1; then
            log "Installing SDL2 system library..."
            sudo apt-get update -qq
            sudo apt-get install -y -qq libsdl2-dev
        elif command -v brew >/dev/null 2>&1; then
            log "Installing SDL2 via Homebrew..."
            brew install sdl2
        else
            print_install_hint "SDL2" "libsdl2-dev" "sdl2"
            exit 1
        fi
    else
        print_install_hint "SDL2" "libsdl2-dev" "sdl2"
        echo "  To let this script install it, rerun: ./run.sh --install-deps"
        exit 1
    fi
fi
ok "SDL2: available"

# Virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV_DIR/bin/python" ]; then
    log "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi
. "$VENV_DIR/bin/activate"
ok "venv: $VENV_DIR"

# Python dependencies
if ! python -c "import pygame, PIL" 2>/dev/null; then
    log "Installing Python dependencies..."
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt
fi
ok "Python dependencies: satisfied"

# Optional Rust extension
RUST_DIR="$SCRIPT_DIR/airwar_core"
RUST_MARKER="$VENV_DIR/.rust_built"
NEED_BUILD=false

if command -v cargo >/dev/null 2>&1; then
    if [ ! -f "$RUST_MARKER" ]; then
        NEED_BUILD=true
    elif [ "$RUST_DIR/Cargo.toml" -nt "$RUST_MARKER" ] 2>/dev/null; then
        NEED_BUILD=true
    elif [ -n "$(find "$RUST_DIR/src" -name '*.rs' -newer "$RUST_MARKER" 2>/dev/null || true)" ]; then
        NEED_BUILD=true
    fi

    if $NEED_BUILD; then
        log "Building Rust extension (airwar_core)..."
        python -m pip install --quiet 'maturin>=1,<2'
        if (cd "$RUST_DIR" && maturin develop --release); then
            touch "$RUST_MARKER"
            ok "Rust extension: built"
        else
            warn "Rust extension build failed. AirWar will use the pure-Python fallback."
        fi
    else
        ok "Rust extension: already built"
    fi
else
    warn "Rust extension: skipped"
fi

log "Launching AirWar..."
exec python main.py
