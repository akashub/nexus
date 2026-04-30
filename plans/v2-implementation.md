# Nexus V2 — Implementation Plan

## Design Decisions (Confirmed)

1. **Single SQLite DB** with `project_id` column — no separate DBs per project
2. **Auto-update on every Claude Code session** — hook/skill fires on SessionEnd, compacts over time
3. **Cloud API deferred** — Ollama-only for now, cloud models added later
4. **Environment replication** — generates setup scripts (complete + context-based), callable from terminal or Claude Code

---

## Architecture Overview

```
Global Graph (projects as nodes)
  └── Project Graph (tools, deps, patterns as nodes)
       └── Concept Detail (description, quickstart, connections)
```

**Data flow:**
- Claude Code session ends → Nexus hook/skill fires → scans Eagle Mem, CLAUDE.md, package files, MCP configs, git history → upserts concepts + edges into project graph
- Desktop app shows global view (project nodes) → click project → project graph → click concept → detail panel
- `nexus replicate <project>` reads project graph → generates shell script with install commands

**New relationship types:** `sends_data_to`, `triggers`, `builds_into`, `configured_by`, `tested_with`, `wraps`, `serves`, `deployed_via`, `replaces` (in addition to existing `uses`, `depends_on`, `similar_to`, `part_of`, `related_to`)

---

## Phase 1: Schema Evolution — Projects Table + project_id

### 1.1 Migration 004: Add projects table and project_id

```sql
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    path TEXT,                    -- absolute path to project root
    description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

ALTER TABLE concepts ADD COLUMN project_id TEXT REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_concepts_project ON concepts(project_id);
```

**Existing V1 concepts:** After migration, all existing concepts have `project_id = NULL`. On first V2 launch, show these in an "Unassigned" group in the global view. The user can drag-assign them to projects, or `nexus scan` will claim them by matching concept names against scanned dependencies.

Projects themselves appear as nodes in the global graph.

**Files to change:**
- `backend/migrations/004_projects.sql` — new migration file
- `backend/src/nexus/models.py` — add `Project` dataclass, add `project_id` field to `Concept`
- `backend/src/nexus/db.py` — add `add_project`, `get_project`, `list_projects`, `delete_project`; update `list_concepts` and `get_concept` to accept optional `project_id` filter
- `backend/src/nexus/server.py` — add `ProjectCreate` pydantic model
- `backend/src/nexus/routes.py` — add `/api/projects` CRUD endpoints, update `/api/graph` to accept `?project_id=` filter, add `/api/graph/global` endpoint that returns projects as nodes with inter-project edges

**Done when:** `nexus db init` applies migration, API returns projects, `GET /api/graph?project_id=X` returns only that project's concepts.

### 1.2 Update frontend types + API hooks

- `desktop/src/types.ts` — add `Project` interface, add `project_id` to `Concept`
- `desktop/src/hooks/useApi.ts` — add `useProjects`, `useAddProject`, `useProjectGraph(projectId)`, `useGlobalGraph`

**Done when:** Frontend can fetch project list and project-scoped graphs.

### 1.3 Global graph view in desktop

The App needs a two-level navigation:

- **Global view** (default): projects as large nodes, edges between projects (derived from cross-project concept connections). Click a project → drill into project graph.
- **Project view**: current GraphView behavior but filtered to `project_id`. Breadcrumb shows `global > project_name`. Back button returns to global view.

**Files to change:**
- `desktop/src/App.tsx` — add `activeProject: Project | null` state, conditionally render GlobalGraphView vs ProjectGraphView
- `desktop/src/components/GlobalGraphView.tsx` — new component, similar to GraphView but renders projects as nodes. Simpler (fewer nodes, no enrichment pulse). Click node → `setActiveProject(project)`.
- `desktop/src/components/GraphView.tsx` — receives `projectId` prop, passes to `useGraph` call
- `desktop/src/components/Breadcrumb.tsx` — small component: `global > project_name` with click-to-go-back

**Done when:** App shows global graph with project nodes. Clicking a project drills into its concept graph. Back button works.

---

## Phase 2: Auto-Capture Engine

The core V2 feature. A scanner that reads project context and builds the knowledge graph automatically.

### 2.1 Project scanner module

