#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage: ./run_with_server.sh [launcher options] [server options]

Launcher options: --install-deps, --rebuild-rust, --skip-rust
Server options:   --host HOST, --port PORT, --debug, --game-arg=ARG
EOF
    exit 0
fi

BOOTSTRAP_ARGS=()
SERVER_ARGS=()
while (($#)); do
    case "$1" in
        --install-deps|--rebuild-rust|--skip-rust)
            BOOTSTRAP_ARGS+=("$1")
            ;;
        --)
            shift
            SERVER_ARGS+=("$@")
            break
            ;;
        *)
            SERVER_ARGS+=("$1")
            ;;
    esac
    shift
done

if ((${#BOOTSTRAP_ARGS[@]})); then
    "$SCRIPT_DIR/run.sh" --prepare-only "${BOOTSTRAP_ARGS[@]}"
else
    "$SCRIPT_DIR/run.sh" --prepare-only
fi

if ((${#SERVER_ARGS[@]})); then
    exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/run_with_server.py" "${SERVER_ARGS[@]}"
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/run_with_server.py"
