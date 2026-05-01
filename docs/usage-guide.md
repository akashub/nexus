# Nexus — Usage Guide & Scenarios

How Nexus works across different setups, what to tell your teammates, and what role Claude plays.

## Install (2 minutes)

```bash
# Install from GitHub
uv tool install "git+https://github.com/akashub/nexus.git#subdirectory=backend"

# Wire into Claude Code
nexus mcp install

# Pull AI models (optional — everything works without Ollama)
ollama pull gemma4
ollama pull nomic-embed-text

# Initialize database
nexus db init
```

## Scenarios

### Fresh install, no projects

You install Nexus, run `nexus mcp install`, and open Claude Code in any directory.

**What happens automatically:**
- The `/nexus` skill teaches Claude how to write knowledge ledger entries
- The PostToolUse hook watches for `npm install`, `pip install`, `brew install`, `cargo add`
- The SessionEnd hook runs `nexus ingest` (processes ledger) + `nexus scan` (reads package files)

**Your first session:** You work normally. Claude notices tools/frameworks being used and logs entries to `/tmp/nexus-ledger.jsonl`. When the session ends, the hook ingests them. Your graph starts building from day one.

**No action needed from you.** Capture is passive.

### Existing projects — seeding the graph

Run `nexus scan` on any project to instantly populate the graph from package files:

```bash
nexus scan /path/to/my-project          # basic scan
nexus scan /path/to/my-project --enrich # also generate AI descriptions
```

This reads `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `Brewfile`, Dockerfiles, CI configs — extracts every dependency and tool, creates concepts, and links them to the project.

### Mid-project adoption (most common)

You've been working on a project for weeks and just installed Nexus.

1. `nexus scan .` — seeds the graph with everything in your package files
2. From now on, hooks auto-capture new installs and session-end scans catch changes
3. Run `nexus journey` to see your learning timeline build up over time

### With the desktop app

The desktop app is optional — for people who want to visualize their graph.

```bash
# Download from GitHub Releases, or build from source:
cd nexus/desktop && pnpm install && pnpm tauri dev
```

The app connects to `nexus serve` (FastAPI on localhost:7777). You get:
- Interactive knowledge graph — nodes colored by category, sized by connections
- Click a node → side panel with description, install instructions, connections
- Project selector → filter by project or see global cross-project view
- Search (Cmd+K) → find any concept
- Timeline view → see when you adopted each tool
- Gap detection → see what your project is missing

### Without the desktop app

Everything works from CLI + Claude Code:

```bash
nexus list                    # see all concepts
nexus search "testing"        # keyword search
nexus show playwright         # full detail + install instructions + connections
nexus journey                 # learning timeline
nexus gaps                    # what's missing from your project
nexus onboard --project .     # expertise profile (known_well / seen / gaps)
nexus status                  # check what's installed and working
```

Claude Code has full access via MCP — it reads your graph to give better suggestions and writes to it to capture new learning.

### With cloud AI models (optional)

For higher-quality enrichment, configure a cloud API key:

```bash
export NEXUS_CLOUD_PROVIDER=anthropic  # or openai
export NEXUS_CLOUD_API_KEY=sk-ant-...
nexus add "kubernetes" --model cloud   # uses Claude/GPT for enrichment
```

Ollama stays the default. Cloud is optional for when you want better descriptions or don't have Ollama running.

## What Claude Does

| During a session | How |
|-----------------|-----|
| Reads your graph | MCP tools: `search_graph`, `get_concept_detail`, `get_expertise` |
| Writes new concepts | MCP tool: `track_install`, `add_concept` |
| Logs rich entries | Writes to `/tmp/nexus-ledger.jsonl` (skill instructions) |
| Checks your gaps | MCP tool: `detect_gaps` |
| Shows your journey | MCP tool: `get_journey` |

| After a session | How |
|----------------|-----|
| Ingests ledger | SessionEnd hook → `nexus ingest` |
| Scans project | SessionEnd hook → `nexus scan` |

**Without MCP:** Claude can still write ledger entries (skill), and hooks still fire. You lose real-time graph queries — Claude can't check what you already know during the session.

**Without hooks:** You lose auto-capture. You'd need to run `nexus scan` and `nexus ingest` manually.

**Without the skill:** Claude doesn't know the ledger format. MCP and hooks still work, but you lose the rich session-context entries that Claude writes.

## What Our Engineering Built

| Layer | What we built |
|-------|--------------|
| Capture | PostToolUse hook, SessionEnd hook, ledger format, ingest pipeline |
| Enrichment | Ollama + cloud model abstraction, Context7 + PyPI/npm/GitHub fallbacks, embedding generation |
| Storage | SQLite + FTS5, migrations, dedup logic, concept/edge/project schema |
| Intelligence | Gap detection, relationship inference, semantic clustering, expertise profiling, journey timeline |
| Integration | MCP server (7 tools), `/nexus` skill, CLI (20+ commands) |
| Visualization | Tauri desktop app, Cytoscape.js graph, side panel, search, project views |
| Distribution | GitHub install, `nexus mcp install`, cross-platform CI builds |

## The Pitch

> Every time you use Claude Code, you learn new tools and frameworks — but that knowledge disappears when the session ends. Nexus captures it automatically.
>
> **Install in 2 minutes:**
> ```
> uv tool install "git+https://github.com/akashub/nexus.git#subdirectory=backend"
> nexus mcp install
> ```
>
> That's it. Now every Claude Code session automatically captures what tools and frameworks you're using. Run `nexus scan .` on your project to seed it with everything from your package files.
>
> Over time you build a personal knowledge graph — what you know, how things connect, which projects use what. Claude reads this graph and gives you better suggestions because it knows your stack.
>
> **What you get:**
> - `nexus journey` — see your learning timeline
> - `nexus gaps` — find what's missing from your project
> - `nexus onboard` — expertise profile across projects
> - `nexus show <tool>` — instant reference with install instructions
> - Desktop app — interactive graph visualization (optional)
>
> Zero config. Zero cloud dependency. Works offline with Ollama, or optionally with Claude/GPT for better enrichment.

## For Codex / Other AI Coding Tools

Nexus works with any tool that supports MCP servers. The `nexus mcp serve` command starts a stdio-transport MCP server. Register it in your tool's MCP config:

```json
{
  "nexus": {
    "command": "nexus",
    "args": ["mcp", "serve"]
  }
}
```

The skill file at `~/.claude/skills/nexus/SKILL.md` teaches the AI the ledger format. Copy it to your tool's equivalent skill/instruction directory.
