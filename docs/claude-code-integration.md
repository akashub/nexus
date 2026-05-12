# AI Tool Integration

Nexus integrates with AI coding tools via MCP (Model Context Protocol). Run `nexus mcp install` to auto-detect and configure all supported tools.

## Supported tools

| Tool | Config location | Format |
|------|----------------|--------|
| **Claude Code** | `~/.claude.json` | JSON `mcpServers` |
| **Cursor** | `~/.cursor/mcp.json` | JSON `mcpServers` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | JSON `mcpServers` |
| **VS Code** | `~/Library/Application Support/Code/User/mcp.json` | JSON `servers` |
| **Codex** | `~/.codex/config.toml` | TOML `[mcp_servers.nexus]` |
| **Gemini CLI** | `~/.gemini/settings.json` | JSON `mcpServers` |

## What gets installed

`nexus mcp install` auto-detects which tools are on your machine and configures each one. For Claude Code, it also installs:

| Component | Purpose | Location |
|-----------|---------|----------|
| **MCP Server** | Gives the AI read/write access to your knowledge graph | Tool-specific config |
| **Hooks** | Auto-captures package installs and runs scans on session end | `~/.claude/settings.json` |
| **Skill** | Teaches Claude when and how to call Nexus MCP tools | `~/.claude/skills/nexus/SKILL.md` |

Hooks and skill are Claude Code-specific. Other tools get the MCP server only.

## How passive capture works (Claude Code)

1. You work normally in Claude Code
2. Claude notices new tools/frameworks and writes entries to `/tmp/nexus-ledger.jsonl`
3. The PostToolUse hook catches `npm install`, `pip install`, `brew install`, `cargo add` commands
4. When the session ends, the SessionEnd hook runs `nexus ingest` + `nexus scan`
5. Your knowledge graph grows automatically

## Setup

```bash
nexus mcp install              # auto-detect and configure all tools
nexus mcp install --tool cursor  # configure a specific tool only
```

## Check status

```bash
nexus mcp install --check   # shows status for all 6 tools
nexus status                # full status with DB stats
```

## Uninstall

```bash
nexus mcp install --uninstall   # removes Nexus from all tools
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