New file: `backend/src/nexus/scanner.py`

Reads multiple sources from a project directory and extracts tool/dependency/pattern information:

**Source 1: Package files** (highest signal)
- `package.json` → npm dependencies (name, version, dev vs prod)
- `pyproject.toml` / `requirements.txt` → Python dependencies
- `Cargo.toml` → Rust crates
- `go.mod` → Go modules
- `Gemfile` → Ruby gems

For each dependency: create a concept with `source="package_scan"`, category inferred from package type (devtool for devDeps, framework for main deps — refined by enrichment later).

**Source 2: CLAUDE.md / AGENTS.md** (high signal)
- Parse stack section → extract tool names, frameworks, patterns mentioned
- Parse directory layout → understand project structure
- These files are written by developers, so tool mentions are intentional

**Source 3: MCP config** (`~/.claude/plugins.json`, `.mcp.json`, project-level MCP configs)
- Each MCP server is a concept (category: devtool)
- Server-to-project relationships: `configured_by`

**Source 4: Eagle Mem** (`~/.eagle-mem/memory.db`)
- Query FTS for project-related sessions, observations, code context
- Extract tool/framework mentions from session summaries
- This gives workflow context that package files miss (e.g., "used Playwright for E2E testing" — the *why*)

**Source 5: Git history** (lower signal, used for relationship inference)
- `git log --oneline -50` → recent commit messages
- Files that change together → concepts that are `related_to`
- New dependency additions correlate with commit messages explaining *why*

**Source 6: Import graph** (for relationship inference)
- Scan top-level source files for import statements
- `import X from Y` → concept X `uses` concept Y
- Don't deep-scan — just entry points and config files

```python
@dataclass
class ScanResult:
    concepts: list[ScannedConcept]  # name, source, category_hint, context
    relationships: list[ScannedRelationship]  # source_name, target_name, rel_type, reason
    project_description: str | None
```

**Files:**
- `backend/src/nexus/scanner.py` — main scanner, delegates to sub-scanners
- `backend/src/nexus/scanners/packages.py` — package file parsing
- `backend/src/nexus/scanners/claude_md.py` — CLAUDE.md / AGENTS.md parsing
- `backend/src/nexus/scanners/mcp.py` — MCP config parsing
- `backend/src/nexus/scanners/eagle_mem.py` — Eagle Mem database querying
- `backend/src/nexus/scanners/git_history.py` — git log parsing

**Done when:** `scanner.scan_project("/path/to/project")` returns a `ScanResult` with concepts and relationships extracted from all available sources.

### 2.2 Upsert logic — merge scanned results into DB

Scanned concepts need to be merged with existing data without losing user edits or AI enrichment.

Rules:
- If concept exists (by name, case-insensitive) in this project → update `source` field, don't overwrite description/notes/category if already enriched
- If concept is new → insert with `source="auto_scan"`, queue for enrichment
- If concept existed in previous scan but not in current → don't delete (user may have added it manually), but mark as `stale` (new field)
- Relationships: add if not exists, don't remove existing ones

**Files:**
- `backend/src/nexus/sync.py` — `sync_scan_results(conn, project_id, scan_result)` — handles upsert logic
- `backend/src/nexus/db.py` — add `get_concept_by_name_and_project(conn, name, project_id)`

**Done when:** Running scan twice on the same project doesn't create duplicates. Manual edits survive re-scans.

### 2.3 CLI: `nexus scan <path>`

Scans a project directory and populates the graph.

```
nexus scan .                    # scan current directory
nexus scan /path/to/project     # scan specific path
nexus scan . --enrich           # scan + enrich all new concepts
nexus scan . --dry-run          # show what would be added without writing
```

Auto-creates a project entry if one doesn't exist for the path.

**Files:**
- `backend/src/nexus/cli.py` — add `scan` command

**Done when:** `cd /some/project && nexus scan . --dry-run` lists concepts that would be added. Without `--dry-run`, concepts appear in the DB under a project.

### 2.4 Claude Code hook/skill for auto-capture

A Claude Code skill that fires on session end (or can be called manually) to auto-scan the current project.

**Option A: CLAUDE.md instruction** (simplest, start here)
Add to project's CLAUDE.md: "At the end of significant sessions, run `nexus scan .` to update the knowledge graph."

