#!/usr/bin/env bash
# powers.sh: install, check and remove helper tools for coding agents.
#
# Usage:
#   powers.sh list                      catalog with install state
#   powers.sh doctor                    state plus version of every installed tool
#   powers.sh install <tool>... [--yes] install (without --yes: only print the plan)
#   powers.sh remove  <tool>... [--yes] remove  (without --yes: only print the plan)
#
# Remote installers are downloaded to a temp file, their sha256 is printed, and
# only then run. Nothing is piped from curl into a shell.
set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"
TOOLS=(uv rtk codebase-memory graphify headroom)
YES=0

# --- catalog -----------------------------------------------------------------
# For each tool: binary, one-line description, prerequisites, source.
tool_bin()  { case "$1" in
  uv) echo uv ;; rtk) echo rtk ;; codebase-memory) echo codebase-memory-mcp ;;
  graphify) echo graphify ;; headroom) echo headroom ;; *) return 1 ;; esac; }
tool_desc() { case "$1" in
  uv)              echo "Python tool installer (needed by graphify and headroom)" ;;
  rtk)             echo "Shrinks shell output before it reaches the model (rtk-ai/rtk)" ;;
  codebase-memory) echo "Code knowledge graph as an MCP server (DeusData/codebase-memory-mcp)" ;;
  graphify)        echo "Code knowledge graph and report as a skill (Graphify-Labs/graphify)" ;;
  headroom)        echo "Local compression proxy for model context (headroomlabs-ai/headroom)" ;;
esac; }
tool_needs() { case "$1" in graphify|headroom) echo uv ;; *) echo "" ;; esac; }

# --- helpers -----------------------------------------------------------------
say()  { printf '%s\n' "$*"; }
warn() { printf '%s\n' "$*" >&2; }
installed() { command -v "$(tool_bin "$1")" >/dev/null 2>&1; }
version() {
  local out
  out="$(timeout 5 "$(tool_bin "$1")" --version 2>&1 | head -1)" || true
  printf '%s' "${out:-unknown}"
}

# step <description> <cmd...>: print the command; run it only with --yes.
step() {
  local desc="$1"; shift
  if [[ $YES -eq 1 ]]; then say "  run      $desc: $*"; "$@"
  else say "  would    $desc: $*"; fi
}

# remote_script <url> <shell> [args...]: download to a temp file, show sha256, run.
remote_script() {
  local url="$1" sh="$2"; shift 2
  if [[ $YES -ne 1 ]]; then say "  would    download $url and run it with $sh $*"; return 0; fi
  local f; f="$(mktemp)" || return 1
  if ! curl -fsSL --proto '=https' --tlsv1.2 -o "$f" "$url"; then
    rm -f "$f"; warn "download failed: $url"; return 1
  fi
  say "  fetched  $url"
  say "  sha256   $(sha256sum "$f" | cut -d' ' -f1)"
  "$sh" "$f" "$@"; local rc=$?
  rm -f "$f"; return $rc
}

# --- per-tool install / remove -------------------------------------------------
do_install() { case "$1" in
  uv)              remote_script https://astral.sh/uv/install.sh sh ;;
  rtk)             remote_script https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh sh
                   say "  next     rtk init -g   (installs the Claude Code hook; then restart Claude Code)" ;;
  codebase-memory) remote_script https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh bash
                   say "  next     restart Claude Code and check /mcp"
                   say "  next     ms-workspace claude-md --refresh   (updates a generated workspace CLAUDE.md only; yours is never touched)" ;;
  graphify)        step "install package" uv tool install graphifyy \
                   && step "register skill" graphify install
                   say "  next     in Claude Code run: /graphify ." ;;
  headroom)        step "install package" uv tool install --python 3.13 "headroom-ai[all]"
                   say "  next     headroom doctor; then headroom wrap claude"
                   say "  note     it sends an anonymous beacon by default; opt out with HEADROOM_TELEMETRY=off" ;;
esac; }

do_remove() { case "$1" in
  uv)              say "  manual   uv has no uninstall command; delete ~/.local/bin/uv and ~/.local/bin/uvx yourself" ;;
  rtk)             say "  manual   rtk documents no uninstall; remove its hook from ~/.claude/settings.json and delete $(command -v rtk)" ;;
  codebase-memory) step "uninstall" codebase-memory-mcp uninstall \
                   && say "  next     ms-workspace claude-md --refresh   (updates a generated workspace CLAUDE.md only; yours is never touched)" ;;
  graphify)        step "unregister" graphify uninstall \
                   && step "remove package" uv tool uninstall graphifyy ;;
  headroom)        step "unwrap" headroom unwrap claude \
                   ; step "remove package" uv tool uninstall headroom-ai ;;
esac; }

known() { tool_bin "$1" >/dev/null 2>&1; }

check_needs() {
  local t="$1" n ok=0
  for n in $(tool_needs "$t"); do
    command -v "$n" >/dev/null 2>&1 && continue
    [[ " ${PLAN[*]} " == *" $n "* ]] && continue   # installed earlier in this same run
    warn "  missing  $t needs '$n' (run: powers.sh install $n --yes)"
    ok=1
  done
  return $ok
}

# --- commands ------------------------------------------------------------------
cmd_list() {
  local t state
  printf '%-16s %-10s %s\n' TOOL STATE DESCRIPTION
  for t in "${TOOLS[@]}"; do
    state=missing; installed "$t" && state=installed
    printf '%-16s %-10s %s\n' "$t" "$state" "$(tool_desc "$t")"
  done
}

cmd_doctor() {
  local t
  for t in "${TOOLS[@]}"; do
    if installed "$t"; then printf '  ok       %-16s %s\n' "$t" "$(version "$t")"
    else printf '  missing  %s\n' "$t"; fi
  done
  if installed rtk && ! rtk gain >/dev/null 2>&1; then
    warn "  warning  'rtk gain' fails: you may have the unrelated 'Rust Type Kit' rtk installed"
  fi
}

cmd_change() {  # install | remove
  local action="$1"; shift
  PLAN=()
  local t rc=0
  for t in "$@"; do
    known "$t" || { warn "unknown tool: $t (see: powers.sh list)"; return 2; }
    PLAN+=("$t")
  done
  [[ ${#PLAN[@]} -gt 0 ]] || { warn "give at least one tool (see: powers.sh list)"; return 2; }
  [[ $YES -eq 1 ]] || say "(plan only: add --yes to run it)"
  for t in "${PLAN[@]}"; do
    say "$action $t: $(tool_desc "$t")"
    if [[ $action == install ]]; then
      if installed "$t"; then say "  ok       already installed ($(version "$t"))"; continue; fi
      check_needs "$t" || { rc=1; continue; }
      do_install "$t" || { warn "  failed   $t"; rc=1; continue; }
    else
      installed "$t" || { say "  ok       not installed"; continue; }
      do_remove "$t" || { warn "  failed   $t"; rc=1; }
    fi
  done
  return $rc
}

main() {
  local cmd="${1:-}"; [[ $# -gt 0 ]] && shift
  local args=() a
  for a in "$@"; do if [[ $a == --yes ]]; then YES=1; else args+=("$a"); fi; done
  case "$cmd" in
    list)    cmd_list ;;
    doctor)  cmd_doctor ;;
    install|remove) cmd_change "$cmd" "${args[@]+"${args[@]}"}" ;;
    -h|--help|"") sed -n '2,11p' "${BASH_SOURCE[0]}" ;;
    *) warn "unknown command: $cmd"; return 2 ;;
  esac
}
main "$@"
