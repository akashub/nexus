#!/usr/bin/env bash
# Nexus SessionEnd hook — ingests knowledge ledger + runs quiet scan.
set -euo pipefail

if ! command -v nexus &>/dev/null; then exit 0; fi

LOG_FILE="${HOME}/.nexus/hook.log"
mkdir -p "$(dirname "$LOG_FILE")"

LEDGER="/tmp/nexus-ledger.jsonl"
if [ -f "$LEDGER" ]; then
  timeout 30 nexus ingest "$LEDGER" --quiet 2>>"$LOG_FILE" || true
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -n "$PROJECT_DIR" ]; then
  timeout 60 nexus scan "$PROJECT_DIR" --quiet 2>>"$LOG_FILE" || true
fi