**Option B: Claude Code skill** (more control)
Create `~/.claude/skills/nexus-capture/nexus-capture.md`:
- Fires on SessionEnd
- Runs `nexus scan <project_path>`
- If new concepts found, runs enrichment on them
- Logs summary: "Added 3 concepts, 2 connections to project X"

**Option C: Eagle Mem PostToolUse hook** (most automated)
Hook into Eagle Mem's PostToolUse that fires on `npm install`, `pip install`, etc.
- Detects install commands → calls `nexus add <package> --project <current>`
- Lightweight, real-time capture

**V2 target is Option B** (Claude Code skill on SessionEnd). Option A (CLAUDE.md instruction) is the transitional step while the skill is being built — it ships first so users get value immediately, then gets replaced by the automated skill. Option C (PostToolUse hook) is post-V2.

**Files:**
- `backend/src/nexus/skills/nexus-capture.md` — Claude Code skill definition
- Or: CLAUDE.md additions for projects that want auto-capture

**Done when:** After a Claude Code session, running the skill/command updates the project's knowledge graph.

### 2.5 Compaction

Over time, repeated scans accumulate redundant data. Compaction merges duplicate concepts, removes stale entries, and consolidates relationships.

```
nexus compact <project>         # compact a specific project
nexus compact --all             # compact all projects
```

Logic:
- Merge concepts with similar names (fuzzy match + embedding similarity > 0.9)
- Remove concepts marked `stale` for > 30 days with no user edits
- Deduplicate edges (same source, target, relationship)
- Re-run embedding for concepts whose descriptions changed

**Files:**
- `backend/src/nexus/compact.py` — compaction logic
- `backend/src/nexus/cli.py` — add `compact` command

**Done when:** `nexus compact my-project` reduces redundant entries and reports what was merged/removed.

---

## Phase 3: Enrichment Pipeline v2

### 3.1 Tiered enrichment with source priority

Current enrichment uses Ollama only. V2 enrichment tries sources in priority order:

1. **Eagle Mem context** — if Eagle Mem has session notes about this tool, use them as primary context
2. **Claude Code session context** — if the scan came from a session, the session knows *why* the tool was added
3. **Context7** — library/framework docs (already implemented)
4. **Web fetch** — fallback for non-library concepts (httpx + readability extraction)
5. **Ollama** — for summarization and category inference (already implemented)

The key insight: Eagle Mem and session context provide the *why* (workflow context), while Context7/web provide the *what* (technical docs). Combine both for richer descriptions.

**Files:**
- `backend/src/nexus/enrich.py` — refactor `enrich_concept` to try Eagle Mem first, then Context7, then web, then Ollama-only
- `backend/src/nexus/scanners/eagle_mem.py` — reuse for enrichment context (query Eagle Mem for sessions mentioning this concept)

**Done when:** Enriching a concept that Eagle Mem knows about produces a description that includes workflow context ("used in this project for X") alongside technical description.

### 3.2 Workflow-aware relationship inference

Current relationship inference uses only embedding similarity. V2 adds structural inference:

- Package A is in `devDependencies`, Package B is in `dependencies` → A `tested_with` B (if A is a testing tool)
- Tool A's output is Tool B's input (from CLAUDE.md or session context) → A `sends_data_to` B
- Framework A wraps Library B (from docs) → A `wraps` B
- Tool A is configured in Tool B's config (e.g., ESLint plugin for TypeScript) → A `configured_by` B

New relationship types to add to schema:
```
sends_data_to, triggers, builds_into, configured_by,
tested_with, wraps, serves, deployed_via, replaces
```

**Files:**
- `backend/src/nexus/enrich.py` — add `_infer_workflow_relationships` function
- `backend/src/nexus/models.py` — add `RELATIONSHIP_TYPES` constant
- `desktop/src/components/graphStyles.ts` — different edge styles for different relationship types (dashed for `similar_to`, thick for `depends_on`, etc.)

**Done when:** Auto-scan of a project produces workflow-aware edges like "vitest tested_with react" and "tailwind configured_by postcss".

---

## Phase 4: Environment Replication

### 4.1 Replication data model

Each concept can have setup instructions attached (what commands to run to install/configure it).

