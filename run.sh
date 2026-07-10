#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' NC=''
fi

log()  { printf '%b\n' "${CYAN}[airwar]${NC} $*"; }
ok()   { printf '%b\n' "${GREEN}[  ok  ]${NC} $*"; }
warn() { printf '%b\n' "${YELLOW}[ warn ]${NC} $*"; }
err()  { printf '%b\n' "${RED}[error]${NC} $*" >&2; }

usage() {
    cat <<'EOF'
Usage: ./run.sh [launcher options] [-- game options]

Launcher options:
  --install-deps   Install Rust with rustup when Cargo is unavailable.
  --rebuild-rust   Rebuild the optional Rust extension.
  --skip-rust      Do not build or load the optional Rust extension.
  --prepare-only   Prepare the virtual environment, then exit.
  -h, --help       Show this help.

Game options are forwarded to AirWar. Use `--` before game options when they
could be confused with launcher options, for example: ./run.sh -- --debug
EOF
}

INSTALL_DEPS="${AIRWAR_INSTALL_DEPS:-0}"
PREPARE_ONLY=0
SKIP_RUST=0
REBUILD_RUST=0
APP_ARGS=()

while (($#)); do
    case "$1" in
        --install-deps)
            INSTALL_DEPS=1
            ;;
        --rebuild-rust)
            REBUILD_RUST=1
            ;;
        --skip-rust)
            SKIP_RUST=1
            ;;
        --prepare-only)
            PREPARE_ONLY=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            APP_ARGS+=("$@")
            break
            ;;
        *)
            APP_ARGS+=("$1")
            ;;
    esac
    shift
done

is_supported_python() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && is_supported_python "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

can_install_deps() {
    case "$INSTALL_DEPS" in
        1|true|TRUE|yes|YES|y|Y) return 0 ;;
        *) return 1 ;;
    esac
}

PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then
    err "Python 3.11 or newer was not found."
    echo "Install Python from https://www.python.org/downloads/"
    exit 1
fi
ok "Python: $($PYTHON --version)"

VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    log "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
elif ! is_supported_python "$VENV_PYTHON"; then
    err "Existing .venv does not use Python 3.11 or newer. Remove .venv and rerun."
    exit 1
fi
ok "venv: $VENV_DIR"

DEPENDENCY_MARKER="$VENV_DIR/.airwar-runtime-deps"
needs_dependency_sync=0
if [[ ! -f "$DEPENDENCY_MARKER" || requirements.txt -nt "$DEPENDENCY_MARKER" || pyproject.toml -nt "$DEPENDENCY_MARKER" ]]; then
    needs_dependency_sync=1
elif ! "$VENV_PYTHON" -c 'import numpy, PIL, pygame' >/dev/null 2>&1; then
    needs_dependency_sync=1
fi

if ((needs_dependency_sync)); then
    log "Installing runtime dependencies..."
    "$VENV_PYTHON" -m pip install --quiet --disable-pip-version-check -r requirements.txt
    touch "$DEPENDENCY_MARKER"
fi
ok "Runtime dependencies: satisfied"

prepare_rust_extension() {
    local rust_dir="$SCRIPT_DIR/airwar_core"
    local marker="$VENV_DIR/.airwar-rust-extension"
    local needs_build=0

    if ((SKIP_RUST)); then
        warn "Rust extension: skipped"
        return 0
    fi

    if [[ -f "$HOME/.cargo/env" ]]; then
        # shellcheck disable=SC1090
        source "$HOME/.cargo/env"
    fi

    if ! command -v cargo >/dev/null 2>&1; then
        if ! can_install_deps; then
            warn "Cargo not found; using the Python fallback."
            echo "  Install Rust from https://rustup.rs/ or rerun with --install-deps."
            return 0
        fi
        if ! command -v curl >/dev/null 2>&1; then
            err "curl is required to install Rust automatically."
            return 1
        fi
        log "Installing Rust toolchain..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
        # shellcheck disable=SC1090
        source "$HOME/.cargo/env"
    fi

    if ((REBUILD_RUST)); then
        rm -f "$marker"
        needs_build=1
    elif [[ ! -f "$marker" || "$rust_dir/Cargo.toml" -nt "$marker" || "$rust_dir/Cargo.lock" -nt "$marker" || "$rust_dir/pyproject.toml" -nt "$marker" ]]; then
        needs_build=1
    elif [[ -n "$(find "$rust_dir/src" -type f -name '*.rs' -newer "$marker" -print -quit)" ]]; then
        needs_build=1
    elif ! "$VENV_PYTHON" -c 'from airwar.core_bindings import RUST_AVAILABLE; raise SystemExit(0 if RUST_AVAILABLE else 1)' >/dev/null 2>&1; then
        needs_build=1
    fi

    if (( ! needs_build )); then
        ok "Rust extension: ready"
        return 0
    fi

    log "Building optional Rust extension..."
    if ! "$VENV_PYTHON" -m pip install --quiet --disable-pip-version-check 'maturin>=1,<2'; then
        warn "Could not install maturin; using the Python fallback."
        return 0
    fi
    if "$VENV_PYTHON" -m maturin develop --release --manifest-path "$rust_dir/Cargo.toml"; then
        touch "$marker"
        ok "Rust extension: built"
    else
        warn "Rust extension build failed; using the Python fallback."
    fi
}

prepare_rust_extension

if ((PREPARE_ONLY)); then
    ok "Runtime environment prepared"
    exit 0
fi

log "Launching AirWar..."
if ((${#APP_ARGS[@]})); then
    exec "$VENV_PYTHON" main.py "${APP_ARGS[@]}"
fi
exec "$VENV_PYTHON" main.py
