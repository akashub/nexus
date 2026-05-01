# Nexus V2 — Claude Code Integration Plan

## Design Decisions (Confirmed)

1. **Expertise levels: inferred from graph density** (no new schema)
   - **Known well**: concept has description + edges (>= 1) + embedding. All three present.
   - **Seen**: concept exists in DB but missing one or more of {description, edges, embedding}. Scanned but unenriched.
   - **Gap**: concept appears in the active project's `package.json`/`pyproject.toml`/CLAUDE.md but is absent from the graph entirely. Gap detection is relative to the active project's dependency files.

2. **Hook transport: CLI subprocess for hooks, MCP imports DB directly**
   - Claude Code hooks (`PostToolUse`, `SessionEnd`) shell out to `nexus` CLI commands.
   - MCP server is a Python process that imports `nexus.db`, `nexus.models`, etc. directly — no HTTP layer.
   - Hooks match Eagle Mem's existing wiring pattern in `~/.claude/settings.json`.

3. **Skill scope: global** (`~/.claude/skills/nexus/`)
   - Nexus is a personal knowledge graph spanning all projects.
   - Hooks fire globally via `~/.claude/settings.json`.
   - Project resolution at runtime: `$CLAUDE_PROJECT_DIR` env var (set by Claude Code) -> `get_project_by_path(cwd)` -> if missing, auto-create project -> proceed.

4. **MCP self-registration: `nexus mcp install`**
   - Writes MCP server entry into `~/.claude.json` under `mcpServers`.
   - Idempotent: re-running is a no-op if entry already exists with same config.

5. **Onboard output: both formats**
   - CLI gets a table (default). MCP gets JSON (default).
   - `--format` flag on CLI: `table` (default) | `json`.
   - MCP tool always returns structured JSON.

---

## Architecture Overview

```
Claude Code Session
  |
  |-- PostToolUse hook (Bash matcher)
  |     fires on: npm install, pip install, brew install, etc.
  |     runs: nexus track <package> --project-dir $CLAUDE_PROJECT_DIR
  |
  |-- SessionEnd hook
  |     runs: nexus scan $CLAUDE_PROJECT_DIR --quiet
  |
  |-- MCP Server (nexus-mcp)
  |     tools: search, onboard, expertise, concepts, projects
  |     imports DB modules directly (no HTTP)
  |
  |-- Skill file (~/.claude/skills/nexus/nexus.md)
  |     instructions for Claude Code to use MCP tools
  |     and interpret onboard output
  |
  +-- CLI (nexus track, nexus onboard, nexus mcp install)
        new commands layered onto existing CLI
```

**Project resolution flow (hooks):**
1. Hook fires, receives `$CLAUDE_PROJECT_DIR` from Claude Code environment
2. `nexus track` / `nexus scan` resolves project: `get_project_by_path(cwd)`
3. If no project found: auto-create from directory name + path
4. Proceed with project-scoped operation

---

## Phase 1: `nexus track` — Real-Time Concept Capture

A lightweight command that adds a single concept from an install command, designed to be called by PostToolUse hooks.

### 1.1 CLI command: `nexus track`

```
nexus track <name> --project-dir <path> [--source npm|pip|brew|cargo] [--dev]
```

Behavior:
- Resolves project from `--project-dir` (auto-creates if needed)
- Checks if concept already exists in project (by name, case-insensitive)
- If exists: no-op, exit 0 (fast path for hooks)
- If new: insert concept with `source="hook_capture"`, category inferred from source type
- Stores setup command (e.g., `npm install react`) derived from source + name + dev flag
- Does NOT enrich (hooks must be fast). Enrichment deferred to `nexus scan --enrich` or manual.

**Files:**
- `backend/src/nexus/cli_track.py` (~60 LOC) — Click command implementation
- `backend/src/nexus/cli.py` — add `main.add_command(track_cmd)` import

**Test cases:**
- `backend/tests/test_track.py`:
  - `test_track_new_concept` — concept added with correct project_id and setup_command
  - `test_track_existing_noop` — existing concept not duplicated, exit 0
  - `test_track_auto_creates_project` — new project created from path when absent
  - `test_track_dev_dependency` — `--dev` flag produces `npm install -D <name>`

**Done when:** `nexus track react --project-dir /path/to/project --source npm` creates a concept in the correct project with `source="hook_capture"` and `setup_commands=["npm install react"]`.

### 1.2 PostToolUse hook script