Migration 005:
```sql
ALTER TABLE concepts ADD COLUMN setup_commands TEXT;  -- JSON array of shell commands
ALTER TABLE concepts ADD COLUMN config_files TEXT;    -- JSON array of {path, content} for config files
```

During enrichment and scanning, populate these fields:
- npm packages → `npm install <name>` or `npm install -D <name>`
- Python packages → `pip install <name>` or `uv add <name>`
- Brew packages → `brew install <name>`
- MCP servers → the MCP config JSON block
- Config files → the actual config content (tsconfig.json, .eslintrc, etc.)

**Files:**
- `backend/migrations/005_setup_fields.sql`
- `backend/src/nexus/models.py` — add `setup_commands` and `config_files` to `Concept`
- `backend/src/nexus/scanners/packages.py` — populate setup_commands during scan

**Done when:** After scanning a project, each package concept has its install command stored.

### 4.2 `nexus replicate` command

Two modes:

**Complete replication:** Generates a script that installs everything in the project graph.
```
nexus replicate my-project --mode complete --output setup.sh
```

Output: a shell script that:
1. Creates project directory
2. Initializes package managers (npm init, uv init, etc.)
3. Installs all dependencies in correct order
4. Copies config files
5. Sets up MCP servers
6. Prints summary of what was installed

**Context-based replication:** Takes a description of what you want and generates a subset.
```
nexus replicate my-project --mode context --context "I want the frontend testing setup"
```

Uses embeddings to find concepts related to the context query, then generates a script for just those tools.

Context-based filtering uses embedding similarity with threshold > 0.4 and returns top 15 matches (user can uncheck in UI preview).

**Files:**
- `backend/src/nexus/replicate.py` — orchestrator: `generate_setup_script(conn, project_id, mode, context_query?)`
- `backend/src/nexus/replicate_packagers.py` — per-ecosystem install command generators (npm, pip, brew, cargo)
- `backend/src/nexus/cli.py` — add `replicate` command

Pre-split because replicate.py will exceed 200 LOC if it combines filtering + script generation + per-ecosystem logic.

**Done when:** `nexus replicate my-project --mode complete` generates a working setup.sh. `--mode context --context "testing"` generates a script with only test-related tools.

### 4.3 Desktop UI for replication

Simple panel accessible from the project detail view:

- "Replicate" button on project node in global graph
- Opens a modal with two tabs: Complete / Context-based
- Context-based tab has a text input for the query
- Preview of what will be installed (checklist, user can uncheck items)
- "Generate Script" button → downloads .sh file
- "Copy to Clipboard" button → copies script content

**Files:**
- `desktop/src/components/ReplicateModal.tsx` — new component
- `desktop/src/hooks/useApi.ts` — add `useReplicate` mutation
- `backend/src/nexus/routes.py` — add `POST /api/projects/{id}/replicate` endpoint

**Done when:** User can click Replicate on a project, choose mode, preview, and download a setup script.

---

## Phase 5: Frontend — Global Graph Navigation

### 5.1 Project selector / global view

Rework the app layout for two-level navigation:

**Header changes:**
- Add project name in breadcrumb: `nexus > project_name` (or just `nexus` for global view)
- Click `nexus` → return to global view

**Global graph specifics:**
- Larger nodes (projects are fewer but more important)
- Node size = concept count in project
- Edges between projects = one weighted edge per project pair, weight = number of shared concepts. Derived at query time, not stored. Only show edges where shared concept count >= 2 (avoids noise from ubiquitous deps like `node`).
- Different color scheme: projects use muted colors, not category colors
- Click project → transition to project graph (zoom-in animation)

**Files:**
- `desktop/src/App.tsx` — add `activeProject` state, breadcrumb, conditional rendering
- `desktop/src/components/GlobalGraphView.tsx` — new, renders projects
- `desktop/src/components/ProjectNode.tsx` — project node detail (concept count, last scan time, description)
- `desktop/src/components/GraphView.tsx` — accept optional `projectId` prop

**Done when:** App has working two-level navigation. Global view shows projects, clicking drills into project graph.

### 5.2 Project side panel

