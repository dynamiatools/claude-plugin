#!/usr/bin/env bash
# Initial setup after cloning this repo: links skills, agents and global
# instructions into ~/.claude using symlinks, so the repo stays the single
# source of truth. Safe to run many times.
#
# Usage:
#   ./install.sh              install / refresh links
#   ./install.sh --dry-run    show what would happen, change nothing
#   ./install.sh --uninstall  remove the links created by this repo
#   ./install.sh --legacy     also link skills and agents (only without the dynamia plugin)
#
# With the dynamia plugin installed, skills, agents and hooks come from the plugin;
# this script then only links bin/ and CLAUDE.md, and removes old skill/agent links.
#
# Environment:
#   CLAUDE_HOME   target config dir (default: ~/.claude)
#   BIN_DIR       where bin/* tools are linked (default: ~/.local/bin)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
BACKUP_DIR="$CLAUDE_HOME/backups/my-claude-$(date +%Y%m%d-%H%M%S)"

DRY_RUN=0
UNINSTALL=0
LEGACY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --legacy)    LEGACY=1 ;;
    -h|--help)   sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 0 ;;
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
  if [[ $LEGACY -eq 1 || $UNINSTALL -eq 1 ]]; then
    for d in "$REPO_DIR"/skills/*/; do
      [[ -d "$d" ]] && echo "${d%/}|$CLAUDE_HOME/skills/$(basename "$d")"
    done
    for f in "$REPO_DIR"/agents/*.md; do
      [[ -f "$f" ]] && echo "$f|$CLAUDE_HOME/agents/$(basename "$f")"
    done
  fi
  for f in "$REPO_DIR"/bin/*; do
    [[ -f "$f" ]] && echo "$f|$BIN_DIR/$(basename "$f")"
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

run mkdir -p "$CLAUDE_HOME" "$BIN_DIR"
[[ $LEGACY -eq 1 ]] && run mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/agents"
if [[ $LEGACY -eq 0 ]]; then
  # The plugin provides skills and agents: drop links from an earlier install of this repo
  # (including ones left dangling by renamed skills) so nothing is listed twice.
  for dst in "$CLAUDE_HOME"/skills/* "$CLAUDE_HOME"/agents/*; do
    if [[ -L "$dst" && "$(readlink "$dst")" == "$REPO_DIR/"* ]]; then
      say "  remove   $dst (now provided by the plugin)"
      run rm "$dst"
    fi
  done
fi
while IFS='|' read -r src dst; do link "$src" "$dst"; done < <(items)

# Make bundled scripts executable.
run find "$REPO_DIR/skills" -path '*/scripts/*.sh' -exec chmod +x {} +
run find "$REPO_DIR/bin" -type f -exec chmod +x {} +

# Tooling check: warn only, never fail.
say ""
say "Checking tools:"
for bin in git jq tmux gh node; do
  if command -v "$bin" >/dev/null 2>&1; then say "  ok       $bin"
  else say "  MISSING  $bin"; fi
done
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) say "  NOTE     $BIN_DIR is not in PATH; add it to your shell profile" ;; esac
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    say "  ok       python3 >= 3.11"
else
    say "  MISSING  python3 >= 3.11 (ms-workspace needs it; the guard hook still works on older versions)"
fi
command -v claude >/dev/null 2>&1 && say "  ok       claude" || say "  MISSING  claude (https://claude.com/claude-code)"

say ""
if [[ $LEGACY -eq 1 ]]; then say "Done. Start a new Claude Code session to load the skills."
else say "Done. Install the plugin with: /plugin marketplace add $REPO_DIR  then  /plugin install dynamia@dynamia"; fi
[[ -d "$BACKUP_DIR" ]] && say "Replaced files were backed up in $BACKUP_DIR"
exit 0