Shell script that parses Bash tool output for install patterns and calls `nexus track`.

**File:** `backend/src/nexus/hooks/post-tool-use.sh` (~50 lines)

The script:
1. Reads `$TOOL_NAME` — only fires on `Bash`
2. Reads `$TOOL_INPUT` — the command that was run
3. Pattern-matches against install commands:
   - `npm install <pkg>`, `pnpm add <pkg>`, `yarn add <pkg>` -> source=npm
   - `pip install <pkg>`, `uv add <pkg>` -> source=pip
   - `brew install <pkg>` -> source=brew
   - `cargo add <pkg>` -> source=cargo
4. Extracts package name(s), detects `--save-dev` / `-D` for dev deps
5. For each package: `nexus track <name> --project-dir "$CLAUDE_PROJECT_DIR" --source <type> [--dev]`
6. Exits 0 always (hook failures must not break Claude Code)

**Test cases:**
- `backend/tests/test_hook_parsing.py`:
  - `test_parse_npm_install` — `npm install react express` yields two track calls
  - `test_parse_npm_dev` — `npm install -D vitest` detects dev flag
  - `test_parse_pip_install` — `pip install fastapi uvicorn` yields two calls
  - `test_parse_uv_add` — `uv add click` yields pip source
  - `test_ignore_non_install` — `npm run build` produces no calls
  - `test_scoped_packages` — `npm install @tanstack/react-query` preserves scope

**Done when:** Installing a package in a Claude Code session auto-creates a Nexus concept without user intervention.

### 1.3 SessionEnd hook script

Runs a quiet scan of the project directory at session end.

**File:** `backend/src/nexus/hooks/session-end.sh` (~15 lines)

```bash
#!/usr/bin/env bash
# Nexus auto-scan on Claude Code session end
if [ -z "$CLAUDE_PROJECT_DIR" ]; then exit 0; fi
if ! command -v nexus &>/dev/null; then exit 0; fi
nexus scan "$CLAUDE_PROJECT_DIR" --quiet 2>/dev/null || true
```

Requires adding `--quiet` flag to `nexus scan` (suppress output except errors).

**Files changed:**
- `backend/src/nexus/cli_scan.py` — add `--quiet` option (~5 lines)

**Done when:** Ending a Claude Code session triggers a background scan. No output unless error.

---

## Phase 2: Expertise Profiling — `nexus onboard`

A command that generates a snapshot of what the developer knows, has seen, and is missing in a project.

### 2.1 Expertise classification logic

**File:** `backend/src/nexus/expertise.py` (~80 LOC)

```python
@dataclass
class ExpertiseEntry:
    name: str
    level: str  # "known_well" | "seen" | "gap"
    category: str | None
    signals: list[str]  # what evidence produced this classification

def classify_expertise(
    conn: Connection, project_id: str,
) -> list[ExpertiseEntry]:
    ...
```

Classification rules:
- **known_well**: `description IS NOT NULL AND embedding IS NOT NULL AND edge_count >= 1`
- **seen**: concept exists in graph for this project, but fails one or more known_well conditions
- **gap**: name appears in project's dependency files (`package.json`, `pyproject.toml`, etc.) but has no matching concept in the graph

Gap detection:
- Re-uses existing scanner output: `scan_npm(path)` and `scan_python(path)` return `ScanResult.concepts`
- Only inspects top-level direct dependencies (e.g., `dependencies` and `devDependencies` keys in `package.json`, not `node_modules` or transitive resolution; `[project.dependencies]` in `pyproject.toml`, not the full lock file)
- Compare scanned concept names against DB concepts for this project
- Names in scan but not in DB = gaps

**Test cases:**
- `backend/tests/test_expertise.py`:
  - `test_known_well_all_signals` — concept with desc + embedding + edge = known_well
  - `test_seen_missing_embedding` — concept without embedding = seen
  - `test_seen_no_edges` — concept with desc + embedding but 0 edges = seen
  - `test_gap_detection` — package in package.json but absent from DB = gap
  - `test_no_false_gaps` — package in DB is not reported as gap
  - `test_mixed_profile` — project with all three levels represented

**Done when:** `classify_expertise(conn, project_id)` returns a list where React (enriched, connected) is "known_well", Tailwind (scanned, no edges) is "seen", and Playwright (in package.json, not in graph) is "gap".

### 2.2 CLI command: `nexus onboard`

```
nexus onboard [project]              # table output (default)
nexus onboard [project] --format json  # JSON output
nexus onboard --project-dir .        # resolve project from cwd
```