When clicking a project node in global view:
- Project name, description, path
- Concept count, edge count
- Last scanned timestamp
- "Open Graph" button → drill into project
- "Scan Now" button → trigger `nexus scan` for this project
- "Replicate" button → open replicate modal
- "Delete Project" button

**Files:**
- `desktop/src/components/ProjectPanel.tsx` — new component
- `desktop/src/hooks/useApi.ts` — add `useScanProject` mutation

**Done when:** Clicking a project in global view shows its details with action buttons.

### 5.3 Edge styling by relationship type

Different visual treatment for different relationship types:

| Relationship | Style |
|---|---|
| `depends_on`, `uses` | Solid line, normal width |
| `similar_to` | Dashed line (already implemented) |
| `part_of` | Dashed line (already implemented) |
| `sends_data_to`, `triggers` | Solid line + animated dash (data flow) |
| `configured_by` | Dotted line, thin |
| `tested_with` | Dashed, green-tinted |
| `wraps`, `serves` | Thick solid line |
| `deployed_via` | Dotted, orange-tinted |
| `replaces` | Red dashed line |

**Files:**
- `desktop/src/components/graphStyles.ts` — add selectors for each relationship type

**Done when:** Different relationship types are visually distinguishable in the graph.

---

## Phase 6: New CLI Commands + API Endpoints

### 6.1 New CLI commands

```
nexus project list                       # list all projects
nexus project add <name> --path <path>   # register a project
nexus project show <name>                # project details + concept count
nexus project remove <name>              # delete project (keeps concepts as orphans)
nexus scan <path>                        # scan project directory
nexus scan <path> --enrich               # scan + enrich new concepts
nexus scan <path> --dry-run              # preview without writing
nexus compact <project>                  # compact project graph
nexus replicate <project>                # generate complete setup script
nexus replicate <project> --context "X"  # context-based replication
```

**Files:**
- `backend/src/nexus/cli.py` — add project and scan subcommands
- May need `cli_project.py` if cli.py gets too long

### 6.2 New API endpoints

```
GET    /api/projects                     # list projects
POST   /api/projects                     # create project
GET    /api/projects/:id                 # project detail
PUT    /api/projects/:id                 # update project
DELETE /api/projects/:id                 # delete project
POST   /api/projects/:id/scan           # trigger scan
POST   /api/projects/:id/replicate      # generate setup script
GET    /api/graph/global                 # global graph (projects as nodes)
GET    /api/graph?project_id=X           # project-scoped graph
```

**Files:**
- `backend/src/nexus/routes.py` — add endpoints (may need to split into `routes_projects.py` if too long)

---

## Implementation Order

| Step | What | Depends On | Effort |
|------|------|-----------|--------|
| 1 | Migration 004 + Project model + DB functions | Nothing | 1 day |
| 2 | Project API endpoints | Step 1 | 0.5 day |
| 3 | Frontend types + hooks + project selector | Step 2 | 1 day |
| 4 | Global graph view (projects as nodes) | Step 3 | 1.5 days |
| 5 | Package scanner (npm, pip, cargo) | Step 1 | 1 day |
| 6 | CLAUDE.md scanner | Step 1 | 0.5 day |
| 7 | Eagle Mem scanner | Step 1 | 0.5 day |
| 8 | MCP config scanner | Step 1 | 0.5 day |
| 9 | Git history scanner | Step 1 | 0.5 day |
| 10 | Scanner orchestrator + upsert logic | Steps 5-9 | 1 day |
| 11 | `nexus scan` CLI command | Step 10 | 0.5 day |
| 12 | Workflow relationship inference | Step 10 | 1 day |
| 13 | Edge styling by relationship type | Step 12 | 0.5 day |
| 14 | Enrichment v2 (Eagle Mem context) | Step 7 | 1 day |
| 15 | Migration 005 + setup fields | Step 1 | 0.5 day |
| 16 | Replication engine | Steps 15, 10 | 1.5 days |
| 17 | `nexus replicate` CLI | Step 16 | 0.5 day |
| 18 | Replication UI | Steps 16, 4 | 1 day |
| 19 | Compaction logic + CLI | Step 10 | 1 day |
| 20 | Claude Code skill for auto-capture | Step 11 | 0.5 day |

**Total: ~15 working days**

Steps 5-9 can be parallelized. Steps 4 and 10 are the critical path.

