#!/usr/bin/env bash
# Initial setup after cloning this repo: links skills, agents and global
# instructions into ~/.claude using symlinks, so the repo stays the single
# source of truth. Safe to run many times.
#
# Usage:
#   ./install.sh              install / refresh links
#   ./install.sh --dry-run    show what would happen, change nothing
#   ./install.sh --uninstall  remove the links created by this repo
#
# Environment:
#   CLAUDE_HOME   target config dir (default: ~/.claude)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
BACKUP_DIR="$CLAUDE_HOME/backups/my-claude-$(date +%Y%m%d-%H%M%S)"

DRY_RUN=0
UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help)   sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

run() { if [[ $DRY_RUN -eq 1 ]]; then echo "  [dry-run] $*"; else "$@"; fi; }
say() { echo "$*"; }

# link <source> <target>: symlink target -> source, backing up real files.
link() {
  local src="$1" dst="$2"
  if [[ -L "$dst" ]]; then
    if [[ "$(readlink "$dst")" == "$src" ]]; then
      say "  ok       $dst"; return
    fi
    say "  relink   $dst (was -> $(readlink "$dst"))"
    run rm "$dst"
  elif [[ -e "$dst" ]]; then
    say "  backup   $dst -> $BACKUP_DIR/"
    run mkdir -p "$BACKUP_DIR"
    run mv "$dst" "$BACKUP_DIR/"
  else
    say "  link     $dst"
  fi
  run ln -s "$src" "$dst"
}

# unlink <source> <target>: remove target only if it points into this repo.
unlink_ours() {
  local src="$1" dst="$2"
  if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
    say "  remove   $dst"
    run rm "$dst"
  fi
}

# Every item this repo provides, as "source|target" pairs.
items() {
  local d f
  for d in "$REPO_DIR"/skills/*/; do
    [[ -d "$d" ]] && echo "${d%/}|$CLAUDE_HOME/skills/$(basename "$d")"
  done
  for f in "$REPO_DIR"/agents/*.md; do
    [[ -f "$f" ]] && echo "$f|$CLAUDE_HOME/agents/$(basename "$f")"
  done
  for f in CLAUDE.md RTK.md; do
    [[ -f "$REPO_DIR/$f" ]] && echo "$REPO_DIR/$f|$CLAUDE_HOME/$f"
  done
}

if [[ $UNINSTALL -eq 1 ]]; then
  say "Removing links to $REPO_DIR from $CLAUDE_HOME"
  while IFS='|' read -r src dst; do unlink_ours "$src" "$dst"; done < <(items)
  say "Done. Backups (if any) remain in $CLAUDE_HOME/backups/."
  exit 0
fi

say "Installing from $REPO_DIR into $CLAUDE_HOME"
[[ $DRY_RUN -eq 1 ]] && say "(dry run: nothing will be changed)"

run mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/agents"
while IFS='|' read -r src dst; do link "$src" "$dst"; done < <(items)

# Make bundled scripts executable.
run find "$REPO_DIR/skills" -path '*/scripts/*.sh' -exec chmod +x {} +

# Tooling check: warn only, never fail.
say ""
say "Checking tools:"
for bin in git jq tmux gh node; do
  if command -v "$bin" >/dev/null 2>&1; then say "  ok       $bin"
  else say "  MISSING  $bin"; fi
done
command -v claude >/dev/null 2>&1 && say "  ok       claude" || say "  MISSING  claude (https://claude.com/claude-code)"

say ""
say "Done. Start a new Claude Code session to load the skills."
[[ -d "$BACKUP_DIR" ]] && say "Replaced files were backed up in $BACKUP_DIR"
exit 0
