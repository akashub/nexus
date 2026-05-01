#!/usr/bin/env bash
# Nexus PostToolUse hook — captures package installs into the knowledge graph.
# Fires on Bash tool use; parses install commands and calls `nexus track`.
set -uo pipefail

# Read hook payload from stdin (Claude Code passes JSON on stdin).
HOOK_JSON="$(cat)"

TOOL_NAME="$(echo "$HOOK_JSON" | jq -r '.tool_name // empty' 2>/dev/null)"
[ "$TOOL_NAME" = "Bash" ] || exit 0

INPUT="$(echo "$HOOK_JSON" | jq -r '.tool_input.command // empty' 2>/dev/null)"
[ -n "$INPUT" ] || exit 0

if ! command -v nexus &>/dev/null; then exit 0; fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${PWD}}"
LOG_FILE="${HOME}/.nexus/hook.log"
mkdir -p "$(dirname "$LOG_FILE")"

track() {
  local name="$1" source="$2" dev="${3:-}"
  # Strip version pins: react@18.2 -> react, fastapi==0.100 -> fastapi
  name="$(echo "$name" | sed -E 's/[@=><~!].*//')"
  [ -z "$name" ] && return 0
  timeout 10 nexus track "$name" --project-dir "$PROJECT_DIR" --source "$source" \
    ${dev:+--dev} --quiet 2>>"$LOG_FILE" || true
}

# npm / pnpm / yarn — match install/add but not uninstall
if echo "$INPUT" | grep -qE '\b(npm install|npm i|pnpm add|yarn add)\b'; then
  dev=""
  echo "$INPUT" | grep -qE '(-D|--save-dev)' && dev="1"
  # Skip global installs
  echo "$INPUT" | grep -qE '(^|\s)-g(\s|$)|--global\b' && exit 0
  for pkg in $(echo "$INPUT" | grep -oE '\b(npm install|npm i|pnpm add|yarn add)\s+.*' \
    | sed -E 's/^[^ ]+ (install|add|i) //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "npm" "$dev"
  done
  exit 0
fi

# pip / uv add
if echo "$INPUT" | grep -qE '\b(pip install|uv add)\b'; then
  for pkg in $(echo "$INPUT" | grep -oE '\b(pip install|uv add)\s+.*' \
    | sed -E 's/^[^ ]+ (install|add) //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "pip"
  done
  exit 0
fi

# brew
if echo "$INPUT" | grep -qE '\bbrew install\b'; then
  for pkg in $(echo "$INPUT" | grep -oE '\bbrew install\s+.*' \
    | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "brew"
  done
  exit 0
fi

# cargo add
if echo "$INPUT" | grep -qE '\bcargo add\b'; then
  for pkg in $(echo "$INPUT" | grep -oE '\bcargo add\s+.*' \
    | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "cargo"
  done
  exit 0
fi
