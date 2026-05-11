# Structural Edge Pipeline — Design Spec

## Problem

The current edge creation system produces garbage relationships. It uses cosine similarity of embeddings to find concept pairs, then asks an LLM to guess the relationship type. This results in edges like `asyncpg depends_on @tanstack/react-query` and `netcdf4 related_to claude`. 45% of concepts (40/88) have zero edges. MCP — the core architecture concept of Farmerchat — has zero connections.

Root causes:
- `_suggest_connections` in `enrich.py` prints suggestions but never calls `add_edge()` — a dead function
- Embedding similarity measures topic closeness, not architectural relationships
- LLM is forced to pick a relationship type for any pair it receives, even unrelated ones
- Edges are global (not project-scoped), so cross-project garbage edges form
- Scanners extract concept names but not how they connect
- No pipeline chaining — scan, enrich, and connect are disconnected operations

## Approach: Hybrid — Structural Primary, LLM Gap-Fill

Use structural scanning (reading actual project files) as the primary edge source. Use the LLM only for orphaned concepts that have zero edges after the structural pass. Restrict similarity-based edges to `similar_to` with strict filters.

## Section 1: Structural Edge Sources

File-based scanners that produce high-confidence edges by reading actual project files.

### 1a. Package dependency edges (upgrade `packages.py`)

Current state: `_infer_npm_relationships` creates generic edges like "vitest tested_with react".

New behavior:
- Parse `dependencies` in package.json → every declared dependency gets a `uses` edge from the project. Known sub-package relationships are detected: if `@tailwindcss/postcss` and `tailwindcss` both appear, create `part_of` edge. Plugin patterns (`eslint-plugin-X` + `eslint`) create `configured_by` edges.
- Parse `devDependencies` → same as above but edges use `dev_depends_on` relationship type
- For Python: parse `pyproject.toml` dependency groups the same way
- Test/build/lint tool detection (existing logic in `_infer_npm_relationships`) is preserved but edges point to the project concept, not an arbitrary "main framework"
- Edges get `confidence: "structural"`

### 1b. CLAUDE.md architecture edges (upgrade `claude_md.py`)

Current state: extracts bold text from Stack section, creates zero relationships.

New behavior:
- Parse the Stack section structure: each bullet says "**Tool** — description mentioning other tools"
- When a Stack entry mentions another concept by name, create a `uses` edge
- Parse explicit relationship language: "built on", "powered by", "calls", "wraps" → map to edge types
- Example: `"**Backend**: Python 3.12+. FastAPI (async) + uvicorn"` → FastAPI `uses` uvicorn

### 1c. MCP config edges (upgrade `mcp.py`)

Current state: extracts MCP server names, creates zero relationships.

New behavior:
- Every MCP server in the project's `.mcp.json` gets a `uses` edge to the project
- If the server command references a known concept, create a `wraps` or `uses` edge

### 1d. Import scanner (new, opt-in depth levels)

Three depth levels:
- **Level 0 (config-only)**: No import scanning. Only 1a-1c. Default.
- **Level 1 (entry points)**: Read imports from main.py, app.py, server.py, index.ts, cli.py. Map third-party imports to known concepts → `uses` edges.
- **Level 2 (full)**: Walk src/ directory, build full import graph. Most accurate, slowest.

## Section 2: LLM Gap-Fill Pass

After structural edges are created, some concepts will still have zero connections — concepts like "MCP" (a protocol, not a package) or "Deployment" (captured from Eagle Mem).

### When it runs
After all structural scanners complete. Only targets concepts with zero edges after the structural pass that are in the `project` layer.

### How it works
1. Gather orphaned concepts (zero edges post-structural)
2. Build a rich context prompt per orphan:
   - Project's CLAUDE.md (full text)
   - Eagle Mem overview for the project
   - List of ALL connected concepts already in the graph (the skeleton)
   - The orphan's own description
3. Prompt: "Here is a project's architecture and its dependency graph. The concept '{name}' has no connections. Based on the architecture, which existing concepts does it relate to, and how? Only output relationships you are confident about. Return empty array if unsure."
4. The LLM can only connect orphans to already-connected concepts — cannot invent new concepts or connect orphans to each other
5. Edges get `confidence: "inferred"`

### Differences from current `infer.py`
- Current: ALL concept pairs, similarity finds candidates, LLM labels
- New: only orphans, full project architecture context, LLM picks target AND relationship, can return empty

### Safeguards
- LLM must pick from existing connected concepts only
- LLM can return empty array (current system forces a relationship)
- Full CLAUDE.md context means LLM understands architecture
- `confidence: "inferred"` flag for UI distinction

## Section 3: Similarity Pass — `similar_to` Only

Final pass after structural + LLM gap-fill.

