#!/usr/bin/env bash
# Launch @dynamia-tools/remote-code-viewer --tunnel in the background against
# the given directory, killing any previous instance, and wait for it to print
# a Cloudflare tunnel URL. On success, prints only that URL to stdout.
set -euo pipefail

# Non-interactive shells may lack node/npx (loaded via nvm in .bashrc).
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  \. "$NVM_DIR/nvm.sh"
fi

STATE_DIR="$HOME/.cache/remote-viewer"
PID_FILE="$STATE_DIR/tunnel.pid"
LOG_FILE="$STATE_DIR/tunnel.log"
TARGET_DIR="${1:-$PWD}"
TIMEOUT="${REMOTE_VIEWER_TIMEOUT:-60}"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "ERROR: directory '$TARGET_DIR' does not exist" >&2
  exit 1
fi

mkdir -p "$STATE_DIR"

# 1) Kill any previous instance so tunnels don't pile up.
if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$OLD_PID" 2>/dev/null || break
      sleep 0.3
    done
    kill -9 "$OLD_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi
# Safety net in case the pid file was lost but a process is still running.
pkill -f "@dynamia-tools/remote-code-viewer" 2>/dev/null || true

: > "$LOG_FILE"

# 2) Launch the new tunnel fully detached from this shell.
(
  cd "$TARGET_DIR"
  setsid nohup npx @dynamia-tools/remote-code-viewer --tunnel \
    >"$LOG_FILE" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"
)
NEW_PID="$(cat "$PID_FILE")"

# 3) Wait for the Cloudflare tunnel URL to show up in the log.
URL=""
STEPS=$(( TIMEOUT * 2 ))
for _ in $(seq 1 "$STEPS"); do
  if ! kill -0 "$NEW_PID" 2>/dev/null; then
    echo "ERROR: process exited before printing a tunnel URL" >&2
    echo "----- log -----" >&2
    cat "$LOG_FILE" >&2
    exit 1
  fi
  URL="$(grep -Eo 'https://[a-zA-Z0-9.-]*trycloudflare\.com[^[:space:]"'"'"']*' "$LOG_FILE" | head -n1 || true)"
  [[ -n "$URL" ]] && break
  sleep 0.5
done

if [[ -z "$URL" ]]; then
  echo "ERROR: timed out after ${TIMEOUT}s waiting for the tunnel URL" >&2
  echo "----- log -----" >&2
  cat "$LOG_FILE" >&2
  exit 1
fi

echo "$URL"