**File:** `backend/src/nexus/cli_onboard.py` (~70 LOC)

Table output format:
```
Expertise Profile: nexus (32 concepts)

KNOWN WELL (12)
  react           framework    desc + 3 edges + embedding
  fastapi         framework    desc + 5 edges + embedding
  cytoscape.js    framework    desc + 2 edges + embedding
  ...

SEEN (15)
  postcss         devtool      no edges
  d3-force        framework    no embedding
  ...

GAPS (5)
  playwright      -            in package.json, not in graph
  msw             -            in package.json, not in graph
  ...
```

JSON output format:
```json
{
  "project": "nexus",
  "total": 32,
  "known_well": [{"name": "react", "category": "framework", "signals": ["desc", "3 edges", "embedding"]}],
  "seen": [...],
  "gaps": [...]
}
```

**Files changed:**
- `backend/src/nexus/cli.py` — add `main.add_command(onboard_cmd)` import

**Test cases:**
- `backend/tests/test_onboard_format.py`:
  - `test_table_renders` — table output contains expected sections
  - `test_json_parses` — JSON output is valid JSON with correct schema
  - `test_empty_project` — graceful output when project has no concepts

**Done when:** `nexus onboard nexus` prints a readable expertise profile. `--format json` produces valid JSON that the MCP can relay to Claude Code.

### 2.3 API endpoint

**File:** `backend/src/nexus/routes_projects.py` — add endpoint (~15 lines)

```
GET /api/projects/:id/expertise    # returns JSON expertise profile
```

**Done when:** Desktop app or MCP can fetch expertise profile via API.

---

## Phase 3: MCP Server

An MCP (Model Context Protocol) server that gives Claude Code direct access to the Nexus knowledge graph.

### 3.1 MCP server entrypoint

**File:** `backend/src/nexus/mcp_server.py` (~80 LOC)

- Uses `mcp` Python SDK (`mcp[cli]`)
- Stdio transport (Claude Code launches it as a subprocess via `nexus mcp serve`)
- Imports `nexus.db`, `nexus.models` directly — no HTTP
- Per-tool-call connections: each tool handler opens its own `get_connection()` in a `try/finally` block (matches `server.py` pattern at lines 38-43, safe for long-lived process with concurrent calls)
- Launched via CLI: `nexus mcp serve` subcommand (avoids uv/path resolution issues)

### 3.2 MCP tool definitions

**File:** `backend/src/nexus/mcp_tools.py` (~180 LOC)

Tools exposed to Claude Code:

| Tool | Params | Returns | Wraps |
|------|--------|---------|-------|
| `search_concepts` | `query: str, project_id?: str, semantic?: bool, limit?: int` | `[{name, category, summary, description}]` | `search_fts()` or embedding similarity via `list_concepts()` + `cosine_similarity()` |
| `get_concept` | `name: str` | `{name, description, summary, category, tags, quickstart, doc_url, edges: [{target, relationship}]}` | `get_concept()` + `get_edges()` |
| `list_projects` | (none) | `[{name, path, concept_count, last_scanned_at}]` | `list_projects()` + `count_concepts()` |
| `get_expertise` | `project_id?: str, project_dir?: str` | `{known_well: [...], seen: [...], gaps: [...]}` | `classify_expertise()` from Phase 2 |
| `onboard` | `project_id?: str, project_dir?: str` | `{project, total, known_well, seen, gaps}` | Same as expertise but with richer metadata |
| `add_concept` | `name: str, project_dir?: str, category?: str` | `{id, name, category}` | `add_concept()` |
| `track_install` | `name: str, source: str, project_dir: str, dev?: bool` | `{status: "added"|"exists", name}` | Shared `track_concept()` function (see below) |

**Shared core logic:** `cli_track.py` exports a `track_concept(conn, name, project_dir, source, dev)` function that both the CLI command and `track_install` MCP tool call. No duplicated logic.

Each tool:
1. Opens DB connection
2. Resolves project from `project_dir` if provided (same logic as hooks)
3. Executes query
4. Returns structured JSON
5. Closes connection

**Test cases:**
- `backend/tests/test_mcp_tools.py`:
  - `test_search_concepts_fts` — FTS search returns matching concepts
  - `test_search_concepts_semantic` — semantic search uses embeddings
  - `test_get_concept_with_edges` — includes edge info in response
  - `test_list_projects` — returns all projects with concept counts
  - `test_get_expertise` — returns classified expertise profile
  - `test_track_install_new` — adds new concept via MCP
  - `test_track_install_existing` — returns exists status for duplicate

