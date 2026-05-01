#!/usr/bin/env bash
# Nexus SessionEnd hook — ingests knowledge ledger + runs quiet scan.
set -euo pipefail

if ! command -v nexus &>/dev/null; then exit 0; fi

# Ingest knowledge ledger if it exists
if [ -f /tmp/nexus-ledger.jsonl ]; then
  nexus ingest /tmp/nexus-ledger.jsonl 2>/dev/null || true
fi

# Scan project directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
[ -n "$PROJECT_DIR" ] && nexus scan "$PROJECT_DIR" --quiet 2>/dev/null || true