### Rules
- Same category required (both "framework", both "devtool", etc.)
- Same project required (no cross-project edges)
- High threshold: cosine similarity > 0.7 (current is 0.55)
- Only produces `similar_to` edges
- `confidence: "similarity"` marker

### Examples
- asyncpg `similar_to` psycopg2-binary (both framework, both Postgres) — created
- fastapi + pydantic — same category but similarity ~0.6, below 0.7 — blocked
- asyncpg + @tanstack/react-query — different projects — blocked

## Section 4: Concept Layering — Project vs Dev Environment

### Problem
Concepts like eagle-anti-slop, cursor, llm-wiki leak into project graphs because Eagle Mem mentioned them during sessions.

### Solution
Add `layer` field to concepts: `"project"` or `"environment"`.

### Assignment rules
- `packages.py`, `claude_md.py`, `mcp.py`, import scanner → `"project"`
- `eagle_mem.py` session scanning, Claude skills/plugins → `"environment"`
- `hook_capture` → `"project"` if installed in project dir, `"environment"` if global
- MCP `add_concept` → `"project"`

### Graph behavior
- Default view shows `project` layer only
- Toggle in sidebar to show environment tools
- Edges only between concepts in the same layer
- LLM gap-fill only operates on `project` layer

## Section 5: Context Display Cleanup

### Problem
SidePanel shows raw Eagle Mem session dumps — truncated, incoherent text.

### New `/api/concepts/:id/context` response
```json
{
  "usage_summary": "AI-generated 2-3 sentence summary",
  "raw_context": ["filtered snippet 1", "filtered snippet 2"],
  "install_commands": ["pip install mcp"],
  "claude_memories": ["relevant memory"]
}
```

### Changes to `context.py`
1. Filter: minimum 40 char snippets, deduplicate, skip command outputs
2. Summarize always: generate and store `usage_summary` on the concept (persists across restarts)
3. Regenerate on re-enrich

### Frontend
SidePanel shows `usage_summary` as primary text. "Show raw" toggle for filtered snippets. If no AI available, show filtered snippets directly.

## Section 6: Pipeline Orchestration

### Unified function: `rebuild_project_edges(conn, project_id, depth=0)`

```
1. Delete existing edges for project (except confidence="manual")
2. Run structural scanners on project path:
   - packages (always)
   - claude_md (always)
   - mcp config (always)
   - entry point imports (if depth >= 1)
   - full import graph (if depth == 2)
3. Similarity pass (same-category, >0.7, similar_to only)
4. LLM gap-fill for orphaned project-layer concepts
5. Return stats: {structural, similarity, inferred, orphans_remaining}
```

### Where it gets called

| Entry point | Behavior |
|---|---|
| Bulk enrich (UI) | Enrich unenriched → `rebuild_project_edges(depth=0)` |
| Project scan (API/CLI) | Scan → sync → enrich → `rebuild_project_edges(depth=0)` |
| Session-end hook | `nexus scan` triggers scan pipeline |
| Single concept enrich | Enrich → `rebuild_project_edges(depth=0)` |
| MCP add_concept | Add → check config files for edges to new concept |
| Hook track_install | Add → check config files for edges |
| CLI `nexus rebuild-graph` | Explicit with `--depth` flag |

### Edge preservation
Manual edges (`confidence: "manual"`) are excluded from deletion on rebuild. Everything else is deterministically recreated.

## Section 7: Schema Changes

### `edges` table — add `confidence` column
- `"structural"` — from config/import scanning
- `"similarity"` — from same-category cosine pass
- `"inferred"` — from LLM gap-fill
- `"manual"` — user-created, never auto-deleted
- Default: `"structural"`. Migration backfills existing as `"inferred"`.

### `concepts` table — add `layer` column
- `"project"` or `"environment"`. Default: `"project"`.
- Migration backfills by source: `package_scan`, `claude_md`, `mcp_config` → `"project"`. Known dev-tool patterns (eagle-*, cursor, llm-wiki, claude-plugins-*) → `"environment"`. Else `"project"`.

Both are `ALTER TABLE ADD COLUMN` migrations. No data loss.

## Section 8: Validation Strategy

### Farmerchat-agentic as benchmark
After running the new pipeline, verify:
- MCP has edges (should connect to google-adk, the agent system)
- google-adk connects to google-genai (depends_on)
- fastapi connects to uvicorn, pydantic (uses)
- asyncpg does NOT connect to @tanstack/react-query
- eagle-anti-slop is in environment layer
- Edge count is lower but every edge is defensible

### Automated checks
- Zero cross-project edges
- Zero edges between project and environment layers
- Every `structural` edge traces to a file
- `similar_to` edges are same-category only
- `inferred` edges have non-empty description

### Test suite
- Unit tests per scanner's relationship extraction
- Integration test: fixture project → verify exact edge set
- Regression: specific garbage edges must not appear

### Manual spot-check
After rebuild on all 4 projects, dump edge list and review before committing.