**Done when:** Claude Code can query the knowledge graph via MCP tools without any HTTP server running.

### 3.3 `nexus mcp install` command

Writes the MCP server entry into Claude Code's config.

**File:** `backend/src/nexus/cli_mcp.py` (~70 LOC)

```
nexus mcp install              # install MCP server + hooks + skill (umbrella installer)
nexus mcp install --check      # check if already installed
nexus mcp install --uninstall  # remove MCP server + hooks + skill
nexus mcp serve                # start MCP server (called by Claude Code, not by user)
```

Note: `nexus mcp install` is the umbrella command that sets up everything: MCP server entry, PostToolUse/SessionEnd hooks, and skill file. It's the single command for full Claude Code integration.

**Target file:** `~/.claude.json`

**JSON entry written:**
```json
{
  "mcpServers": {
    "nexus": {
      "command": "nexus",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

Uses `nexus mcp serve` as the entrypoint (nexus is already a console_script entry point, so no uv/path resolution needed).

**Idempotency:** Reads existing `~/.claude.json`, checks if `mcpServers.nexus` exists. If present with same config, no-op. If present with different config, updates. If absent, adds. Preserves all other config. Creates `~/.claude.json` with minimal structure if file doesn't exist.

**Files changed:**
- `backend/src/nexus/cli.py` — add `main.add_command(mcp_group)` import

**Test cases:**
- `backend/tests/test_mcp_install.py`:
  - `test_install_fresh` — creates entry in empty mcpServers
  - `test_install_idempotent` — re-running doesn't duplicate
  - `test_install_preserves_other_servers` — existing MCP servers untouched
  - `test_uninstall` — removes nexus entry, preserves others
  - `test_check_installed` — reports correct status

**Done when:** `nexus mcp install` makes Nexus available as an MCP server in Claude Code. Re-running is safe.

---

## Phase 4: Claude Code Skill

A skill file that teaches Claude Code how to use Nexus MCP tools and hooks.

### 4.1 Skill file

**File:** `~/.claude/skills/nexus/nexus.md` (~100 lines)

Content (note: YAML frontmatter is required for Claude Code skill discovery):
```markdown
---
name: nexus
description: Query and update the Nexus personal knowledge graph. Tracks tools, frameworks, and concepts across projects.
---

# Nexus Knowledge Graph

Nexus is a personal developer knowledge graph. It tracks tools, frameworks,
and concepts you learn across projects.

## Available MCP Tools

Use these tools to interact with the knowledge graph:

### Onboarding (start of session)
- `nexus.onboard(project_dir)` — get expertise profile for current project
  Shows what you know well, what you've seen, and what's missing.
  Use this at session start to understand the developer's context.

### Search & Lookup
- `nexus.search_concepts(query)` — find concepts by keyword or semantic similarity
- `nexus.get_concept(name)` — get full detail including description, quickstart, edges

### Projects
- `nexus.list_projects()` — see all tracked projects

### Capture
- `nexus.add_concept(name, project_dir, category)` — add a concept manually
- `nexus.track_install(name, source, project_dir)` — record an install
  (PostToolUse hook does this automatically for npm/pip/brew/cargo installs)

## When to Use

- **Session start**: Call `onboard` to understand what the developer knows
- **Before explaining a tool**: Check `get_concept` — if known_well, skip basics
- **When developer asks "what do I know about X"**: Use `search_concepts`
- **After installing something**: Hook handles this automatically, but you can
  verify with `get_concept`
- **When suggesting tools**: Check `get_expertise` to avoid suggesting things
  the developer already knows
```

### 4.2 Hook registration

The hooks from Phase 1 need to be registered in `~/.claude/settings.json`.

`nexus mcp install` (Phase 3.3) also registers the hooks. Alternatively, a separate `nexus hooks install` command.

Decision: bundle hook registration into `nexus mcp install` (single install command for everything).

**Hook entries added to `~/.claude/settings.json`:**

Hook script paths are resolved at install time using `importlib.resources.files("nexus") / "hooks" / "post-tool-use.sh"` to get the absolute path of the bundled script. The resolved absolute path is written into settings.json.

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "/abs/path/to/nexus/hooks/post-tool-use.sh"
      }]
    }
  ],
  "SessionEnd": [
    {
      "hooks": [{
        "type": "command",
        "command": "/abs/path/to/nexus/hooks/session-end.sh"
      }]
    }
  ]
}
```

