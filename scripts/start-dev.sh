#!/usr/bin/env bash
# Start FastAPI backend + Next.js dashboard for local development.
# See docs/superpowers/specs/2026-05-03-start-dev-script-design.md
set -euo pipefail

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
READY_TIMEOUT="${READY_TIMEOUT:-30}"
CONDA_ENV="${CONDA_ENV:-paperclaw}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -t 1 ]; then
    C_API=$'\033[36m'   # cyan
    C_WEB=$'\033[32m'   # green
    C_DEV=$'\033[33m'   # yellow
    C_ERR=$'\033[31m'   # red
    C_OFF=$'\033[0m'
else
    C_API=""; C_WEB=""; C_DEV=""; C_ERR=""; C_OFF=""
fi

dev()  { printf '%s[dev]%s %s\n' "$C_DEV" "$C_OFF" "$*"; }
err()  { printf '%s[dev]%s %s%s%s\n' "$C_DEV" "$C_OFF" "$C_ERR" "$*" "$C_OFF" >&2; }

prefix() {
    local tag="$1" color="$2" line
    while IFS= read -r line; do
        printf '%s%s%s %s\n' "$color" "$tag" "$C_OFF" "$line"
    done
}

API_PID=""
WEB_PID=""
CLEANUP_DONE=0

# Kill a backgrounded process AND its descendants. We start each service via
# `setsid` so it becomes its own process-group leader, then `kill -- -PGID`
# tears down uvicorn's reloader/workers and npm's child node process together.
kill_tree() {
    local pid="$1"
    [ -z "$pid" ] && return 0
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
}

cleanup() {
    [ "$CLEANUP_DONE" -eq 1 ] && return
    CLEANUP_DONE=1
    trap - INT TERM EXIT
    if [ -n "$API_PID" ] || [ -n "$WEB_PID" ]; then
        dev "shutting down…"
    fi
    kill_tree "$WEB_PID"
    kill_tree "$API_PID"
    [ -n "$WEB_PID" ] && wait "$WEB_PID" 2>/dev/null || true
    [ -n "$API_PID" ] && wait "$API_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# --- pre-flight checks ----------------------------------------------------

if ! command -v lsof >/dev/null 2>&1; then
    err "'lsof' not found; install it (apt: lsof) so port checks can run."
    exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
    err "'conda' not found in PATH."
    exit 1
fi

if ! conda env list | awk '{print $1}' | grep -qx "$CONDA_ENV"; then
    err "conda env '$CONDA_ENV' not found. Run 'make env' first."
    exit 1
fi

if [ ! -d frontend/node_modules ]; then
    dev "frontend/node_modules missing — running 'npm install' (one-time)…"
    ( cd frontend && npm install )
fi

check_port() {
    local port="$1" pid_cmd
    if pid_cmd="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -F pc 2>/dev/null)"; then
        if [ -n "$pid_cmd" ]; then
            local pid name
            pid="$(printf '%s\n' "$pid_cmd" | awk '/^p/{sub(/^p/,""); print; exit}')"
            name="$(printf '%s\n' "$pid_cmd" | awk '/^c/{sub(/^c/,""); print; exit}')"
            err "port $port already in use (pid $pid — $name)"
            return 1
        fi
    fi
    return 0
}

# --- load .env (must come BEFORE port checks so .env can override ports) -

if [ -f .env ]; then
    dev "loading .env"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

check_port "$API_PORT" || exit 1
check_port "$WEB_PORT" || exit 1

mkdir -p logs

# --- start backend --------------------------------------------------------

dev "starting api on $API_HOST:$API_PORT (conda env: $CONDA_ENV)"
setsid conda run --no-capture-output -n "$CONDA_ENV" \
    uv run uvicorn app.api.app:create_app \
        --factory --reload \
        --host "$API_HOST" --port "$API_PORT" \
    > >(prefix '[api]' "$C_API" | tee logs/dev-api.log) 2>&1 &
API_PID=$!

# --- wait for readiness ---------------------------------------------------

dev "waiting for api readiness (timeout ${READY_TIMEOUT}s)…"
ready=0
for _ in $(seq 1 "$READY_TIMEOUT"); do
    if curl -sf "http://$API_HOST:$API_PORT/openapi.json" >/dev/null 2>&1; then
        ready=1
        break
    fi
    if ! kill -0 "$API_PID" 2>/dev/null; then
        err "api process exited before becoming ready"
        exit 1
    fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    err "api not ready after ${READY_TIMEOUT}s"
    exit 1
fi
dev "api ready"

# --- start frontend -------------------------------------------------------

dev "starting web on :$WEB_PORT"
setsid bash -c "
    cd frontend
    NEXT_PUBLIC_API_BASE_URL='http://localhost:$API_PORT' \
    PAPERCLAW_API_BASE_URL='http://localhost:$API_PORT' \
    PAPERCLAW_DATA_SOURCE=http \
    PORT='$WEB_PORT' \
    exec npm run dev
" > >(prefix '[web]' "$C_WEB" | tee logs/dev-web.log) 2>&1 &
WEB_PID=$!

# --- print access URLs ----------------------------------------------------

cat <<EOF

──────────────────────────────────────────────
 API   http://localhost:$API_PORT/docs
 Web   http://localhost:$WEB_PORT
──────────────────────────────────────────────
 Logs  logs/dev-api.log · logs/dev-web.log
 Press Ctrl+C to stop both.

EOF

wait
