# Claude Code Integration

Nexus integrates with Claude Code through three components installed by `nexus mcp install`.

## What gets installed

| Component | Purpose | Location |
|-----------|---------|----------|
| **MCP Server** | Gives Claude read/write access to your knowledge graph | `~/.claude.json` |
| **Hooks** | Auto-captures package installs and runs scans on session end | `~/.claude/settings.json` |
| **Skill** | Teaches Claude the ledger format for logging tools as you work | `~/.claude/skills/nexus/SKILL.md` |

## How passive capture works

1. You work normally in Claude Code
2. Claude notices new tools/frameworks and writes entries to `/tmp/nexus-ledger.jsonl`
3. The PostToolUse hook catches `npm install`, `pip install`, `brew install`, `cargo add` commands
4. When the session ends, the SessionEnd hook runs `nexus ingest` + `nexus scan`
5. Your knowledge graph grows automatically

## Setup

```bash
nexus mcp install
```

## Check status

```bash
nexus mcp install --check   # quick check
nexus status                # full status with DB stats
```

## Uninstall

```bash
nexus mcp install --uninstall
```

## Knowledge Ledger Format

Claude Code writes entries to `/tmp/nexus-ledger.jsonl` during sessions. Each line is JSON:

```json
{
  "name": "zod",
  "description": "TypeScript-first schema validation with static type inference",
  "summary": "Schema validation + type inference",
  "category": "library",
  "context": "Added for API request validation in the Express backend",
  "project_dir": "/path/to/project",
  "relationships": [
    {"target": "typescript", "type": "depends_on"},
    {"target": "express", "type": "uses"}
  ]
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Tool, framework, or concept name |
| `description` | no | What it is |
| `summary` | no | One-liner |
| `category` | no | devtool, framework, library, concept, pattern, language |
| `context` | no | Why it was used in this session (stored as `notes`) |
| `project_dir` | no | Project directory path |
| `relationships` | no | Array of `{target, type}` objects |

### Relationship types

`uses`, `depends_on`, `similar_to`, `part_of`, `tested_with`, `configured_by`, `builds_into`, `wraps`, `serves`, `deployed_via`, `replaces`, `related_to`, `sends_data_to`, `triggers`