Note: must merge with existing hooks (Eagle Mem already has PostToolUse and SessionEnd entries). The install command appends to existing arrays, doesn't replace them.

**Test cases:**
- `backend/tests/test_hook_registration.py`:
  - `test_merges_with_existing_hooks` — Eagle Mem hooks preserved
  - `test_no_duplicate_hooks` — re-running doesn't duplicate entries

**Done when:** `nexus mcp install` sets up MCP server + hooks + skill file in one command. Claude Code has full Nexus integration after running it.

---

## Phase 5: Skill File Deployment + Polish

### 5.1 Install command copies skill file

Extend `nexus mcp install` to also copy the skill file to `~/.claude/skills/nexus/nexus.md`.

**Files changed:**
- `backend/src/nexus/cli_mcp.py` — add skill file copy logic (~15 lines)
- `backend/src/nexus/skills/nexus.md` — skill file bundled with package (source of truth)

### 5.2 `nexus status` command

Quick health check showing integration status.

```
nexus status
```

Output:
```
Nexus Integration Status
  Database:    ~/.nexus/nexus.db (42 concepts, 3 projects)
  MCP Server:  installed (in ~/.claude.json)
  Hooks:       installed (PostToolUse + SessionEnd)
  Skill:       installed (~/.claude/skills/nexus/nexus.md)
  Ollama:      running (gemma4:e2b)
```

**File:** `backend/src/nexus/cli_status.py` (~60 LOC)

**Files changed:**
- `backend/src/nexus/cli.py` — add `main.add_command(status_cmd)` import

**Done when:** `nexus status` shows green/red for each integration component.

---

## Implementation Order

| Step | What | Depends On | Effort | New Files |
|------|------|-----------|--------|-----------|
| 1 | `nexus track` CLI command | Nothing (existing DB) | 0.5 day | `cli_track.py` (~60 LOC) |
| 2 | PostToolUse hook script | Step 1 | 0.5 day | `hooks/post-tool-use.sh` (~50 lines) |
| 3 | SessionEnd hook script + `--quiet` flag | Nothing | 0.25 day | `hooks/session-end.sh` (~15 lines) |
| 4 | Expertise classification | Nothing | 0.5 day | `expertise.py` (~80 LOC) |
| 5 | `nexus onboard` CLI | Step 4 | 0.5 day | `cli_onboard.py` (~70 LOC) |
| 6 | Onboard API endpoint | Step 4 | 0.25 day | (modify `routes_projects.py`) |
| 7 | MCP server entrypoint | Nothing | 0.5 day | `mcp_server.py` (~80 LOC) |
| 8 | MCP tool definitions | Steps 4, 7 | 1 day | `mcp_tools.py` (~180 LOC) |
| 9 | `nexus mcp install` (MCP + hooks + skill) | Steps 2, 3, 7, 8 | 0.5 day | `cli_mcp.py` (~70 LOC) |
| 10 | Skill file | Step 8 | 0.25 day | `skills/nexus.md` (~100 lines) |
| 11 | `nexus status` | Step 9 | 0.25 day | `cli_status.py` (~60 LOC) |
| 12 | Tests for all phases | Steps 1-11 | 1 day | 6 test files |

**Total: ~6 working days**

Steps 1-3 and 4-6 can be parallelized. Step 7 can start immediately. Step 8 depends on 4+7. Step 9 is the integration point.

**Critical path:** Step 4 (expertise) -> Step 8 (MCP tools) -> Step 9 (install command)

---

## File Impact Summary

**New files (12):**
- `backend/src/nexus/cli_track.py` — track command (~60 LOC)
- `backend/src/nexus/cli_onboard.py` — onboard command (~70 LOC)
- `backend/src/nexus/cli_mcp.py` — mcp install/check/uninstall (~70 LOC)
- `backend/src/nexus/cli_status.py` — status command (~60 LOC)
- `backend/src/nexus/expertise.py` — expertise classification (~80 LOC)
- `backend/src/nexus/mcp_server.py` — MCP entrypoint (~80 LOC)
- `backend/src/nexus/mcp_tools.py` — MCP tool definitions (~180 LOC)
- `backend/src/nexus/hooks/post-tool-use.sh` — PostToolUse hook (~50 lines)
- `backend/src/nexus/hooks/session-end.sh` — SessionEnd hook (~15 lines)
- `backend/src/nexus/skills/nexus.md` — Claude Code skill (~100 lines)
- `backend/tests/test_track.py` — track tests
- `backend/tests/test_expertise.py` — expertise tests
- `backend/tests/test_onboard_format.py` — onboard output tests
- `backend/tests/test_mcp_tools.py` — MCP tool tests
- `backend/tests/test_mcp_install.py` — install idempotency tests
- `backend/tests/test_hook_parsing.py` — hook pattern matching tests

