#!/usr/bin/env bash
# Nexus PostToolUse hook — captures package installs into the knowledge graph.
# Fires on Bash tool use; parses install commands and calls `nexus track`.
set -euo pipefail

# Only fire on Bash tool
[ "${TOOL_NAME:-}" = "Bash" ] || exit 0

INPUT="${TOOL_INPUT:-}"
[ -n "$INPUT" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${PWD}}"

track() {
  local name="$1" source="$2" dev="${3:-}"
  nexus track "$name" --project-dir "$PROJECT_DIR" --source "$source" ${dev:+--dev} --quiet 2>/dev/null || true
}

# npm / pnpm / yarn
if echo "$INPUT" | grep -qE '(npm install|pnpm add|yarn add)'; then
  dev=""
  echo "$INPUT" | grep -qE '(-D|--save-dev)' && dev="1"
  for pkg in $(echo "$INPUT" | grep -oE '(npm install|pnpm add|yarn add)\s+.*' | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "npm" "$dev"
  done
  exit 0
fi

# pip / uv add
if echo "$INPUT" | grep -qE '(pip install|uv add)'; then
  for pkg in $(echo "$INPUT" | grep -oE '(pip install|uv add)\s+.*' | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "pip"
  done
  exit 0
fi

# brew
if echo "$INPUT" | grep -qE 'brew install'; then
  for pkg in $(echo "$INPUT" | grep -oE 'brew install\s+.*' | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "brew"
  done
  exit 0
fi

# cargo add
if echo "$INPUT" | grep -qE 'cargo add'; then
  for pkg in $(echo "$INPUT" | grep -oE 'cargo add\s+.*' | sed 's/^[^ ]* [^ ]* //' | tr ' ' '\n' | grep -v '^-'); do
    [ -n "$pkg" ] && track "$pkg" "cargo"
  done
  exit 0
fi