---

## File Impact Summary

**New files:**
- `backend/migrations/004_projects.sql`
- `backend/migrations/005_setup_fields.sql`
- `backend/src/nexus/scanner.py`
- `backend/src/nexus/scanners/__init__.py`
- `backend/src/nexus/scanners/packages.py`
- `backend/src/nexus/scanners/claude_md.py`
- `backend/src/nexus/scanners/eagle_mem.py`
- `backend/src/nexus/scanners/mcp.py`
- `backend/src/nexus/scanners/git_history.py`
- `backend/src/nexus/sync.py`
- `backend/src/nexus/compact.py`
- `backend/src/nexus/replicate.py`
- `backend/src/nexus/replicate_packagers.py`
- `desktop/src/components/GlobalGraphView.tsx`
- `desktop/src/components/ProjectPanel.tsx`
- `desktop/src/components/ReplicateModal.tsx`
- `desktop/src/components/Breadcrumb.tsx`

**Modified files:**
- `backend/src/nexus/models.py` — Project dataclass, project_id on Concept, setup fields
- `backend/src/nexus/db.py` — project CRUD, project-scoped queries
- `backend/src/nexus/server.py` — ProjectCreate model, new endpoints
- `backend/src/nexus/routes.py` — project + scan + replicate routes
- `backend/src/nexus/enrich.py` — tiered enrichment, workflow relationships
- `backend/src/nexus/cli.py` — scan, compact, replicate, project commands
- `desktop/src/types.ts` — Project type, updated Concept
- `desktop/src/hooks/useApi.ts` — project hooks, scan/replicate mutations
- `desktop/src/App.tsx` — two-level navigation, activeProject state
- `desktop/src/components/GraphView.tsx` — projectId prop
- `desktop/src/components/graphStyles.ts` — relationship-specific edge styles
- `CLAUDE.md` — updated with V2 commands and architecture

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Eagle Mem DB schema changes break scanner | Scanner can't read sessions | Pin to known Eagle Mem schema, handle missing tables gracefully |
| Package scanning too slow on large monorepos | `nexus scan` takes minutes | Scan only top-level package files, skip node_modules/.venv, cache results |
| Global graph cluttered with too many projects | Unreadable | Max 20 projects in global view, search/filter for more |
| Replication scripts break on different OS | Scripts fail on Windows/Linux | Generate platform-aware scripts, test on macOS first (Aakash's platform) |
| 200 LOC limit makes scanner files too fragmented | Hard to follow | Each scanner is independent and small, orchestrator ties them together |

---

## End-to-End Golden Path (V2 Verification)

1. **Scan this repo:** `cd ~/Development_dg/Project/nexus && nexus scan .`
   - Creates "nexus" project node
   - Detects: React, Tailwind, Tauri, FastAPI, Cytoscape.js, d3-force, Vite, Click, Ollama, Context7, SQLite
   - Infers edges: `vite builds_into react`, `tailwind configured_by postcss`, `cytoscape uses d3-force`, `fastapi serves react`

2. **Scan another project:** `cd ~/some-other-project && nexus scan .`
   - Creates second project node
   - Shared deps (e.g., both use React) → edge between project nodes in global view

3. **Open desktop app → Global view:**
   - See "nexus" and "other-project" as nodes with a weighted edge
   - Click "nexus" → drill into project graph
   - See React, Tailwind, FastAPI etc. as concept nodes with workflow edges
   - Hover React → connected nodes highlight (Vite, Tailwind, Cytoscape)

4. **Replicate:**
   - Click "nexus" project → Replicate → Complete mode → preview shows all deps
   - Switch to Context-based → type "frontend visualization" → preview shows: React, Cytoscape.js, d3-force, Tailwind, Vite
   - Generate Script → downloads setup.sh with `npm install react cytoscape d3-force`, `npx tailwindcss init`, etc.

5. **Auto-capture:**
   - End a Claude Code session in a project directory
   - Nexus skill fires → `nexus scan .` runs → new deps from the session appear in graph
   - Open desktop → new concepts visible, enrichment queued

6. **Compaction:**
   - After 10 sessions, `nexus compact nexus` → merges duplicates, removes stale entries
   - Graph is cleaner, no redundant nodes