**Modified files (4):**
- `backend/src/nexus/cli.py` — import new commands (track, onboard, mcp, status)
- `backend/src/nexus/cli_scan.py` — add `--quiet` flag
- `backend/src/nexus/routes_projects.py` — add expertise endpoint
- `backend/pyproject.toml` — add `mcp[cli]` dependency

**No frontend changes** in this plan. The expertise endpoint is available for future desktop UI, but this plan focuses on CLI + MCP integration.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| `$CLAUDE_PROJECT_DIR` not set in all hook contexts | Hooks silently fail, no capture | Check for env var, fallback to `$PWD`, log warning if neither available |
| PostToolUse hook fires on non-install Bash commands | Wasted CPU parsing irrelevant commands | Fast regex check at top of script, exit 0 immediately for non-matches |
| MCP SDK version incompatibility | Server won't start | Pin `mcp[cli]` version in pyproject.toml, test against Claude Code's expected protocol version |
| `~/.claude.json` doesn't exist yet | Install command fails | Create file with minimal structure if absent |
| Hook and Eagle Mem both fire on PostToolUse | Double processing or conflicts | Nexus hook only does `nexus track`, Eagle Mem hook does its own thing — orthogonal. No conflict. |
| 200 LOC limit on `mcp_tools.py` (7 tools) | May exceed limit | Each tool handler is ~25 lines; 7 x 25 = 175. If exceeded, split into `mcp_tools_query.py` and `mcp_tools_capture.py` |
| Expertise "gap" false positives from transitive deps | Noise in onboard output | Only report gaps for direct dependencies (top-level in package.json/pyproject.toml), not transitive |

---

## End-to-End Golden Path

### First-time setup:
```bash
cd ~/Development_dg/Project/nexus
nexus mcp install
# Output: MCP server installed, hooks registered, skill deployed
nexus status
# Output: all green
```

### Session start (Claude Code):
Claude Code starts a session in the nexus project. The skill instructs it to call `nexus.onboard(project_dir="/Users/Aakash/Development_dg/Project/nexus")`.

Output:
```json
{
  "project": "nexus",
  "total": 32,
  "known_well": [
    {"name": "react", "category": "framework", "signals": ["desc", "3 edges", "embedding"]},
    {"name": "fastapi", "category": "framework", "signals": ["desc", "5 edges", "embedding"]}
  ],
  "seen": [
    {"name": "postcss", "category": "devtool", "signals": ["no edges"]},
    {"name": "d3-force", "category": "framework", "signals": ["no embedding"]}
  ],
  "gaps": [
    {"name": "playwright", "signals": ["in package.json, not in graph"]}
  ]
}
```

Claude Code now knows: skip React/FastAPI basics, may need to explain d3-force more carefully, and Playwright is entirely new to this developer.

### During session (auto-capture):
Developer runs `npm install zod` in the session.

1. PostToolUse hook fires
2. Hook script parses: `npm install zod` -> package name `zod`, source `npm`
3. Runs: `nexus track zod --project-dir /Users/Aakash/Development_dg/Project/nexus --source npm`
4. Concept `zod` created with `source="hook_capture"`, `setup_commands=["npm install zod"]`

### Session end (auto-scan):
1. SessionEnd hook fires
2. Runs: `nexus scan /Users/Aakash/Development_dg/Project/nexus --quiet`
3. Picks up any new dependencies added to package.json during session
4. Updates `last_scanned_at` on project

### Manual check (CLI):
```bash
nexus onboard nexus
# Table showing known_well / seen / gaps for the nexus project

nexus onboard nexus --format json | jq '.gaps'
# JSON array of gap concepts
```

### MCP query (during Claude Code session):
```
Claude: Let me check what you know about testing tools...
[calls nexus.search_concepts("testing")]
-> Returns: vitest (known_well), playwright (gap)
Claude: I see you're familiar with vitest but haven't used Playwright yet.
        Let me explain Playwright from the ground up...
```
