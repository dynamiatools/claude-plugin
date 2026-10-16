#!/usr/bin/env bash
# claude-tmux: start a tmux session running Claude Code in a subfolder of a base directory.
# The session has a single window, and its name is the subfolder name.
#
# Usage:
#   claude-tmux.sh <subfolder>              # create the session and attach
#   claude-tmux.sh <subfolder> --detached   # create the session in the background
#
# Environment:
#   CLAUDE_TMUX_BASE_DIR   base directory holding the projects (default: $HOME/IdeaProjects)
set -euo pipefail

BASE_DIR="${CLAUDE_TMUX_BASE_DIR:-$HOME/IdeaProjects}"

DETACHED=0
CHOSEN=""
for arg in "$@"; do
    case "$arg" in
        --detached) DETACHED=1 ;;
        *) CHOSEN="$arg" ;;
    esac
done

for bin in tmux claude jq; do
    command -v "$bin" >/dev/null 2>&1 || { echo "Error: $bin is not installed or not in PATH." >&2; exit 1; }
done

if [ -z "$CHOSEN" ]; then
    echo "Usage: $(basename "$0") <subfolder> [--detached]" >&2
    exit 1
fi

if [ ! -d "$BASE_DIR/$CHOSEN" ]; then
    echo "Error: '$CHOSEN' does not exist inside $BASE_DIR." >&2
    exit 1
fi

SUB_DIR="$BASE_DIR/$CHOSEN"
SESSION_NAME="$CHOSEN"
CLAUDE_CONFIG="$HOME/.claude.json"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Error: a tmux session named '$SESSION_NAME' already exists." >&2
    exit 1
fi

# Mark the directory as trusted so Claude skips the "trust this folder" dialog.
if [ -f "$CLAUDE_CONFIG" ]; then
    tmp="$(mktemp)"
    jq --arg dir "$SUB_DIR" \
        '.projects[$dir] = ((.projects[$dir] // {}) + {"hasTrustDialogAccepted": true})' \
        "$CLAUDE_CONFIG" > "$tmp" && mv "$tmp" "$CLAUDE_CONFIG"
fi

tmux new-session -d -s "$SESSION_NAME" -n "$CHOSEN" -c "$SUB_DIR" \
    "claude --name \"$(hostname):$CHOSEN\"; tmux kill-session -t \"$SESSION_NAME\""

# Enable Remote Control in the background once Claude shows its prompt, so the
# session appears in claude.ai/code without manual steps.
(
    for _ in $(seq 1 30); do
        sleep 1
        if tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | grep -q '^❯'; then
            break
        fi
    done
    tmux send-keys -t "$SESSION_NAME" "/remote-control" Enter
    sleep 1.5
    tmux send-keys -t "$SESSION_NAME" Enter
) >/dev/null 2>&1 &
disown

if [ "$DETACHED" -eq 1 ]; then
    echo "tmux session '$SESSION_NAME' created in the background."
    echo "Attach with: tmux attach -t $SESSION_NAME"
else
    exec tmux attach-session -t "$SESSION_NAME"
fi
