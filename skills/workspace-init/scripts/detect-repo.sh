#!/usr/bin/env bash
# Detect the basics of a git repo and print them as one JSON object.
# Usage: detect-repo.sh <repo-dir>
# Deterministic on purpose: keeps the skill cheap in tokens.
set -euo pipefail

DIR="${1:?usage: detect-repo.sh <repo-dir>}"
[[ -e "$DIR/.git" ]] || { echo "ERROR: '$DIR' is not a git repo" >&2; exit 1; }
cd "$DIR"

url="$(git remote get-url origin 2>/dev/null || true)"

# Default branch: origin/HEAD, falling back to the current branch.
default="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
[[ -n "$default" ]] || default="$(git branch --show-current)"

# Base branch: prefer "next" when it exists (locally or on origin).
base="$default"
if git show-ref --verify --quiet refs/heads/next || git show-ref --verify --quiet refs/remotes/origin/next; then
  base="next"
fi

stacks=()
test_cmds=()
add() { stacks+=("$1"); test_cmds+=("$2"); }

[[ -f pom.xml ]] && add maven "mvn -T1C -B test"
{ [[ -f build.gradle.kts ]] || [[ -f build.gradle ]]; } && add gradle "./gradlew test"
if [[ -f package.json ]]; then
  if [[ -f pnpm-workspace.yaml ]] || [[ -f pnpm-lock.yaml ]]; then add pnpm "pnpm -r test"
  elif [[ -f yarn.lock ]]; then add yarn "yarn test"
  else add npm "npm test"; fi
fi
[[ -f go.mod ]] && add go "go test ./..."
{ [[ -f pyproject.toml ]] || [[ -f requirements.txt ]]; } && add python "pytest"
[[ -f Cargo.toml ]] && add rust "cargo test"

compose=false
{ [[ -f docker-compose.yml ]] || [[ -f docker-compose.yaml ]] || [[ -f compose.yaml ]]; } && compose=true
has_claude_md=false
[[ -f CLAUDE.md ]] && has_claude_md=true

jq -n \
  --arg name "$(basename "$PWD")" \
  --arg url "$url" \
  --arg default "$default" \
  --arg base "$base" \
  --argjson compose "$compose" \
  --argjson claude_md "$has_claude_md" \
  --argjson stacks "$(printf '%s\n' "${stacks[@]:-}" | jq -R . | jq -s 'map(select(length>0))')" \
  --argjson tests "$(printf '%s\n' "${test_cmds[@]:-}" | jq -R . | jq -s 'map(select(length>0))')" \
  '{name:$name, url:$url, default_branch:$default, base:$base, stacks:$stacks,
    suggested_test:$tests, has_compose:$compose, has_claude_md:$claude_md}'
